"""Zero-network integration smoke for the pinned Advait B2B CSV submodule."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.atc_worker_bridge_managed_v3 import ATCWorkerBridgeManagedV3


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    sample = root / "vendor" / "advait_b2b" / "b2b_sample_input.csv"
    if not sample.is_file() or sample.is_symlink():
        raise RuntimeError("pinned_b2b_sample_missing_or_invalid")

    with tempfile.TemporaryDirectory() as tmp:
        bridge = ATCWorkerBridgeManagedV3(tmp)
        if not bridge.runtime.b2b_adapter_available:
            raise RuntimeError("pinned_b2b_adapter_unavailable")
        staged = bridge.stage_b2b_csv(
            sample.read_bytes(), owner_consented=True, allow_unencrypted_storage=True
        )
        task_id = bridge.enqueue_b2b_reconciliation(
            staged["artifact_id"], owner_confirmed=True
        )
        outcome = bridge.run_once()
        report = bridge.report(task_id)
        if outcome.get("status") != "done" or report.get("status") != "done":
            raise RuntimeError("b2b_integration_task_not_verified")
        result = report["result"]
        if result.get("rows_checked") != 5 or result.get("flags", 0) < 1:
            raise RuntimeError("b2b_sample_result_unexpected")
        if "INV-001" in json.dumps(result) or "North Traders" in json.dumps(result):
            raise RuntimeError("source_row_leaked_into_operational_task_result")
        artifacts = bridge.runtime.b2b_adapter.vault.read_outputs(result["artifact_set_id"])
        if not all(artifacts.values()):
            raise RuntimeError("b2b_output_artifact_missing")
        print(json.dumps({
            "status": "done_verified",
            "rows_checked": result["rows_checked"],
            "flags": result["flags"],
            "artifact_set_id": result["artifact_set_id"],
            "evidence_sha256": report["evidence_sha256"],
            "source_rows_persisted_in_task_queue": False,
        }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
