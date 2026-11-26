"""Manual, bounded OpenRouter :free smoke test. Never prints prompt or model output."""
from __future__ import annotations
import argparse
import os
import re
import sys
from pathlib import Path

from core.provider_router_v1 import (
    ProviderCallLedger, ProviderRouterV1, ProviderPolicyError, ProviderRequestError,
)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9._/-]{1,180}:free", args.model):
        print("BLOCKED: model identifier must end exactly in :free and contain only safe identifier characters.")
        return 2
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("BLOCKED: OPENROUTER_API_KEY is not configured.")
        return 2
    audit_dir = Path("artifacts")
    audit_dir.mkdir(exist_ok=True)
    ledger = ProviderCallLedger(audit_dir / "openrouter_smoke_audit.db")
    router = ProviderRouterV1(ledger=ledger)
    try:
        result = router.call(
            provider="openrouter",
            model=args.model,
            messages=[{"role": "user", "content": "Reply with exactly: ADV AIT FREE PROVIDER CHECK OK"}],
            temperature=0,
            max_tokens=32,
        )
    except (ProviderPolicyError, ProviderRequestError) as exc:
        print("SMOKE_TEST_FAILED:", str(exc))
        return 1
    print("SMOKE_TEST_PASSED")
    print("provider:", result.provider)
    print("model:", result.model)
    print("latency_ms:", result.latency_ms)
    print("usage_metadata_available:", bool(result.usage))
    print("response_content: [not displayed]")
    print("audit_database: artifacts/openrouter_smoke_audit.db")
    return 0

if __name__ == "__main__":
    sys.exit(main())
