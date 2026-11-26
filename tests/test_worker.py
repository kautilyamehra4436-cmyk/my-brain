import json
import tempfile
import unittest
from core.managed_sqlite_v1 import managed_connection
from pathlib import Path

from core.task_queue import TaskQueue
from core.worker import BoundedWorker


def accepted(task_id, result, evidence):
    return (
        bool(task_id)
        and evidence.get("fixture") == "synthetic"
        and result.get("value") == evidence.get("expected_value")
    )


def echo_handler(data):
    return {
        "result": {"value": data["value"]},
        "evidence": {"fixture": "synthetic", "expected_value": data["value"]},
    }


class BoundedWorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.queue = TaskQueue(Path(self.temp.name) / "worker.db")

    def tearDown(self):
        self.temp.cleanup()

    def enqueue(self, **overrides):
        payload = {
            "execution_mode": "bounded_adapter",
            "adapter": "fixture.echo",
            "action": "local_analysis",
            "estimated_cost": 0,
            "free_quota_available": True,
            "risk": "low",
            "input": {"value": "verified"},
        }
        payload.update(overrides)
        return self.queue.enqueue("Bounded fixture task", payload)

    def worker(self, **kwargs):
        return BoundedWorker(
            self.queue,
            {"fixture.echo": echo_handler},
            evidence_verifier=kwargs.get("evidence_verifier", accepted),
            owner_approval_verifier=kwargs.get("owner_approval_verifier"),
        )

    def test_executes_allowlisted_handler_and_verifies_result(self):
        plan_id = self.queue.enqueue("ATC plan-only step", {"status": "plan_only"})
        task_id = self.enqueue()
        outcome = self.worker().run_once()
        self.assertEqual(outcome["status"], "done")
        self.assertEqual(outcome["task_id"], task_id)
        self.assertEqual(self.queue.list_tasks(status="done")[0]["id"], task_id)
        self.assertEqual(self.queue.list_tasks(status="pending")[0]["id"], plan_id)

    def test_no_eligible_task_is_idle_and_plan_remains_pending(self):
        plan_id = self.queue.enqueue("ATC plan-only step", {"status": "plan_only"})
        outcome = self.worker().run_once()
        self.assertEqual(outcome["status"], "idle")
        self.assertEqual(self.queue.list_tasks(status="pending")[0]["id"], plan_id)

    def test_unknown_adapter_fails_closed(self):
        task_id = self.enqueue(adapter="unregistered.adapter")
        outcome = self.worker().run_once()
        self.assertEqual(outcome["status"], "failed")
        self.assertEqual(self.queue.list_tasks(status="failed")[0]["id"], task_id)

    def test_positive_cost_fails_closed(self):
        task_id = self.enqueue(estimated_cost="0.01")
        outcome = self.worker().run_once()
        self.assertEqual(outcome["status"], "failed")
        self.assertEqual(self.queue.list_tasks(status="failed")[0]["id"], task_id)

    def test_quota_exhaustion_fails_closed(self):
        task_id = self.enqueue(free_quota_available=False)
        outcome = self.worker().run_once()
        self.assertEqual(outcome["status"], "failed")
        self.assertEqual(self.queue.list_tasks(status="failed")[0]["id"], task_id)

    def test_high_risk_without_authenticated_owner_verifier_fails_closed(self):
        task_id = self.enqueue(risk="high")
        outcome = self.worker().run_once()
        self.assertEqual(outcome["status"], "failed")
        self.assertEqual(outcome["reason"], "owner_verifier_unavailable")
        self.assertEqual(self.queue.list_tasks(status="failed")[0]["id"], task_id)

    def test_high_risk_requires_out_of_band_owner_approval(self):
        task_id = self.enqueue(risk="high")
        owner_calls = []
        worker = self.worker(owner_approval_verifier=lambda tid, action, payload: (
            owner_calls.append((tid, action, payload))
            or (tid == task_id and action == "local_analysis"
                and "approval_token" not in payload)
        ))
        outcome = worker.run_once()
        self.assertEqual(outcome["status"], "done")
        self.assertEqual(owner_calls[0][0:2], (task_id, "local_analysis"))
        self.assertNotIn("approval_token", owner_calls[0][2])
        self.assertEqual(self.queue.list_tasks(status="done")[0]["id"], task_id)

    def test_missing_independent_verifier_fails_closed(self):
        task_id = self.enqueue()
        outcome = self.worker(evidence_verifier=None).run_once()
        self.assertEqual(outcome["status"], "failed")
        self.assertEqual(outcome["reason"], "evidence_verifier_unavailable")
        self.assertEqual(self.queue.list_tasks(status="failed")[0]["id"], task_id)

    def test_handler_exception_message_is_not_persisted(self):
        task_id = self.enqueue()
        worker = BoundedWorker(
            self.queue,
            {"fixture.echo": lambda _: (_ for _ in ()).throw(RuntimeError("SECRET customer-row data"))},
            evidence_verifier=accepted,
        )
        outcome = worker.run_once()
        self.assertEqual(outcome["status"], "failed")
        self.assertEqual(outcome["reason"], "runtimeerror_execution_failed")
        failed = self.queue.list_tasks(status="failed")[0]
        self.assertEqual(failed["id"], task_id)
        self.assertNotIn("SECRET", failed["error"])
        self.assertNotIn("customer-row", failed["error"])
        self.assertNotIn("SECRET", str(self.queue.audit_events()))

    def test_enqueue_rejects_nested_secret_material(self):
        with self.assertRaisesRegex(ValueError, "sensitive_material"):
            self.queue.enqueue("Unsafe task", {"input": {"approval_token": "do-not-store"}})
        with self.assertRaisesRegex(ValueError, "sensitive_material"):
            self.queue.enqueue("Unsafe task", {"nested": [{"API-Key": "do-not-store"}]})
        with self.assertRaisesRegex(ValueError, "sensitive_material"):
            self.queue.enqueue("Unsafe task", {"input": "Bearer abcdefghijklmnopqrstuvwxyz"})

    def test_enqueue_rejects_oversized_payload(self):
        with self.assertRaisesRegex(ValueError, "payload_too_large"):
            self.queue.enqueue("Large task", {"input": "x" * 70000})

    def test_legacy_sensitive_payload_fails_closed(self):
        task_id = self.enqueue(risk="high")
        task = self.queue.list_tasks(status="pending")[0]
        payload = json.loads(task["payload"])
        payload["approval_token"] = "legacy-persisted-token"
        with managed_connection(self.queue.db_path) as con:
            con.execute("UPDATE tasks SET payload=? WHERE id=?", (json.dumps(payload), task_id))
        outcome = self.worker(owner_approval_verifier=lambda *_: True).run_once()
        self.assertEqual(outcome["status"], "failed")
        failed = self.queue.list_tasks(status="failed")[0]
        self.assertNotIn("legacy-persisted-token", failed["error"])
        self.assertEqual(json.loads(failed["payload"]), {})
        self.assertNotIn("legacy-persisted-token", str(self.queue.audit_events()))

    def test_sensitive_handler_result_is_not_persisted(self):
        task_id = self.enqueue()
        worker = BoundedWorker(
            self.queue,
            {"fixture.echo": lambda _: {
                "result": {"api_key": "SECRET_VALUE"},
                "evidence": {"fixture": "synthetic", "expected_value": "verified"},
            }},
            evidence_verifier=accepted,
        )
        outcome = worker.run_once()
        self.assertEqual(outcome["status"], "failed")
        self.assertEqual(outcome["reason"], "sensitive_output_blocked")
        failed = self.queue.list_tasks(status="failed")[0]
        self.assertEqual(failed["id"], task_id)
        self.assertIsNone(failed["result"])
        self.assertNotIn("SECRET_VALUE", str(self.queue.audit_events()))

    def test_task_failure_error_is_sanitized(self):
        task_id = self.enqueue()
        self.queue.claim_next(eligible=lambda p: p.get("execution_mode") == "bounded_adapter")
        self.queue.fail(task_id, "SECRET=customer-sensitive-value")
        failed = self.queue.list_tasks(status="failed")[0]
        self.assertEqual(failed["error"], "task_failed")
        self.assertNotIn("customer-sensitive-value", str(self.queue.audit_events()))
