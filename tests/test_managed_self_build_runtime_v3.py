import tempfile
import unittest
from pathlib import Path
from core.managed_self_build_runtime_v3 import ManagedSelfBuildRuntimeV3

class ManagedSelfBuildRuntimeV3Tests(unittest.TestCase):
    def test_runtime_uses_leased_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime=ManagedSelfBuildRuntimeV3(Path(tmp)/"new"/"worker")
            self.assertEqual(type(runtime.queue).__name__,"ManagedTaskQueueV3")
            report=runtime.run_until_idle(1)
            self.assertEqual(report["processed"],0)
            self.assertEqual(report["queue_version"],"ManagedTaskQueueV3")
            self.assertEqual(report["lease_status"]["active_leases"],[])
    def test_runtime_bounds_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                ManagedSelfBuildRuntimeV3(tmp,max_attempts=0)

if __name__=="__main__":
    unittest.main()
