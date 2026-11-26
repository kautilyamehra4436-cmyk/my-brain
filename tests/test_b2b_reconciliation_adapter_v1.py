import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from core.b2b_reconciliation_adapter_v1 import B2BReconciliationAdapterV1
from core.financial_record_vault_v1 import FinancialRecordVaultV1, FinancialVaultError
from core.governed_self_build_runtime_v3 import GovernedSelfBuildRuntimeV3


SOURCE = b"invoice_id,vendor,amount,po_ref\nI-1,PRIVATE_VENDOR,10,P-1\n"


def fake_reconciler(csv_text):
    if "PRIVATE_VENDOR" not in csv_text:
        raise ValueError("unexpected test input")
    return {
        "rows_checked": 1,
        "flags": 0,
        "severity_counts": {},
        "rule_counts": {},
        "normalized_csv": "invoice_id,vendor,amount,po_ref\nI-1,PRIVATE_VENDOR,10,P-1\n",
        "exceptions_csv": "row_number,invoice_id,rule,severity,field,observed,expected,detail\n",
        "summary": "Rows checked: 1\nFlags: 0\n",
        "findings": [],
    }


class B2BAdapterVaultTests(unittest.TestCase):
    def test_stage_and_read_use_private_separate_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = FinancialRecordVaultV1(Path(tmp) / "financial_vault_v1")
            staged = vault.stage_csv(SOURCE)
            source_path = vault.input_dir / f"{staged['artifact_id']}.csv"
            self.assertEqual(vault.read_input(staged["artifact_id"]), SOURCE)
            self.assertEqual(stat.S_IMODE(source_path.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(vault.root.stat().st_mode), 0o700)

    def test_adapter_returns_metadata_only_and_verifies_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = B2BReconciliationAdapterV1(
                Path(tmp) / "financial_vault_v1", reconciler=fake_reconciler
            )
            staged = adapter.stage_csv(SOURCE)
            output = adapter.handle({"input_artifact_id": staged["artifact_id"]})
            result, evidence = output["result"], output["evidence"]
            self.assertNotIn("PRIVATE_VENDOR", json.dumps(result))
            self.assertNotIn("PRIVATE_VENDOR", json.dumps(evidence))
            self.assertEqual(result["rows_checked"], 1)
            self.assertTrue(adapter.verify_evidence("task-1", result, evidence))
            files = adapter.vault.read_outputs(result["artifact_set_id"])
            self.assertIn(b"PRIVATE_VENDOR", files["normalized_csv"])

    def test_retries_are_idempotent_for_same_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = B2BReconciliationAdapterV1(
                Path(tmp) / "financial_vault_v1", reconciler=fake_reconciler
            )
            staged = adapter.stage_csv(SOURCE)
            first = adapter.handle({"input_artifact_id": staged["artifact_id"]})
            second = adapter.handle({"input_artifact_id": staged["artifact_id"]})
            self.assertEqual(first, second)

    def test_tampered_output_fails_evidence_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = B2BReconciliationAdapterV1(
                Path(tmp) / "financial_vault_v1", reconciler=fake_reconciler
            )
            staged = adapter.stage_csv(SOURCE)
            output = adapter.handle({"input_artifact_id": staged["artifact_id"]})
            result, evidence = output["result"], output["evidence"]
            target = adapter.vault.output_dir / result["artifact_set_id"] / "normalized.csv"
            target.write_bytes(b"tampered")
            self.assertFalse(adapter.verify_evidence("task-1", result, evidence))

    def test_invalid_artifact_ids_and_symlinks_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = FinancialRecordVaultV1(Path(tmp) / "vault")
            with self.assertRaises(ValueError):
                vault.read_input("../outside")
            outside = Path(tmp) / "outside.csv"
            outside.write_bytes(SOURCE)
            link_id = "a" * 32
            (vault.input_dir / f"{link_id}.csv").symlink_to(outside)
            with self.assertRaises(FinancialVaultError):
                vault.read_input(link_id)

    def test_runtime_requires_explicit_owner_consent_and_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = GovernedSelfBuildRuntimeV3(tmp, b2b_reconciler=fake_reconciler)
            with self.assertRaises(PermissionError):
                runtime.stage_b2b_csv(SOURCE)
            staged = runtime.stage_b2b_csv(SOURCE, owner_consented=True)
            with self.assertRaises(PermissionError):
                runtime.enqueue_b2b_reconciliation(staged["artifact_id"])

    def test_queue_and_result_do_not_contain_financial_source_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = GovernedSelfBuildRuntimeV3(tmp, b2b_reconciler=fake_reconciler)
            staged = runtime.stage_b2b_csv(SOURCE, owner_consented=True)
            task_id = runtime.enqueue_b2b_reconciliation(
                staged["artifact_id"], owner_confirmed=True
            )
            task = runtime.queue.list_tasks()[0]
            self.assertNotIn("PRIVATE_VENDOR", task["payload"])
            payload = json.loads(task["payload"])
            self.assertEqual(payload["input"], {"input_artifact_id": staged["artifact_id"]})
            outcome = runtime.run_once()
            self.assertEqual(outcome["status"], "done")
            completed = next(item for item in runtime.queue.list_tasks() if item["id"] == task_id)
            result = json.loads(completed["result"])
            self.assertNotIn("PRIVATE_VENDOR", completed["result"])
            self.assertEqual(result["rows_checked"], 1)
            self.assertEqual(completed["status"], "done")


if __name__ == "__main__":
    unittest.main()
