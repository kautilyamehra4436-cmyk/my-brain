"""TaskQueue v2 using Advait's shared SQLite lifecycle policy."""
from contextlib import contextmanager

from core.managed_sqlite_v1 import managed_connection
from core.task_queue import TaskQueue


class ManagedTaskQueueV2(TaskQueue):
    """Drop-in TaskQueue API with parent creation and guaranteed connection close."""
    @contextmanager
    def _connect(self):
        with managed_connection(self.db_path, timeout=10) as con:
            yield con
