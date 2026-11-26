import gc
import tempfile
import unittest
import warnings
from pathlib import Path

from core.atc_worker_bridge_managed_v1 import ATCWorkerBridgeManagedV1
from core.managed_task_queue_v1 import ManagedTaskQueueV1


class ManagedRuntimeTests(unittest.TestCase):
    def test_managed_queue_api_and_status(self):
        with tempfile.TemporaryDirectory() as temp:
            queue = ManagedTaskQueueV1(Path(temp) / "tasks.db")
            task_id = queue.enqueue("sample", {"execution_mode": "plan_only"})
            self.assertEqual(queue.list_tasks()[0]["id"], task_id)
            self.assertEqual(queue.claim_next(eligible=lambda p: False), None)
            self.assertEqual(queue.list_tasks(status="pending")[0]["id"], task_id)

    def test_managed_bridge_executes_local_tool_and_reports_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            bridge = ATCWorkerBridgeManagedV1(temp)
            plan = bridge.plan("Count words in a sample text using a local tool")
            task_id = bridge.enqueue_local_tool(
                plan,
                {"name":"text.counter","version":"1.0.0",
                 "operation":"text.word_count",
                 "description":"Counts words in bounded local text"},
                {"text":"Managed database connections close after every operation"},
            )
            outcome = bridge.run_once()
            report = bridge.report(task_id)
            self.assertEqual(outcome["status"], "done")
            self.assertEqual(report["status"], "done")
            self.assertTrue(report["evidence_sha256"])
            self.assertEqual(report["result"]["output"]["words"], 7)

    def test_queue_operations_do_not_emit_sqlite_resource_warnings(self):
        with tempfile.TemporaryDirectory() as temp:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", ResourceWarning)
                queue = ManagedTaskQueueV1(Path(temp) / "tasks.db")
                queue.enqueue("sample", {})
                queue.list_tasks()
                queue.audit_events()
                gc.collect()
            self.assertFalse(
                [w for w in caught if issubclass(w.category, ResourceWarning)],
                "managed queue leaked a SQLite connection",
            )


if __name__ == "__main__":
    unittest.main()
