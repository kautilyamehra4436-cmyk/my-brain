"""Compatibility TaskQueue variant using the shared hardened SQLite lifecycle."""
from __future__ import annotations

from core.managed_sqlite_v1 import managed_connection
from core.task_queue import TaskQueue


class ManagedTaskQueueV1(TaskQueue):
    """Drop-in compatibility class routed through the shared SQLite manager."""

    def _connect(self):
        return managed_connection(self.db_path, timeout=10)
