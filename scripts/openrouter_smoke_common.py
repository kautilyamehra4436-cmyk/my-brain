"""Canonical OpenRouter smoke adapter; no retries, paid fallback or content logging."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.provider_router_v1 import (
    ProviderCallLedger,
    ProviderPolicyError,
    ProviderRequestError,
    ProviderRouterV1,
)

MODEL_PATTERN = re.compile(r"^[A-Za-z0-9._/-]{1,180}:free$")


def run_smoke(version: str, model: str, timeout_seconds: int, *, router=None) -> int:
    if version not in {"v3", "v4"}:
        print("BLOCKED: unsupported smoke version.")
        return 2
    if not isinstance(model, str) or not MODEL_PATTERN.fullmatch(model):
        print("BLOCKED: model identifier must end exactly in :free.")
        return 2
    if router is None:
        if not os.environ.get("OPENROUTER_API_KEY"):
            print("BLOCKED: OPENROUTER_API_KEY is missing.")
            return 2
        audit_path = Path("artifacts") / f"openrouter_smoke_audit_{version}.db"
        ledger = ProviderCallLedger(audit_path)
        router = ProviderRouterV1(ledger=ledger, policy={"timeout_seconds": timeout_seconds})
    try:
        result = router.call(
            provider="openrouter",
            model=model,
            messages=[{"role": "user", "content": "Reply with exactly the word OK."}],
            temperature=0,
            max_tokens=128,
            reasoning_enabled=False,
        )
    except (ProviderPolicyError, ProviderRequestError) as exc:
        print("SMOKE_TEST_FAILED:", str(exc)[:100])
        return 1
    if not result.text.strip():
        print("SMOKE_TEST_FAILED: empty_text")
        return 1
    print("SMOKE_TEST_PASSED")
    print("provider:", result.provider)
    print("model:", result.model)
    print("latency_ms:", result.latency_ms)
    print("zero_cost_verified:", result.usage.get("cost") in (0, 0.0, "0", "0.0"))
    print("usage_metadata_available:", bool(result.usage))
    print("response_content: [not displayed]")
    print(f"audit_database: artifacts/openrouter_smoke_audit_{version}.db")
    return 0
