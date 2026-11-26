"""Run Advait's read-only, evidence-bound AI Developer audit."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.governed_ai_developer_v1 import GovernedAIDeveloperV1, ManagedProviderCallLedger
from core.provider_router_v1 import ProviderRouterV1

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--audit-db", required=True)
    args = parser.parse_args()
    if not args.model.endswith(":free"):
        parser.error("model must end in :free; paid models are blocked")
    ledger = ManagedProviderCallLedger(args.audit_db)
    router = ProviderRouterV1(ledger=ledger)
    agent = GovernedAIDeveloperV1(root=ROOT, router=router)
    report = agent.run(model=args.model)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "completed_read_only",
        "finding_count": report["finding_count"],
        "source_scope": report["source_scope"],
        "output": str(output)
    }, ensure_ascii=False, sort_keys=True))

if __name__ == "__main__":
    main()
