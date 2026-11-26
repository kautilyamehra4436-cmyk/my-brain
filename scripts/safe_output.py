"""Exclusive, private output helpers for local audit/report artifacts."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

MAX_REPORT_BYTES = 1_000_000


def write_new_json(path: str | Path, value: Any, *, max_bytes: int = MAX_REPORT_BYTES) -> Path:
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or not 1 <= max_bytes <= MAX_REPORT_BYTES:
        raise ValueError("invalid_report_size_limit")
    target = Path(path).expanduser()
    if target.is_symlink():
        raise PermissionError("report_symlink_blocked")
    parent = target.parent
    if parent.is_symlink():
        raise PermissionError("report_parent_symlink_blocked")
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if parent.is_symlink() or not parent.is_dir():
        raise PermissionError("report_parent_not_safe")
    try:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    except (TypeError, ValueError):
        raise ValueError("report_must_be_finite_json") from None
    data = encoded.encode("utf-8")
    if len(data) > max_bytes:
        raise ValueError("report_too_large")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(str(target), flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(encoded)
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        raise
    return target
