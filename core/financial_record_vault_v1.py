"""Separate, permission-restricted storage for financial source and output artifacts."""
from __future__ import annotations

import hashlib
import os
import re
import stat
import uuid
from pathlib import Path
from typing import Any

MAX_SOURCE_BYTES = 1_048_576
MAX_OUTPUT_BYTES = 4_194_304
_INPUT_ID = re.compile(r"^[0-9a-f]{32}$")
_OUTPUT_ID = re.compile(r"^[0-9a-f]{64}$")
_OUTPUT_NAMES = {
    "normalized_csv": "normalized.csv",
    "exceptions_csv": "exceptions.csv",
    "summary": "summary.txt",
}


class FinancialVaultError(RuntimeError):
    pass


class FinancialRecordVaultV1:
    """Financial records are kept outside operational queue/tool SQLite databases."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self._ensure_directory(self.root)
        self.input_dir = self.root / "inputs"
        self.output_dir = self.root / "outputs"
        self._ensure_directory(self.input_dir)
        self._ensure_directory(self.output_dir)

    @staticmethod
    def _ensure_directory(path: Path) -> None:
        if path.is_symlink():
            raise FinancialVaultError("vault_directory_symlink_blocked")
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        if path.is_symlink() or not path.is_dir():
            raise FinancialVaultError("vault_directory_invalid")
        os.chmod(path, 0o700)
        path.resolve(strict=True)

    @staticmethod
    def _nofollow_flag() -> int:
        flag = getattr(os, "O_NOFOLLOW", None)
        if flag is None:
            raise FinancialVaultError("secure_no_follow_open_unavailable")
        return flag

    @classmethod
    def _write_exclusive(cls, path: Path, content: bytes) -> None:
        if path.is_symlink():
            raise FinancialVaultError("vault_file_symlink_blocked")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | cls._nofollow_flag()
        fd = os.open(str(path), flags, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(path, 0o600)

    @classmethod
    def _read_regular(cls, path: Path, max_bytes: int) -> bytes:
        if path.is_symlink():
            raise FinancialVaultError("vault_file_symlink_blocked")
        flags = os.O_RDONLY | cls._nofollow_flag()
        fd = os.open(str(path), flags)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise FinancialVaultError("vault_artifact_not_regular_file")
            if info.st_size > max_bytes:
                raise FinancialVaultError("vault_artifact_exceeds_size_limit")
            content = stream.read(max_bytes + 1)
        if len(content) > max_bytes:
            raise FinancialVaultError("vault_artifact_exceeds_size_limit")
        return content

    def stage_csv(self, content: bytes) -> dict[str, Any]:
        """Stage an explicitly supplied CSV; returns only an opaque ID and digest."""
        if not isinstance(content, bytes):
            raise TypeError("CSV source must be bytes")
        if not content or len(content) > MAX_SOURCE_BYTES:
            raise ValueError("CSV source is empty or exceeds 1 MiB")
        if b"\x00" in content:
            raise ValueError("CSV source contains a NUL byte")
        content.decode("utf-8-sig")
        artifact_id = uuid.uuid4().hex
        self._write_exclusive(self.input_dir / f"{artifact_id}.csv", content)
        return {
            "artifact_id": artifact_id,
            "sha256": hashlib.sha256(content).hexdigest(),
            "bytes": len(content),
        }

    def read_input(self, artifact_id: str) -> bytes:
        if not isinstance(artifact_id, str) or not _INPUT_ID.fullmatch(artifact_id):
            raise ValueError("invalid_financial_input_artifact_id")
        return self._read_regular(self.input_dir / f"{artifact_id}.csv", MAX_SOURCE_BYTES)

    def store_outputs(self, input_sha256: str, report: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(input_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", input_sha256):
            raise ValueError("invalid_input_digest")
        encoded = {
            "normalized_csv": report["normalized_csv"].encode("utf-8"),
            "exceptions_csv": report["exceptions_csv"].encode("utf-8"),
            "summary": report["summary"].encode("utf-8"),
        }
        total = sum(len(value) for value in encoded.values())
        if total > MAX_OUTPUT_BYTES:
            raise ValueError("financial output exceeds 4 MiB")
        artifact_set_id = hashlib.sha256(
            f"b2b-reconcile-v1:{input_sha256}".encode("ascii")
        ).hexdigest()
        directory = self.output_dir / artifact_set_id
        if directory.is_symlink():
            raise FinancialVaultError("vault_output_directory_symlink_blocked")
        if directory.exists():
            if not directory.is_dir():
                raise FinancialVaultError("vault_output_path_not_directory")
            existing = self.read_outputs(artifact_set_id)
            if existing != encoded:
                raise FinancialVaultError("existing_output_artifact_conflict")
        else:
            os.mkdir(directory, 0o700)
            for key, filename in _OUTPUT_NAMES.items():
                self._write_exclusive(directory / filename, encoded[key])
        return {
            "artifact_set_id": artifact_set_id,
            "sha256": {
                key: hashlib.sha256(value).hexdigest()
                for key, value in encoded.items()
            },
        }

    def read_outputs(self, artifact_set_id: str) -> dict[str, bytes]:
        if not isinstance(artifact_set_id, str) or not _OUTPUT_ID.fullmatch(artifact_set_id):
            raise ValueError("invalid_financial_output_artifact_id")
        directory = self.output_dir / artifact_set_id
        if directory.is_symlink() or not directory.is_dir():
            raise FinancialVaultError("vault_output_directory_missing_or_invalid")
        return {
            key: self._read_regular(directory / filename, MAX_OUTPUT_BYTES)
            for key, filename in _OUTPUT_NAMES.items()
        }
