"""Provider call ledger using Advait's shared SQLite lifecycle policy."""
from contextlib import contextmanager

from core.managed_sqlite_v1 import managed_connection
from core.provider_router_v1 import ProviderCallLedger


class ManagedProviderCallLedgerV2(ProviderCallLedger):
    """Drop-in ledger API with deterministic close and parent directory creation."""
    @contextmanager
    def _connect(self):
        with managed_connection(self.db_path, timeout=10) as con:
            yield con
