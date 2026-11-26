"""Additive TaskQueue variant that deterministically closes SQLite connections."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from core.task_queue import TaskQueue


class ManagedTaskQueueV1(TaskQueue):
    """Drop-in TaskQueue subclass with explicit SQLite connection closure.

    The base TaskQueue uses sqlite3.Connection as a transaction context manager;
    that commits/rolls back but does not close the connection. This subclass
    preserves the base API while closing every connection in a finally block.
    """

    @contextmanager
    def _connect(self):
        con = sqlite3.connect(self.db_path, timeout=10)
        try:
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA foreign_keys=ON")
            yield con
            con.commit()
        except BaseException:
            con.rollback()
            raise
        finally:
            con.close()
