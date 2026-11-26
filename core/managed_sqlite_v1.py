"""Shared SQLite resource lifecycle and local-path policy for Advait.

Use managed_connection for local SQLite state. Connections are always closed,
transactions commit/rollback deterministically, database files are mode 0600,
and direct database/parent symlinks plus arbitrary SQLite URI paths are rejected.
"""
from __future__ import annotations

import math
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


def _prepare_path(db_path: str | Path) -> str:
    raw = os.fspath(db_path)
    if not isinstance(raw, str) or not raw or "\x00" in raw:
        raise ValueError("invalid_sqlite_path")
    if raw == ":memory:":
        return raw
    if raw.startswith("file:"):
        raise ValueError("sqlite_uri_paths_not_supported")
    path = Path(raw).expanduser()
    if path.name in {"", ".", ".."}:
        raise ValueError("invalid_sqlite_path")
    if path.is_symlink():
        raise PermissionError("sqlite_database_symlink_blocked")
    parent = path.parent
    if parent.is_symlink():
        raise PermissionError("sqlite_parent_symlink_blocked")
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if parent.is_symlink() or not parent.is_dir():
        raise PermissionError("sqlite_parent_directory_not_safe")
    if path.is_symlink():
        raise PermissionError("sqlite_database_symlink_blocked")
    if path.exists() and not path.is_file():
        raise PermissionError("sqlite_database_not_regular_file")
    return str(path)


@contextmanager
def managed_connection(
    db_path: str | Path, *, timeout: float = 10.0
) -> Iterator[sqlite3.Connection]:
    """Yield one connection and deterministically commit/rollback/close."""
    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not math.isfinite(float(timeout))
        or timeout <= 0
        or timeout > 60
    ):
        raise ValueError("timeout_must_be_between_0_and_60_seconds")
    target = _prepare_path(db_path)
    con = sqlite3.connect(target, timeout=float(timeout))
    try:
        if target != ":memory:":
            path = Path(target)
            if path.is_symlink() or not path.is_file():
                raise PermissionError("sqlite_database_path_changed_during_open")
            try:
                os.chmod(target, 0o600, follow_symlinks=False)
            except (NotImplementedError, TypeError):
                if path.is_symlink():
                    raise PermissionError("sqlite_database_symlink_blocked")
                os.chmod(target, 0o600)
        con.execute(f"PRAGMA busy_timeout={max(1, int(float(timeout) * 1000))}")
        con.execute("PRAGMA foreign_keys=ON")
        if target != ":memory:":
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
