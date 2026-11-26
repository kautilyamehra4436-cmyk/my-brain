"""Shared SQLite resource lifecycle policy for new Advait components.

Use managed_connection for every new SQLite integration. The connection is
always closed, including commit/rollback failures. Parent directories are
created before connecting. This does not silently migrate legacy callers.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


def _prepare_path(db_path: str | Path) -> str:
    raw = str(db_path)
    if raw == ":memory:" or raw.startswith("file:"):
        return raw
    path = Path(raw).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)


@contextmanager
def managed_connection(
    db_path: str | Path, *, timeout: float = 10.0
) -> Iterator[sqlite3.Connection]:
    """Yield one SQLite connection and deterministically commit/rollback/close."""
    if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or timeout <= 0:
        raise ValueError("timeout_must_be_positive_number")
    target = _prepare_path(db_path)
    con = sqlite3.connect(target, timeout=float(timeout))
    try:
        con.execute(f"PRAGMA busy_timeout={int(float(timeout) * 1000)}")
        con.execute("PRAGMA foreign_keys=ON")
        if target != ":memory:" and not target.startswith("file::memory:"):
            con.execute("PRAGMA journal_mode=WAL")
        yield con
        con.commit()
    except BaseException:
        try:
            con.rollback()
        except sqlite3.Error:
            pass
        raise
    finally:
        con.close()
