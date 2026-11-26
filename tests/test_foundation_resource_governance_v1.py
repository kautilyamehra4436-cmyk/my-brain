import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.managed_sqlite_v1 import managed_connection
from core.managed_task_queue_v2 import ManagedTaskQueueV2
from core.managed_provider_call_ledger_v2 import ManagedProviderCallLedgerV2
from core.engineering_lessons_v1 import lessons_for_agent


class FoundationResourceGovernanceTests(unittest.TestCase):
    def test_creates_nested_parent_and_closes_connection(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "deep" / "nested" / "db.sqlite"
            captured = []
            real_connect = sqlite3.connect

            def tracking_connect(*args, **kwargs):
                con = real_connect(*args, **kwargs)
                captured.append(con)
                return con

            with patch("core.managed_sqlite_v1.sqlite3.connect", side_effect=tracking_connect):
                with managed_connection(target) as con:
                    con.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY)")
            self.assertTrue(target.exists())
            self.assertEqual(len(captured), 1)
            with self.assertRaises(sqlite3.ProgrammingError):
                captured[0].execute("SELECT 1")

    def test_rolls_back_and_closes_on_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "rollback.sqlite"
            captured = []
            real_connect = sqlite3.connect

            def tracking_connect(*args, **kwargs):
                con = real_connect(*args, **kwargs)
                captured.append(con)
                return con

            with real_connect(target) as setup:
                setup.execute("CREATE TABLE sample (id INTEGER)")
            with patch("core.managed_sqlite_v1.sqlite3.connect", side_effect=tracking_connect):
                with self.assertRaisesRegex(RuntimeError, "forced"):
                    with managed_connection(target) as con:
                        con.execute("INSERT INTO sample(id) VALUES(1)")
                        raise RuntimeError("forced")
            with self.assertRaises(sqlite3.ProgrammingError):
                captured[0].execute("SELECT 1")
            with real_connect(target) as verify:
                self.assertEqual(verify.execute("SELECT id FROM sample").fetchall(), [])

    def test_managed_task_queue_creates_missing_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "new" / "dir" / "tasks.sqlite"
            queue = ManagedTaskQueueV2(db)
            task_id = queue.enqueue("foundation test", {"x": 1})
            self.assertEqual(queue.list_tasks()[0]["id"], task_id)

    def test_managed_provider_ledger_creates_missing_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "new" / "dir" / "provider.sqlite"
            ledger = ManagedProviderCallLedgerV2(db)
            ledger.append(
                request_id="foundation-1", provider="openrouter", model="test:free",
                request_sha256="a" * 64, response_sha256="b" * 64,
                status="success", latency_ms=1, usage={}
            )
            self.assertEqual(len(ledger.events()), 1)

    def test_invalid_timeout_fails_before_open(self):
        with self.assertRaises(ValueError):
            with managed_connection(":memory:", timeout=0):
                pass

    def test_agent_lessons_include_verified_root_causes(self):
        lessons = lessons_for_agent()
        self.assertGreaterEqual(len(lessons), 5)
        self.assertIn("FOUNDATION-001", {item["id"] for item in lessons})
        self.assertIn("FOUNDATION-002", {item["id"] for item in lessons})


if __name__ == "__main__":
    unittest.main()
