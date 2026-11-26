import tempfile
import unittest
from pathlib import Path
from core.managed_atc_queue_adapter_v1 import ManagedATCQueueAdapterV1
from core.managed_self_build_runtime_v2 import ManagedSelfBuildRuntimeV2
from core.atc_planner import ATCPlanner

class FoundationRuntimeMigrationV2Tests(unittest.TestCase):
    def test_self_build_runtime_uses_managed_queue_v2(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime=ManagedSelfBuildRuntimeV2(Path(tmp)/"missing"/"nested")
            self.assertEqual(type(runtime.queue).__name__,"ManagedTaskQueueV2")
            report=runtime.run_until_idle(1)
            self.assertEqual(report["processed"],0)
            self.assertEqual(report["remaining_pending"],0)
    def test_atc_plan_queue_adapter_stores_only_plan_steps(self):
        with tempfile.TemporaryDirectory() as tmp:
            planner=ATCPlanner(Path(tmp)/"atc"/"ledger.db")
            record=planner.think("Review a local text file")
            adapter=ManagedATCQueueAdapterV1(Path(tmp)/"queue"/"tasks.db")
            ids=adapter.enqueue_plan(record)
            self.assertEqual(len(ids),5)
            tasks=adapter.queue.list_tasks()
            self.assertEqual(len(tasks),5)
            import json
            self.assertTrue(all(json.loads(item["payload"])["status"]=="plan_only" for item in tasks))
    def test_adapter_rejects_non_draft_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter=ManagedATCQueueAdapterV1(Path(tmp)/"queue.db")
            with self.assertRaises(ValueError):
                adapter.enqueue_plan({"version":"ATC-1.2.0","status":"EXECUTED","plan_steps":[]})

if __name__=="__main__":
    unittest.main()
