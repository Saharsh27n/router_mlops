"""SmartRoute gateway — FastAPI application.

Request path:  classify -> route -> call provider -> log
Later blocks extend this with the cascade verifier, the response cache and the
security middleware; the ordering of those concerns lives in `_handle_chat`.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field

from gateway import cascade, db, drift_demo, metrics, security
from gateway.config import settings
from gateway.hybrid_router import hybrid_router
from gateway.providers import ProviderPool
from gateway.router_service import router_service
from router import drift, policy
from router.drift import REFERENCE_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("smartroute")

pool: ProviderPool | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool
    db.init_db()
    router_service.load()
    pool = ProviderPool()
    log.info("gateway ready: provider=%s model=%s", pool.mode, router_service.info())
    yield
    if pool:
        await pool.aclose()


app = FastAPI(
    title="SmartRoute LLM Gateway",
    description=(
        "Routes each query to a cheap or expensive language model using a trained "
        "difficulty classifier, and measures what that saves."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------- schemas


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=8000)
    strategy: str = Field(
        default="hybrid",
        description="Routing strategy: 'hybrid' (ML+SLM), 'ml_fast' (ML), or 'llm_semantic'.",
    )
    threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Override the confidence threshold for this request.",
    )
    no_cascade: bool = Field(
        default=False,
        description="Skip cascade verification. Used by the A/B comparison in eval.",
    )


class RoutingInfo(BaseModel):
    predicted_label: str
    confidence: float
    model: str
    reason: str
    strategy: str = "hybrid"
    slm_consulted: bool = False
    routing_latency_ms: float = 0.0
    escalated: bool = False
    cached: bool = False
    redactions: int = 0
    flagged: bool = False
    model_version: str


class UsageInfo(BaseModel):
    input_tokens: int
    output_tokens: int
    cost_usd: float
    baseline_cost_usd: float
    saved_usd: float
    latency_ms: float
    provider: str


class ChatResponse(BaseModel):
    answer: str
    routing: RoutingInfo
    usage: UsageInfo


# --------------------------------------------------------------------- auth


async def require_api_key(x_api_key: str | None = Header(default=None)) -> str:
    """Gate on a valid key, then rate-limit that key. Order matters: there is no
    point spending rate-limit budget on a caller who was never authenticated."""
    if not security.is_valid_key(x_api_key):
        raise HTTPException(status_code=401, detail="missing or invalid X-API-Key")

    key_id = security.hash_key(x_api_key)[:12]
    allowed, retry_after = security.rate_limiter.check(key_id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="rate limit exceeded",
            headers={"Retry-After": str(round(retry_after, 1))},
        )
    return key_id


# --------------------------------------------------------------------- routes


@app.get("/health", tags=["ops"])
async def health() -> dict:
    return {
        "status": "ok" if router_service.ready else "degraded",
        "model": router_service.info(),
        "provider": pool.mode if pool else "uninitialised",
        "threshold": settings.router_threshold,
    }


@app.post("/v1/chat", response_model=ChatResponse, tags=["gateway"])
async def chat(request: ChatRequest, _key: str = Depends(require_api_key)) -> ChatResponse:
    if pool is None or not router_service.ready:
        raise HTTPException(status_code=503, detail="gateway not ready")
    return await _handle_chat(request)


async def _handle_chat(request: ChatRequest) -> ChatResponse:
    started = time.perf_counter()
    threshold = request.threshold if request.threshold is not None else settings.router_threshold

    # PII is masked before anything else happens: the redacted text is what gets
    # classified, what gets sent to the provider, and what gets persisted to our own
    # log, so a raw email or card number never exists outside this request's memory.
    redaction = security.redact(request.query)
    safe_query = redaction.text
    flagged = security.check_injection(request.query)
    if flagged:
        metrics.INJECTION_FLAGS.inc()
    for placeholder, _original in redaction.redacted:
        kind = placeholder.strip("<>").rsplit("_", 1)[0]
        metrics.PII_REDACTIONS.labels(kind=kind).inc()

    routing_result = await hybrid_router.route(
        query=safe_query,
        provider_pool=pool,
        strategy=request.strategy,
        threshold=threshold,
    )
    label = routing_result.predicted_label
    confidence = routing_result.confidence
    served_model = routing_result.model
    reason = routing_result.reason
    slm_consulted = routing_result.slm_consulted
    routing_latency_ms = routing_result.routing_latency_ms

    completion = await pool.complete(served_model, safe_query)
    total_cost = completion.cost_usd
    escalated = False

    # Cascade: the routing decision was made before any answer existed, so check the
    # cheap model's output and retry on the large model if it looks like a failure.
    is_cheap_model = served_model in (policy.CHEAP, policy.MODEL_FAST)
    if is_cheap_model and not request.no_cascade:
        verdict = cascade.verify(safe_query, completion.text)
        if verdict.escalate:
            escalated = True
            retry = await pool.complete(policy.EXPENSIVE, safe_query)
            metrics.ESCALATIONS.labels(trigger=verdict.trigger).inc()
            # Both calls are billed. An escalation that fires too often will show up
            # as a drop in measured savings rather than being quietly absorbed.
            total_cost += retry.cost_usd
            completion = retry
            served_model = policy.EXPENSIVE
            reason = f"{reason} -> escalated ({verdict.reason})"

    # The model only ever saw placeholders, so rehydrate before the answer reaches the
    # user -- the redaction is invisible to them even though it protected the request.
    answer_text = redaction.rehydrate(completion.text)

    # The counterfactual: what this exact request would have cost had we sent every
    # query to the large model. Measured per request, not extrapolated.
    baseline_cost = policy.cost_usd(
        policy.EXPENSIVE, completion.input_tokens, completion.output_tokens
    )
    elapsed_ms = (time.perf_counter() - started) * 1000

    metrics.REQUESTS.labels(model=served_model, provider=completion.provider).inc()
    metrics.ROUTING_DECISIONS.labels(predicted_label=label, model=served_model).inc()
    metrics.LATENCY.labels(model=served_model).observe(elapsed_ms / 1000)
    metrics.COST.labels(kind="actual").inc(total_cost)
    metrics.COST.labels(kind="baseline").inc(baseline_cost)
    if completion.provider == "mock" and pool.mode == "groq":
        metrics.PROVIDER_FALLBACKS.inc()

    await db.log_request(
        db.RequestRecord(
            query=safe_query,
            predicted_label=label,
            confidence=confidence,
            model=served_model,
            reason=reason,
            provider=completion.provider,
            input_tokens=completion.input_tokens,
            output_tokens=completion.output_tokens,
            cost_usd=total_cost,
            baseline_cost_usd=baseline_cost,
            latency_ms=elapsed_ms,
            model_version=router_service.version,
            escalated=escalated,
            redactions=redaction.count,
            flagged=flagged,
        )
    )

    return ChatResponse(
        answer=answer_text,
        routing=RoutingInfo(
            predicted_label=label,
            confidence=confidence,
            model=served_model,
            reason=reason,
            strategy=request.strategy,
            slm_consulted=slm_consulted,
            routing_latency_ms=routing_latency_ms,
            escalated=escalated,
            redactions=redaction.count,
            flagged=flagged,
            model_version=router_service.version,
        ),
        usage=UsageInfo(
            input_tokens=completion.input_tokens,
            output_tokens=completion.output_tokens,
            cost_usd=total_cost,
            baseline_cost_usd=baseline_cost,
            saved_usd=baseline_cost - total_cost,
            latency_ms=elapsed_ms,
            provider=completion.provider,
        ),
    )


@app.get("/stats", tags=["dashboard"])
async def stats() -> dict:
    return {**db.stats(), "model": router_service.info(), "timeline": db.cost_timeline()}


@app.get("/requests/recent", tags=["dashboard"])
async def recent(limit: int = 25) -> list[dict]:
    return db.recent(min(limit, 200))


@app.get("/metrics", tags=["ops"], include_in_schema=False)
async def prometheus_metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/drift", tags=["ops"])
async def drift_status(window: int = 60) -> dict:
    """Compare the last `window` live queries against the training distribution."""
    if not REFERENCE_PATH.exists():
        raise HTTPException(status_code=503, detail="no drift reference built yet")

    recent_queries = db.recent_queries(limit=window)
    if len(recent_queries) < 5:
        return {
            "status": "insufficient_data",
            "n_current": len(recent_queries),
            "message": "need at least 5 recent requests to compute drift",
        }

    report = drift.check_drift(recent_queries)
    payload = drift.report_to_dict(report)

    worst = max(report.features, key=lambda f: f.psi, default=None)
    metrics.DRIFT_SCORE.labels(feature="max").set(report.max_psi)
    if worst:
        metrics.DRIFT_SCORE.labels(feature=worst.feature).set(worst.psi)

    return payload


@app.post("/admin/simulate-drift", tags=["admin"])
async def simulate_drift(n: int = 30, _key: str = Depends(require_api_key)) -> dict:
    """Inject synthetic out-of-distribution traffic so /drift has something to show
    without waiting for real traffic to shift. Rows are tagged `synthetic=True` so a
    demo reset can clear them without touching genuine history."""
    queries = drift_demo.generate(n=n)
    for query in queries:
        label, confidence = router_service.predict(query)
        decision = policy.decide(label, confidence, settings.router_threshold)
        await db.log_request(
            db.RequestRecord(
                query=query,
                predicted_label=label,
                confidence=confidence,
                model=decision.model,
                reason=f"{decision.reason} [synthetic drift demo]",
                provider="synthetic",
                input_tokens=policy.estimate_tokens(query),
                output_tokens=0,
                cost_usd=0.0,
                baseline_cost_usd=0.0,
                latency_ms=0.0,
                model_version=router_service.version,
                synthetic=True,
            )
        )
    return {"injected": len(queries)}


@app.post("/admin/retrain", tags=["admin"])
async def retrain(_key: str = Depends(require_api_key)) -> dict:
    """Retrain the router and promote it only if it earns the champion slot.

    Runs the real training entrypoint in a worker thread so a demo click doesn't block
    the event loop, then reloads the serving model -- a successful promotion takes
    effect immediately, with no gateway restart.
    """
    import asyncio
    import contextlib

    from router.train import main as train_main

    # argparse calls sys.exit(0) on a clean run; that is not a failure here.
    with contextlib.suppress(SystemExit):
        await asyncio.to_thread(train_main, [])

    previous_version = router_service.version
    router_service.load()

    import mlflow

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    client = mlflow.MlflowClient()
    metrics_run = client.get_run(
        client.get_model_version_by_alias(
            settings.registered_model_name, settings.model_alias
        ).run_id
    )

    return {
        "version": router_service.version,
        "previous_version": previous_version,
        "promoted": router_service.version != previous_version,
        "macro_f1": metrics_run.data.metrics.get("macro_f1"),
        "cost_savings_pct": metrics_run.data.metrics.get("cost_savings_pct"),
    }
