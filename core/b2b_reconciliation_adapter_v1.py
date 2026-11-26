"""Governed adapter for the pinned Advait B2B CSV reconciler."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
from typing import Any

from core.financial_record_vault_v1 import FinancialRecordVaultV1


VERIFICATION_TYPE = "b2b_csv_reconcile_v1"
ADAPTER_NAME = "b2b.csv_reconcile.v1"


class B2BAdapterUnavailable(RuntimeError):
    pass


def _load_pinned_reconciler():
    repository_root = Path(__file__).resolve().parents[1]
    submodule_root = repository_root / "vendor" / "advait_b2b"
    if submodule_root.is_symlink() or not submodule_root.is_dir():
        raise B2BAdapterUnavailable("pinned_advait_b2b_submodule_not_initialized")
    module_path = submodule_root / "b2b_reconcile.py"
    if module_path.is_symlink() or not module_path.is_file():
        raise B2BAdapterUnavailable("pinned_advait_b2b_module_missing")
    spec = importlib.util.spec_from_file_location(
        "_advait_pinned_b2b_reconcile_v1", module_path
    )
    if spec is None or spec.loader is None:
        raise B2BAdapterUnavailable("pinned_advait_b2b_module_load_failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    reconcile = getattr(module, "reconcile_text", None)
    if not callable(reconcile):
        raise B2BAdapterUnavailable("pinned_b2b_reconcile_text_contract_missing")
    return reconcile


class B2BReconciliationAdapterV1:
    """Source CSV and reports stay in a separate file vault, never in task payload/result."""

    def __init__(self, vault_root: str | Path, *, reconciler=None):
        self.reconciler = reconciler if reconciler is not None else _load_pinned_reconciler()
        if not callable(self.reconciler):
            raise TypeError("reconciler must be callable")
        self.vault = FinancialRecordVaultV1(vault_root)

    def stage_csv(self, content: bytes) -> dict[str, Any]:
        return self.vault.stage_csv(content)

    def worker_handlers(self):
        return {ADAPTER_NAME: self.handle}

    def _build_report(self, input_artifact_id: str):
        raw = self.vault.read_input(input_artifact_id)
        text = raw.decode("utf-8-sig")
        report = self.reconciler(text)
        required = {
            "rows_checked", "flags", "severity_counts", "rule_counts",
            "normalized_csv", "exceptions_csv", "summary",
        }
        if not isinstance(report, dict) or not required.issubset(report):
            raise ValueError("b2b_reconciler_report_contract_invalid")
        if (
            not isinstance(report["rows_checked"], int) or isinstance(report["rows_checked"], bool)
            or not isinstance(report["flags"], int) or isinstance(report["flags"], bool)
            or report["rows_checked"] < 0 or report["flags"] < 0
        ):
            raise ValueError("b2b_reconciler_counts_invalid")
        if not isinstance(report["severity_counts"], dict) or not isinstance(report["rule_counts"], dict):
            raise ValueError("b2b_reconciler_breakdown_invalid")
        for key in ("normalized_csv", "exceptions_csv", "summary"):
            if not isinstance(report[key], str):
                raise ValueError("b2b_reconciler_artifact_invalid")
        return raw, report

    @staticmethod
    def _metadata(input_artifact_id: str, input_sha256: str, report: dict[str, Any],
                  artifact_set: dict[str, Any]) -> dict[str, Any]:
        return {
            "adapter": ADAPTER_NAME,
            "input_artifact_id": input_artifact_id,
            "input_sha256": input_sha256,
            "artifact_set_id": artifact_set["artifact_set_id"],
            "rows_checked": report["rows_checked"],
            "flags": report["flags"],
            "severity_counts": report["severity_counts"],
            "rule_counts": report["rule_counts"],
            "output_sha256": artifact_set["sha256"],
        }

    def handle(self, data: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(data, dict) or set(data) != {"input_artifact_id"}:
            raise ValueError("b2b_handler_requires_only_input_artifact_id")
        input_artifact_id = data["input_artifact_id"]
        raw, report = self._build_report(input_artifact_id)
        input_sha256 = hashlib.sha256(raw).hexdigest()
        artifact_set = self.vault.store_outputs(input_sha256, report)
        result = self._metadata(input_artifact_id, input_sha256, report, artifact_set)
        evidence = {
            "verification_type": VERIFICATION_TYPE,
            **result,
        }
        return {"result": result, "evidence": evidence}

    def verify_evidence(self, task_id: str, result: dict, evidence: dict) -> bool:
        try:
            if not isinstance(task_id, str) or not task_id:
                return False
            if not isinstance(result, dict) or not isinstance(evidence, dict):
                return False
            if evidence.get("verification_type") != VERIFICATION_TYPE:
                return False
            input_artifact_id = evidence.get("input_artifact_id")
            raw, report = self._build_report(input_artifact_id)
            input_sha256 = hashlib.sha256(raw).hexdigest()
            artifact_set_id = hashlib.sha256(
                f"b2b-reconcile-v1:{input_sha256}".encode("ascii")
            ).hexdigest()
            actual_outputs = self.vault.read_outputs(artifact_set_id)
            expected_outputs = {
                "normalized_csv": report["normalized_csv"].encode("utf-8"),
                "exceptions_csv": report["exceptions_csv"].encode("utf-8"),
                "summary": report["summary"].encode("utf-8"),
            }
            if actual_outputs != expected_outputs:
                return False
            expected_artifact_set = {
                "artifact_set_id": artifact_set_id,
                "sha256": {
                    key: hashlib.sha256(value).hexdigest()
                    for key, value in expected_outputs.items()
                },
            }
            expected_result = self._metadata(
                input_artifact_id, input_sha256, report, expected_artifact_set
            )
            expected_evidence = {
                "verification_type": VERIFICATION_TYPE,
                **expected_result,
            }
            return result == expected_result and evidence == expected_evidence
        except Exception:
            return False
