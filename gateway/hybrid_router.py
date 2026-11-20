"""Hybrid Router: Multi-tier routing combining fast statistical ML with SLM fallback.

Architecture:
  - Tier 1: Fast Scikit-learn Classifier (<3ms, MLflow @champion)
  - Tier 2: SLM-Judge (Small Language Model fallback when Tier 1 is ambiguous)
  - Strategy Selection:
      * 'hybrid': ML first; escalate to SLM-Judge only when ambiguous (40% - 65% conf).
      * 'ml_fast': Sub-millisecond statistical routing only.
      * 'llm_semantic': Zero-shot SLM intent & complexity classifier.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any

from gateway.config import settings
from gateway.router_service import router_service
from router import policy

log = logging.getLogger(__name__)

AMBIGUOUS_LOW = 0.40
AMBIGUOUS_HIGH = 0.65

SLM_ROUTER_PROMPT = """You are an ultra-fast query complexity router for an LLM Gateway.
Classify the user's query into exactly one of these categories:
- "simple": Factual lookup, trivial translation, simple definition, short greetings.
- "moderate": General synthesis, open QA, essay brainstorming, editing, summarization.
- "complex_reasoning": Multi-step math, formal logic, riddles, science word problems.
- "complex_code": Code generation, algorithm design, debugging, SQL queries, regex.

Respond ONLY with a valid JSON object matching this schema:
{
  "category": "simple" | "moderate" | "complex_reasoning" | "complex_code",
  "confidence": 0.0 to 1.0,
  "reason": "1-line explanation"
}

Query:
"""


@dataclass
class HybridRoutingResult:
    predicted_label: str
    confidence: float
    model: str
    reason: str
    strategy_used: str
    slm_consulted: bool
    routing_latency_ms: float


class HybridRouter:
    def __init__(self) -> None:
        pass

    async def route(
        self,
        query: str,
        provider_pool: Any,
        strategy: str = "hybrid",
        threshold: float | None = None,
    ) -> HybridRoutingResult:
        started = time.perf_counter()
        active_threshold = threshold if threshold is not None else settings.router_threshold

        if strategy == "llm_semantic":
            return await self._route_slm(query, provider_pool, started, strategy="llm_semantic")

        # Tier 1: Fast ML classification
        ml_label, ml_confidence = router_service.predict(query)

        if strategy == "ml_fast":
            decision = policy.decide(ml_label, ml_confidence, active_threshold)
            return HybridRoutingResult(
                predicted_label=ml_label,
                confidence=ml_confidence,
                model=decision.model,
                reason=f"[Tier-1 ML] {decision.reason}",
                strategy_used="ml_fast",
                slm_consulted=False,
                routing_latency_ms=(time.perf_counter() - started) * 1000,
            )

        # Strategy: 'hybrid'
        # Check if Tier 1 is ambiguous (confidence in ambiguous zone or label is moderate)
        is_ambiguous = (AMBIGUOUS_LOW <= ml_confidence <= AMBIGUOUS_HIGH) or (
            ml_label == "moderate" and ml_confidence < active_threshold + 0.05
        )

        if not is_ambiguous:
            decision = policy.decide(ml_label, ml_confidence, active_threshold)
            return HybridRoutingResult(
                predicted_label=ml_label,
                confidence=ml_confidence,
                model=decision.model,
                reason=f"[Tier-1 Confident ML] {decision.reason}",
                strategy_used="hybrid",
                slm_consulted=False,
                routing_latency_ms=(time.perf_counter() - started) * 1000,
            )

        # Tier 2: Ambiguity detected -> escalate to SLM-Judge
        log.info(
            "Tier-1 ambiguous (label=%s, conf=%.2f) -> escalating to SLM-Judge",
            ml_label,
            ml_confidence,
        )
        try:
            slm_result = await self._route_slm(
                query,
                provider_pool,
                started,
                strategy="hybrid",
                ml_fallback_label=ml_label,
                ml_fallback_conf=ml_confidence,
            )
            return slm_result
        except Exception as exc:
            log.warning("SLM-Judge failed (%s); falling back to Tier-1 ML decision", exc)
            decision = policy.decide(ml_label, ml_confidence, active_threshold)
            return HybridRoutingResult(
                predicted_label=ml_label,
                confidence=ml_confidence,
                model=decision.model,
                reason=f"[Tier-1 Fallback] {decision.reason}",
                strategy_used="hybrid",
                slm_consulted=True,
                routing_latency_ms=(time.perf_counter() - started) * 1000,
            )

    async def _route_slm(
        self,
        query: str,
        provider_pool: Any,
        started: float,
        strategy: str,
        ml_fallback_label: str = "moderate",
        ml_fallback_conf: float = 0.5,
    ) -> HybridRoutingResult:
        # Prompt the fast router model
        prompt = SLM_ROUTER_PROMPT + query[:500]
        # Use the fast model for routing classification
        completion = await provider_pool.complete(model=policy.MODEL_FAST, prompt=prompt)
        text = completion.text.strip()

        # Parse JSON
        category = ml_fallback_label
        confidence = ml_fallback_conf
        reason = "SLM evaluated intent"

        # Attempt to extract JSON even if model output contains markdown code fence
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                category = data.get("category", category)
                confidence = float(data.get("confidence", 0.85))
                reason = data.get("reason", reason)
            except Exception:
                pass

        # Map SLM category to destination model
        mapped_model = policy.map_category_to_model(category)

        return HybridRoutingResult(
            predicted_label=category,
            confidence=confidence,
            model=mapped_model,
            reason=f"[Tier-2 SLM-Judge] {category}: {reason}",
            strategy_used=strategy,
            slm_consulted=True,
            routing_latency_ms=(time.perf_counter() - started) * 1000,
        )


hybrid_router = HybridRouter()
