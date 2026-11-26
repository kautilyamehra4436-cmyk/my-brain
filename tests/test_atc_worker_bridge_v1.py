import tempfile
import unittest
from pathlib import Path

from core.atc_worker_bridge_v1 import ATCWorkerBridgeError, ATCWorkerBridgeV1


class ATCWorkerBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.bridge = ATCWorkerBridgeV1(Path(self.temp.name))

    def tearDown(self):
        self.temp.cleanup()

    def plan(self):
        return self.bridge.plan("Count words in a sample text using a local tool")

    def spec(self):
        return {
            "name": "text.counter",
            "version": "1.0.0",
            "operation": "text.word_count",
            "description": "Counts words in bounded local text",
        }

    def test_plan_is_draft_and_does_not_enqueue_or_execute(self):
        plan = self.plan()
        self.assertEqual(plan["status"], "DRAFT_PLAN")
        self.assertEqual(plan["execution_status"], "NOT_EXECUTED")
        self.assertEqual(self.bridge.runtime.queue.list_tasks(), [])

    def test_explicit_bridge_executes_allowlisted_local_tool_end_to_end(self):
        plan = self.plan()
        task_id = self.bridge.enqueue_local_tool(
            plan, self.spec(), {"text": "Advait can now connect planning and work"}
        )
        self.assertEqual(self.bridge.task_status(task_id)["status"], "pending")
        outcome = self.bridge.run_once()
        self.assertEqual(outcome["status"], "done")
        report = self.bridge.report(task_id)
        self.assertEqual(report["status"], "done")
        self.assertEqual(report["atc_record_id"], plan["record_id"])
        self.assertEqual(report["result"]["output"]["words"], 7)
        self.assertTrue(report["evidence_sha256"])

    def test_risk_flagged_plan_cannot_cross_bridge(self):
        plan = self.bridge.plan("Send payment to the vendor")
        with self.assertRaisesRegex(ATCWorkerBridgeError, "owner_review_required"):
            self.bridge.enqueue_local_tool(plan, self.spec(), {"text": "blocked"})
        self.assertEqual(self.bridge.runtime.queue.list_tasks(), [])

    def test_non_allowlisted_tool_is_rejected_before_enqueue(self):
        plan = self.plan()
        bad = {**self.spec(), "operation": "shell.execute"}
        with self.assertRaises(ValueError):
            self.bridge.enqueue_local_tool(plan, bad, {"command": "echo unsafe"})
        self.assertEqual(self.bridge.runtime.queue.list_tasks(), [])

    def test_modified_or_executed_plan_is_rejected(self):
        plan = self.plan()
        plan["execution_status"] = "DONE"
        with self.assertRaisesRegex(ATCWorkerBridgeError, "unexecuted_draft"):
            self.bridge.enqueue_local_tool(plan, self.spec(), {"text": "x"})


if __name__ == "__main__":
    unittest.main()
