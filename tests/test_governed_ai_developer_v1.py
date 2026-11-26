import json
import tempfile
import unittest
from pathlib import Path

from core.governed_ai_developer_v1 import (
    AuditInputError, GovernedAIDeveloperV1, ManagedProviderCallLedger
)

class GovernedAIDeveloperTests(unittest.TestCase):
    def test_valid_report_requires_verbatim_evidence(self):
        sources = [{"path": "core/task_queue.py", "source": "def run():\n    pass\n"}]
        raw = json.dumps({"findings": [{
            "path": "core/task_queue.py", "line_start": 1, "line_end": 2,
            "evidence": "def run():\n    pass", "finding": "Example finding",
            "impact": "Example impact", "recommendation": "Review the function"
        }]})
        report = GovernedAIDeveloperV1.validate_report(raw, sources)
        self.assertEqual(report["finding_count"], 1)
        self.assertFalse(report["findings"][0]["auto_patch"])
        self.assertEqual(report["findings"][0]["status"], "REVIEW_REQUIRED")

    def test_rejects_non_verbatim_evidence(self):
        sources = [{"path": "core/task_queue.py", "source": "def run():\n    pass\n"}]
        raw = json.dumps({"findings": [{
            "path": "core/task_queue.py", "line_start": 1, "line_end": 1,
            "evidence": "invented code", "finding": "x", "impact": "y", "recommendation": "z"
        }]})
        with self.assertRaises(AuditInputError):
            GovernedAIDeveloperV1.validate_report(raw, sources)

    def test_rejects_unallowlisted_path(self):
        sources = [{"path": "core/task_queue.py", "source": "x\n"}]
        raw = json.dumps({"findings": [{
            "path": "../secrets.txt", "line_start": 1, "line_end": 1,
            "evidence": "x", "finding": "x", "impact": "y", "recommendation": "z"
        }]})
        with self.assertRaises(AuditInputError):
            GovernedAIDeveloperV1.validate_report(raw, sources)

    def test_rejects_malformed_model_output(self):
        with self.assertRaises(AuditInputError):
            GovernedAIDeveloperV1.validate_report("not json", [])

    def test_managed_provider_ledger_closes_connections(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = ManagedProviderCallLedger(Path(tmp) / "provider.db")
            ledger.append(
                request_id="r1", provider="openrouter", model="x:free",
                request_sha256="a" * 64, response_sha256="b" * 64,
                status="success", latency_ms=1, usage={}
            )
            self.assertEqual(len(ledger.events()), 1)

if __name__ == "__main__":
    unittest.main()
