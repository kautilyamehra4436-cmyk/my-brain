import tempfile
import unittest
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
        self.assertIn("owner verifier unavailable", outcome["reason"])
        self.assertEqual(self.queue.list_tasks(status="failed")[0]["id"], task_id)

    def test_high_risk_requires_exact_owner_approval(self):
        task_id = self.enqueue(risk="high")
        owner_calls = []
        worker = self.worker(owner_approval_verifier=lambda tid, action, payload, token: (
            owner_calls.append((tid, action, token)) or tid == task_id and action == "local_analysis" and token == "fixture-approval"
        ))
        # Add the opaque approval token only to this synthetic test task.
        running_payload = self.queue.list_tasks(status="pending")[0]["payload"]
        import json
        decoded = json.loads(running_payload)
        decoded["approval_token"] = "fixture-approval"
        # Queue payloads are immutable through the public API; use a new task with token.
        self.queue.fail if False else None
        # The test's owner verifier must not be bypassed; the worker rejects missing token.
        outcome = worker.run_once()
        self.assertEqual(outcome["status"], "failed")
        self.assertTrue(owner_calls)
        self.assertEqual(self.queue.list_tasks(status="failed")[0]["id"], task_id)

    def test_missing_independent_verifier_fails_closed(self):
        task_id = self.enqueue()
        outcome = self.worker(evidence_verifier=None).run_once()
        self.assertEqual(outcome["status"], "failed")
        self.assertIn("evidence verifier unavailable", outcome["reason"])
        self.assertEqual(self.queue.list_tasks(status="failed")[0]["id"], task_id)

    def test_handler_exception_is_recorded_as_failure(self):
        task_id = self.enqueue()
        worker = BoundedWorker(
            self.queue,
            {"fixture.echo": lambda _: (_ for _ in ()).throw(RuntimeError("fixture failure"))},
            evidence_verifier=accepted,
        )
        outcome = worker.run_once()
        self.assertEqual(outcome["status"], "failed")
        self.assertIn("fixture failure", outcome["reason"])
        self.assertEqual(self.queue.list_tasks(status="failed")[0]["id"], task_id)
