"""LLM providers: the real Groq API, and a mock that stands in for it.

The mock is not just a test fixture. A live demo that depends on a third-party free
tier is a demo that can fail in front of an examiner because of a rate limit or a
dropped wifi connection, so the gateway degrades to the mock automatically and records
which provider actually served each request. The load test also runs against the mock
on purpose -- otherwise the benchmark would be measuring Groq's latency, not ours.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import random
import time
from dataclasses import dataclass

import httpx

from gateway.config import settings
from router import policy

log = logging.getLogger(__name__)


@dataclass
class Completion:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    provider: str  # "groq" | "mock"

    @property
    def cost_usd(self) -> float:
        return policy.cost_usd(self.model, self.input_tokens, self.output_tokens)


class MockProvider:
    """Deterministic stand-in with plausible latency and output length.

    Latency and verbosity scale with model size so the dashboard's latency and cost
    charts still tell the truth about the *shape* of the tradeoff when no key is set.
    """

    name = "mock"

    PROFILE = {
        policy.CHEAP: {"base_ms": 220, "jitter_ms": 90, "words": 45},
        policy.EXPENSIVE: {"base_ms": 780, "jitter_ms": 260, "words": 150},
    }

    async def complete(self, model: str, prompt: str) -> Completion:
        profile = self.PROFILE.get(model, self.PROFILE[policy.CHEAP])

        # Seed from the prompt so the same query always gets the same mock answer --
        # otherwise the cache hit-rate metric would be meaningless.
        seed = int(hashlib.sha256(f"{model}:{prompt}".encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)

        if os.getenv("FAST_MOCK") == "true" or "PYTEST_CURRENT_TEST" in os.environ:
            latency_s = 0.0
        else:
            latency_s = (profile["base_ms"] + rng.random() * profile["jitter_ms"]) / 1000
        started = time.perf_counter()
        await asyncio.sleep(latency_s)

        n_words = profile["words"] + rng.randint(-10, 10)
        text = f"[mock:{model}] Responding to: {prompt[:90]}\n\n" + " ".join(
            rng.choice(_FILLER) for _ in range(n_words)
        )
        return Completion(
            text=text,
            model=model,
            input_tokens=policy.estimate_tokens(prompt),
            output_tokens=policy.estimate_tokens(text),
            latency_ms=(time.perf_counter() - started) * 1000,
            provider=self.name,
        )


_FILLER = (
    "the model considers each step carefully before producing a final answer which "
    "accounts for context constraints and the requested level of detail"
).split()


class GroqProvider:
    """Thin async client for Groq's OpenAI-compatible chat completions endpoint."""

    name = "groq"

    def __init__(self, api_key: str, base_url: str, timeout: float) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    #: Rate-limit headers from the most recent response, so callers that need to pace
    #: themselves (the eval harness) can do so from real numbers rather than guesswork.
    last_rate_limit: dict[str, str] = {}

    async def complete(self, model: str, prompt: str, max_tokens: int | None = None) -> Completion:
        started = time.perf_counter()
        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens or settings.max_output_tokens,
            "temperature": 0.2,
        }
        if "gpt-oss" in model:
            body["reasoning_effort"] = "low"

        response = await self._client.post("/chat/completions", json=body)
        self.last_rate_limit = {
            key: value
            for key, value in response.headers.items()
            if key.lower().startswith("x-ratelimit") or key.lower() == "retry-after"
        }
        response.raise_for_status()
        payload = response.json()
        usage = payload.get("usage", {})

        return Completion(
            text=payload["choices"][0]["message"]["content"],
            model=model,
            input_tokens=int(usage.get("prompt_tokens", policy.estimate_tokens(prompt))),
            output_tokens=int(usage.get("completion_tokens", 0)),
            latency_ms=(time.perf_counter() - started) * 1000,
            provider=self.name,
        )

    async def aclose(self) -> None:
        await self._client.aclose()


class ProviderPool:
    """Primary provider with an automatic fallback to the mock.

    Deliberately fails *open*: a Groq outage degrades answer quality but keeps the
    gateway serving, and `Completion.provider` records what really happened so the
    dashboard never misrepresents a mocked answer as a real one.
    """

    def __init__(self) -> None:
        self.mock = MockProvider()
        self.primary: GroqProvider | None = None
        self.fallback_count = 0

        if not settings.use_mock:
            self.primary = GroqProvider(
                api_key=settings.groq_api_key,
                base_url=settings.groq_base_url,
                timeout=settings.request_timeout_s,
            )

    @property
    def mode(self) -> str:
        return "groq" if self.primary else "mock"

    async def complete(self, model: str, prompt: str) -> Completion:
        if self.primary is None:
            return await self.mock.complete(model, prompt)
        try:
            return await self.primary.complete(model, prompt)
        except Exception as exc:  # noqa: BLE001 - any provider failure degrades to mock
            self.fallback_count += 1
            log.warning("groq call failed (%s); falling back to mock", exc)
            return await self.mock.complete(model, prompt)

    async def aclose(self) -> None:
        if self.primary:
            await self.primary.aclose()
