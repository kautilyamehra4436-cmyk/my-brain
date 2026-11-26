"""Run Advait AI Developer v2 with prior verified lessons loaded."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.governed_ai_developer_v2 import GovernedAIDeveloperV2
from core.managed_provider_call_ledger_v2 import ManagedProviderCallLedgerV2
from core.provider_router_v1 import ProviderRouterV1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--audit-db", required=True)
    args = parser.parse_args()
    if not args.model.endswith(":free"):
        parser.error("model must end in :free; paid models are blocked")
    audit_db = Path(args.audit_db)
    output = Path(args.output)
    audit_db.parent.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    ledger = ManagedProviderCallLedgerV2(str(audit_db))
    router = ProviderRouterV1(ledger=ledger)
    agent = GovernedAIDeveloperV2(root=ROOT, router=router)
    report = agent.run(model=args.model)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "completed_read_only_with_lessons",
        "finding_count": report["finding_count"],
        "source_scope": report["source_scope"],
        "output": str(output),
        "lessons_loaded": True
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
