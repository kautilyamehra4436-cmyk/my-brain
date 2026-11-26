"""Safe declarative self-build tool factory for Advait v32.0.

This v1 builds tools from a strict operation catalogue; it never evaluates generated
Python, imports user modules, runs shell commands, or performs network access.
"""
from __future__ import annotations

import csv
from contextlib import contextmanager
import hashlib
import io
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

MAX_INPUT_BYTES = 1_000_000
MAX_OUTPUT_BYTES = 1_000_000
OPERATIONS = {
    "text.word_count",
    "text.sha256",
    "json.canonicalize",
    "csv.profile",
}
_NAME = re.compile(r"^[a-z][a-z0-9_.-]{1,63}$")
_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class ToolSpecError(ValueError):
    """Tool specification violates the safe declarative contract."""


class ToolExecutionError(ValueError):
    """Tool input or execution violates resource/format limits."""


class SelfBuildToolFactory:
    """Build, persist and execute only declarative tools from a fixed allowlist."""

    def __init__(self, db_path: str | Path = "advait_self_build_tools_v1.db"):
        self.db_path = str(db_path)
        with self._connection() as con:
            con.execute(
                """CREATE TABLE IF NOT EXISTS tool_versions (
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    description TEXT NOT NULL,
                    spec_json TEXT NOT NULL,
                    spec_sha256 TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(name, version)
                )"""
            )
            con.execute(
                """CREATE TRIGGER IF NOT EXISTS tool_versions_no_update
                   BEFORE UPDATE ON tool_versions BEGIN
                   SELECT RAISE(ABORT, 'tool registry is append-only');
                   END"""
            )
            con.execute(
                """CREATE TRIGGER IF NOT EXISTS tool_versions_no_delete
                   BEFORE DELETE ON tool_versions BEGIN
                   SELECT RAISE(ABORT, 'tool registry is append-only');
                   END"""
            )

    def _connect(self):
        con = sqlite3.connect(self.db_path, timeout=10)
        con.execute("PRAGMA foreign_keys=ON")
        return con

    @contextmanager
    def _connection(self):
        """Commit on success, roll back on failure, and always close the handle."""
        con = self._connect()
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    @staticmethod
    def validate_spec(spec: dict[str, Any]) -> dict[str, str]:
        if not isinstance(spec, dict) or set(spec) != {
            "name", "version", "operation", "description"
        }:
            raise ToolSpecError("spec must contain exactly name, version, operation, description")
        name, version = spec["name"], spec["version"]
        operation, description = spec["operation"], spec["description"]
        if not isinstance(name, str) or not _NAME.fullmatch(name):
            raise ToolSpecError("invalid_tool_name")
        if not isinstance(version, str) or not _VERSION.fullmatch(version):
            raise ToolSpecError("version_must_be_semver")
        if operation not in OPERATIONS:
            raise ToolSpecError("operation_not_allowlisted")
        if not isinstance(description, str) or not description.strip() or len(description) > 240:
            raise ToolSpecError("invalid_description")
        return {
            "name": name, "version": version, "operation": operation,
            "description": description.strip(),
        }

    def build(self, spec: dict[str, Any]) -> dict[str, str]:
        clean = self.validate_spec(spec)
        encoded = canonical_json(clean)
        digest = sha256_text(encoded)
        try:
            with self._connection() as con:
                con.execute(
                    """INSERT INTO tool_versions
                       (name, version, operation, description, spec_json, spec_sha256)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (clean["name"], clean["version"], clean["operation"],
                     clean["description"], encoded, digest),
                )
        except sqlite3.IntegrityError as exc:
            raise ToolSpecError("tool_version_already_exists") from exc
        return {**clean, "spec_sha256": digest, "status": "built"}

    def get(self, name: str, version: str) -> dict[str, str] | None:
        with self._connection() as con:
            row = con.execute(
                """SELECT name, version, operation, description, spec_sha256
                   FROM tool_versions WHERE name=? AND version=?""",
                (name, version),
            ).fetchone()
        if row is None:
            return None
        return dict(zip(("name", "version", "operation", "description", "spec_sha256"), row))

    def list_tools(self) -> list[dict[str, str]]:
        with self._connection() as con:
            rows = con.execute(
                """SELECT name, version, operation, description, spec_sha256
                   FROM tool_versions ORDER BY name, version"""
            ).fetchall()
        keys = ("name", "version", "operation", "description", "spec_sha256")
        return [dict(zip(keys, row)) for row in rows]

    def execute(self, name: str, version: str, data: dict[str, Any]) -> dict[str, Any]:
        record = self.get(name, version)
        if record is None:
            raise ToolExecutionError("tool_not_registered")
        if not isinstance(data, dict):
            raise ToolExecutionError("input_must_be_object")
        operation = record["operation"]

        if operation in {"text.word_count", "text.sha256"}:
            if set(data) != {"text"} or not isinstance(data["text"], str):
                raise ToolExecutionError("input_requires_text_string")
            raw = data["text"].encode("utf-8")
            if len(raw) > MAX_INPUT_BYTES:
                raise ToolExecutionError("input_too_large")
            if operation == "text.word_count":
                text = data["text"]
                return {"characters": len(text), "words": len(text.split()),
                        "lines": len(text.splitlines())}
            return {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}

        if operation == "json.canonicalize":
            if set(data) != {"value"}:
                raise ToolExecutionError("input_requires_value")
            try:
                encoded = canonical_json(data["value"])
            except (TypeError, ValueError) as exc:
                raise ToolExecutionError("value_is_not_finite_json") from exc
            if len(encoded.encode("utf-8")) > MAX_OUTPUT_BYTES:
                raise ToolExecutionError("output_too_large")
            return {"canonical_json": encoded, "sha256": sha256_text(encoded)}

        if operation == "csv.profile":
            if set(data) != {"csv_text"} or not isinstance(data["csv_text"], str):
                raise ToolExecutionError("input_requires_csv_text")
            raw = data["csv_text"].encode("utf-8")
            if len(raw) > MAX_INPUT_BYTES:
                raise ToolExecutionError("input_too_large")
            try:
                reader = csv.reader(io.StringIO(data["csv_text"], newline=""), strict=True)
                rows = list(reader)
            except csv.Error as exc:
                raise ToolExecutionError("invalid_csv") from exc
            if not rows:
                return {"headers": [], "data_rows": 0, "column_counts": []}
            headers = rows[0]
            if any(len(row) != len(headers) for row in rows[1:]):
                raise ToolExecutionError("inconsistent_csv_column_count")
            return {"headers": headers, "data_rows": max(0, len(rows) - 1),
                    "column_counts": [len(row) for row in rows[1:]]}

        raise ToolExecutionError("operation_not_allowlisted")

    def worker_handlers(self):
        """Return a minimal host allowlist compatible with BoundedWorker."""
        def create_and_execute(data: dict[str, Any]) -> dict[str, Any]:
            if not isinstance(data, dict) or set(data) != {"spec", "input"}:
                raise ToolExecutionError("handler_requires_spec_and_input")
            built = self.build(data["spec"])
            output = self.execute(built["name"], built["version"], data["input"])
            result = {"tool": built["name"], "version": built["version"], "output": output}
            evidence = {
                "tool_name": built["name"],
                "tool_version": built["version"],
                "spec_sha256": built["spec_sha256"],
                "result_sha256": sha256_text(canonical_json(result)),
                "verification_type": "registry_and_result_integrity",
            }
            return {"result": result, "evidence": evidence}

        return {"selfbuild.create_execute": create_and_execute}

    def worker_evidence_verifier(self):
        """Verify registry identity and result digest; not a semantic correctness proof."""
        def verify(_task_id: str, result: dict[str, Any], evidence: dict[str, Any]) -> bool:
            if not isinstance(result, dict) or not isinstance(evidence, dict):
                return False
            record = self.get(evidence.get("tool_name"), evidence.get("tool_version"))
            if record is None:
                return False
            return (
                record["spec_sha256"] == evidence.get("spec_sha256")
                and result.get("tool") == record["name"]
                and result.get("version") == record["version"]
                and evidence.get("result_sha256") == sha256_text(canonical_json(result))
                and evidence.get("verification_type") == "registry_and_result_integrity"
            )
        return verify
