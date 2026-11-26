"""Regression test: legacy TaskQueue must close every SQLite connection."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.task_queue import TaskQueue


class LegacyTaskQueueConnectionLifecycleTests(unittest.TestCase):
    def test_queue_operations_close_every_sqlite_connection(self):
        original_connect = sqlite3.connect
        opened = []

        def tracked_connect(*args, **kwargs):
            connection = original_connect(*args, **kwargs)
            opened.append(connection)
            return connection

        with tempfile.TemporaryDirectory() as tmp:
            with patch("core.managed_sqlite_v1.sqlite3.connect", side_effect=tracked_connect):
                queue = TaskQueue(Path(tmp) / "nested" / "tasks.db")
                queue.enqueue("lifecycle check", {"kind": "test"})
                queue.list_tasks()
                queue.audit_events()

        self.assertGreaterEqual(len(opened), 4)
        for connection in opened:
            with self.subTest(connection=connection):
                with self.assertRaises(sqlite3.ProgrammingError):
                    connection.execute("SELECT 1")


if __name__ == "__main__":
    unittest.main()
