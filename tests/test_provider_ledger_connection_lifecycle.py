"""Regression test: ProviderCallLedger must close each SQLite connection."""
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.provider_router_v1 import ProviderCallLedger


class ProviderCallLedgerConnectionLifecycleTests(unittest.TestCase):
    def test_ledger_operations_close_every_sqlite_connection(self):
        original_connect = sqlite3.connect
        opened = []

        def tracked_connect(*args, **kwargs):
            connection = original_connect(*args, **kwargs)
            opened.append(connection)
            return connection

        with tempfile.TemporaryDirectory() as tmp:
            with patch("core.managed_sqlite_v1.sqlite3.connect", side_effect=tracked_connect):
                ledger = ProviderCallLedger(Path(tmp) / "nested" / "provider.db")
                ledger.append(
                    request_id="request-1",
                    provider="openrouter",
                    model="fixture:free",
                    request_sha256="a" * 64,
                    response_sha256="b" * 64,
                    status="success",
                    http_status=200,
                    latency_ms=1,
                    usage={},
                    cost_usd=0,
                )
                ledger.events()

        self.assertGreaterEqual(len(opened), 3)
        for connection in opened:
            with self.subTest(connection=connection):
                with self.assertRaises(sqlite3.ProgrammingError):
                    connection.execute("SELECT 1")


if __name__ == "__main__":
    unittest.main()
