"""Regression test: legacy TaskQueue must close every SQLite connection."""
import gc
import tempfile
import unittest
import warnings
from pathlib import Path

from core.task_queue import TaskQueue


class LegacyTaskQueueConnectionLifecycleTests(unittest.TestCase):
    def test_queue_operations_do_not_emit_unclosed_connection_warnings(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue = TaskQueue(Path(tmp) / "nested" / "tasks.db")
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", ResourceWarning)
                queue.enqueue("lifecycle check", {"kind": "test"})
                queue.list_tasks()
                queue.audit_events()
                gc.collect()

            leaked = [
                warning for warning in caught
                if issubclass(warning.category, ResourceWarning)
                and "sqlite3.Connection" in str(warning.message)
            ]
            self.assertEqual(leaked, [], "TaskQueue leaked SQLite connections")


if __name__ == "__main__":
    unittest.main()
