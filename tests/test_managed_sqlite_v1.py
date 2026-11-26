import os
import sqlite3
import stat
import tempfile
import unittest
from pathlib import Path

from core.managed_sqlite_v1 import managed_connection


class ManagedSQLitePathSafetyTests(unittest.TestCase):
    def test_connection_closes_and_commits_on_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.db"
            with managed_connection(path) as connection:
                connection.execute("CREATE TABLE values_v1 (value TEXT)")
                connection.execute("INSERT INTO values_v1 VALUES ('ok')")
            with self.assertRaises(sqlite3.ProgrammingError):
                connection.execute("SELECT 1")
            with managed_connection(path) as check:
                self.assertEqual(check.execute("SELECT value FROM values_v1").fetchone()[0], "ok")

    def test_exception_rolls_back_and_closes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.db"
            with managed_connection(path) as connection:
                connection.execute("CREATE TABLE values_v1 (value TEXT)")
            with self.assertRaisesRegex(RuntimeError, "fixture_abort"):
                with managed_connection(path) as connection:
                    connection.execute("INSERT INTO values_v1 VALUES ('not-committed')")
                    raise RuntimeError("fixture_abort")
            with self.assertRaises(sqlite3.ProgrammingError):
                connection.execute("SELECT 1")
            with managed_connection(path) as check:
                self.assertEqual(check.execute("SELECT COUNT(*) FROM values_v1").fetchone()[0], 0)

    def test_database_file_is_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "private.db"
            with managed_connection(path) as connection:
                connection.execute("CREATE TABLE t (v INTEGER)")
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_database_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            real = Path(tmp) / "real.db"
            with managed_connection(real):
                pass
            link = Path(tmp) / "linked.db"
            link.symlink_to(real)
            with self.assertRaises(PermissionError):
                with managed_connection(link):
                    pass

    def test_parent_directory_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target"
            target.mkdir()
            link = Path(tmp) / "linked"
            link.symlink_to(target, target_is_directory=True)
            with self.assertRaises(PermissionError):
                with managed_connection(link / "state.db"):
                    pass

    def test_arbitrary_sqlite_file_uri_is_rejected(self):
        with self.assertRaises(ValueError):
            with managed_connection("file:unsafe.db?mode=ro"):
                pass

    def test_in_memory_database_remains_supported(self):
        with managed_connection(":memory:") as connection:
            connection.execute("CREATE TABLE t (v INTEGER)")
            connection.execute("INSERT INTO t VALUES (7)")
            self.assertEqual(connection.execute("SELECT v FROM t").fetchone()[0], 7)


if __name__ == "__main__":
    unittest.main()
