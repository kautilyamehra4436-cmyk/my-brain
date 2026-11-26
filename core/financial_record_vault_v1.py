"""Separate permission-restricted financial artifact storage (not encrypted at rest)."""
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
    """Separate files from operational SQLite; POSIX permissions, no encryption."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self._ensure_directory(self.root)
        self._root_real = self.root.resolve(strict=True)
        self.input_dir = self.root / "inputs"
        self.output_dir = self.root / "outputs"
        self._ensure_directory(self.input_dir)
        self._ensure_directory(self.output_dir)
        self._input_real = self.input_dir.resolve(strict=True)
        self._output_real = self.output_dir.resolve(strict=True)

    @staticmethod
    def _ensure_directory(path: Path) -> None:
        if path.is_symlink():
            raise FinancialVaultError("vault_directory_symlink_blocked")
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        if path.is_symlink() or not path.is_dir():
            raise FinancialVaultError("vault_directory_invalid")
        os.chmod(path, 0o700)
        path.resolve(strict=True)

    def _assert_directory(self, path: Path, expected_real: Path) -> None:
        if path.is_symlink() or not path.is_dir():
            raise FinancialVaultError("vault_directory_invalid_or_symlinked")
        if path.resolve(strict=True) != expected_real:
            raise FinancialVaultError("vault_directory_retargeted")

    def _assert_child(self, parent: Path, path: Path, expected_parent: Path) -> None:
        self._assert_directory(parent, expected_parent)
        if path.is_symlink():
            raise FinancialVaultError("vault_child_symlink_blocked")
        if path.parent.resolve(strict=True) != expected_parent:
            raise FinancialVaultError("vault_parent_path_retargeted")

    @staticmethod
    def _nofollow_flag() -> int:
        flag = getattr(os, "O_NOFOLLOW", None)
        if flag is None:
            raise FinancialVaultError("secure_no_follow_open_unavailable")
        return flag

    def _write_exclusive(
        self, path: Path, content: bytes, parent: Path, expected_parent: Path
    ) -> None:
        self._assert_child(parent, path, expected_parent)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | self._nofollow_flag()
        fd = os.open(str(path), flags, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(path, 0o600)

    def _read_regular(
        self, path: Path, max_bytes: int, parent: Path, expected_parent: Path
    ) -> bytes:
        self._assert_child(parent, path, expected_parent)
        flags = os.O_RDONLY | self._nofollow_flag()
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

    def stage_csv(self, content: bytes, *, allow_unencrypted_storage: bool = False) -> dict[str, Any]:
        """Stage CSV only after explicit acknowledgement that storage is not encrypted."""
        if allow_unencrypted_storage is not True:
            raise PermissionError("explicit_unencrypted_storage_acknowledgement_required")
        if not isinstance(content, bytes):
            raise TypeError("CSV source must be bytes")
        if not content or len(content) > MAX_SOURCE_BYTES:
            raise ValueError("CSV source is empty or exceeds 1 MiB")
        if b"\x00" in content:
            raise ValueError("CSV source contains a NUL byte")
        content.decode("utf-8-sig")
        artifact_id = uuid.uuid4().hex
        self._write_exclusive(
            self.input_dir / f"{artifact_id}.csv", content,
            self.input_dir, self._input_real,
        )
        return {
            "artifact_id": artifact_id,
            "sha256": hashlib.sha256(content).hexdigest(),
            "bytes": len(content),
        }

    def read_input(self, artifact_id: str) -> bytes:
        if not isinstance(artifact_id, str) or not _INPUT_ID.fullmatch(artifact_id):
            raise ValueError("invalid_financial_input_artifact_id")
        return self._read_regular(
            self.input_dir / f"{artifact_id}.csv", MAX_SOURCE_BYTES,
            self.input_dir, self._input_real,
        )

    def store_outputs(self, input_sha256: str, report: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(input_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", input_sha256):
            raise ValueError("invalid_input_digest")
        encoded = {
            "normalized_csv": report["normalized_csv"].encode("utf-8"),
            "exceptions_csv": report["exceptions_csv"].encode("utf-8"),
            "summary": report["summary"].encode("utf-8"),
        }
        if sum(len(value) for value in encoded.values()) > MAX_OUTPUT_BYTES:
            raise ValueError("financial output exceeds 4 MiB")
        artifact_set_id = hashlib.sha256(
            f"b2b-reconcile-v1:{input_sha256}".encode("ascii")
        ).hexdigest()
        directory = self.output_dir / artifact_set_id
        self._assert_child(self.output_dir, directory, self._output_real)
        if directory.exists():
            if not directory.is_dir():
                raise FinancialVaultError("vault_output_path_not_directory")
            existing = self.read_outputs(artifact_set_id)
            if existing != encoded:
                raise FinancialVaultError("existing_output_artifact_conflict")
        else:
            os.mkdir(directory, 0o700)
            directory_real = directory.resolve(strict=True)
            for key, filename in _OUTPUT_NAMES.items():
                self._write_exclusive(
                    directory / filename, encoded[key], directory, directory_real
                )
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
        self._assert_child(self.output_dir, directory, self._output_real)
        if not directory.is_dir():
            raise FinancialVaultError("vault_output_directory_missing_or_invalid")
        directory_real = directory.resolve(strict=True)
        expected_directory = self._output_real / artifact_set_id
        if directory_real != expected_directory:
            raise FinancialVaultError("vault_output_directory_retargeted")
        return {
            key: self._read_regular(
                directory / filename, MAX_OUTPUT_BYTES, directory, directory_real
            )
            for key, filename in _OUTPUT_NAMES.items()
        }
