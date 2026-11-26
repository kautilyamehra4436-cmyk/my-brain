import tempfile
import unittest
from pathlib import Path
from core.zero_cost_guard import evaluate
from core.task_queue import TaskQueue


class GuardTests(unittest.TestCase):
    def test_free_action_allowed(self):
        self.assertTrue(evaluate("research", 0).allowed)

    def test_positive_cost_blocked_even_approval(self):
        self.assertFalse(evaluate("research", 0.01, owner_approved=True).allowed)

    def test_payment_blocked(self):
        self.assertFalse(evaluate("payment", 0).allowed)

    def test_quota_exhausted_blocks(self):
        self.assertFalse(evaluate("research", 0, free_quota_available=False).allowed)

    def test_invalid_cost_fails_closed(self):
        self.assertFalse(evaluate("research", "unknown").allowed)


class QueueTests(unittest.TestCase):
    def test_queue_lifecycle_requires_verified_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            q = TaskQueue(Path(d) / "test.db")
            tid = q.enqueue("Sample", {"n": 1})
            task = q.claim_next()
            self.assertEqual(task["id"], tid)
            self.assertEqual(task["status"], "running")

            with self.assertRaises(PermissionError):
                q.complete(tid, {"ok": True})

            q.complete(
                tid,
                {"ok": True},
                evidence={"fixture": "synthetic", "acceptance": "passed"},
                verifier=lambda task_id, result, evidence: (
                    task_id == tid and result.get("ok") is True
                    and evidence.get("acceptance") == "passed"
                ),
            )
            stored = q.list_tasks()[0]
            self.assertEqual(stored["status"], "done")
            self.assertTrue(stored["evidence_sha256"])
            events = [x["event"] for x in q.audit_events()]
            self.assertEqual(events, ["enqueue", "claim", "complete_verified"])

    def test_rejected_evidence_does_not_complete(self):
        with tempfile.TemporaryDirectory() as d:
            q = TaskQueue(Path(d) / "test.db")
            tid = q.enqueue("Sample")
            q.claim_next()
            with self.assertRaises(PermissionError):
                q.complete(
                    tid, {"ok": True}, evidence={"claim": "untrusted"},
                    verifier=lambda *_: False,
                )
            self.assertEqual(q.list_tasks()[0]["status"], "running")

    def test_non_json_evidence_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            q = TaskQueue(Path(d) / "test.db")
            tid = q.enqueue("Sample")
            q.claim_next()
            with self.assertRaises(ValueError):
                q.complete(
                    tid, {"ok": True}, evidence={"bad": float("nan")},
                    verifier=lambda *_: True,
                )
            self.assertEqual(q.list_tasks()[0]["status"], "running")

    def test_blank_title_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                TaskQueue(Path(d) / "x.db").enqueue("  ")


if __name__ == "__main__":
    unittest.main()
