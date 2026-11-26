"""End-to-end, zero-API ATC-to-worker integration smoke test."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.atc_worker_bridge_v1 import ATCWorkerBridgeV1


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="advait-atc-bridge-") as temp:
        bridge = ATCWorkerBridgeV1(temp)
        plan = bridge.plan("Count words in a sample text using a local tool")
        task_id = bridge.enqueue_local_tool(
            plan,
            {
                "name": "text.counter",
                "version": "1.0.0",
                "operation": "text.word_count",
                "description": "Counts words in bounded local text",
            },
            {"text": "Advait connects its planner to its local worker"},
        )
        outcome = bridge.run_once()
        report = bridge.report(task_id)
        result = {
            "plan_status": plan["status"],
            "plan_execution_status": plan["execution_status"],
            "worker_outcome": outcome,
            "task_report": report,
            "api_calls": 0,
            "external_actions": 0,
        }
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if outcome.get("status") == "done" and report["status"] == "done" else 1


if __name__ == "__main__":
    raise SystemExit(main())
