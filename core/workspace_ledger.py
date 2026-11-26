"""Append-only, role-scoped SQLite knowledge ledger for Advait workspaces.

Security boundary:
- The host MUST pass an actor_id obtained from authenticated server/session state.
- resolve_role MUST be supplied by trusted host code; this module does not authenticate users.
- Agents can read their own records and explicitly shared records.
- Owners can read all records.
- No update/delete API is provided; corrections are new records.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from typing import Callable

KINDS = {"command", "task", "report", "learning", "decision", "resource", "evidence"}
ROLES = {"owner", "agent"}
VISIBILITIES = {"shared", "private"}


def _canonical(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    )


def _required_text(value, field, limit):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    value = value.strip()
    if len(value) > limit:
        raise ValueError(f"{field} exceeds {limit} characters")
    return value


class WorkspaceLedger:
    """Trusted-host mediated workspace ledger; standard-library only."""

    def __init__(self, db_path="brain_workspace.db",
                 resolve_role: Callable[[str], str] | None = None):
        self.db_path = str(db_path)
        self.resolve_role = resolve_role
        self._init()

    def _connect(self):
        con = sqlite3.connect(self.db_path, timeout=10)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA foreign_keys=ON")
        return con

    def _init(self):
        with self._connect() as con:
            con.execute(
                """CREATE TABLE IF NOT EXISTS workspace_records (
                    record_id TEXT PRIMARY KEY,
                    owner_role TEXT NOT NULL CHECK(owner_role IN ('owner','agent')),
                    visibility TEXT NOT NULL CHECK(visibility IN ('shared','private')),
                    kind TEXT NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    source_ref TEXT,
                    evidence_ref TEXT,
                    task_id TEXT,
                    content_sha256 TEXT NOT NULL,
                    created_at REAL NOT NULL
                )"""
            )
            con.execute(
                """CREATE TABLE IF NOT EXISTS workspace_audit (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor_id TEXT NOT NULL,
                    actor_role TEXT NOT NULL,
                    event TEXT NOT NULL,
                    record_id TEXT,
                    details_json TEXT NOT NULL,
                    at REAL NOT NULL
                )"""
            )
            # Database-level guard: records and audit events are append-only.
            con.execute(
                """CREATE TRIGGER IF NOT EXISTS workspace_records_no_update
                   BEFORE UPDATE ON workspace_records
                   BEGIN SELECT RAISE(ABORT, 'workspace ledger is append-only'); END"""
            )
            con.execute(
                """CREATE TRIGGER IF NOT EXISTS workspace_records_no_delete
                   BEFORE DELETE ON workspace_records
                   BEGIN SELECT RAISE(ABORT, 'workspace ledger is append-only'); END"""
            )
            con.execute(
                """CREATE TRIGGER IF NOT EXISTS workspace_audit_no_update
                   BEFORE UPDATE ON workspace_audit
                   BEGIN SELECT RAISE(ABORT, 'workspace audit is append-only'); END"""
            )
            con.execute(
                """CREATE TRIGGER IF NOT EXISTS workspace_audit_no_delete
                   BEFORE DELETE ON workspace_audit
                   BEGIN SELECT RAISE(ABORT, 'workspace audit is append-only'); END"""
            )

    def _role(self, actor_id):
        actor_id = _required_text(actor_id, "actor_id", 200)
        if not callable(self.resolve_role):
            raise PermissionError("trusted identity resolver unavailable; fail closed")
        try:
            role = self.resolve_role(actor_id)
        except Exception as exc:
            raise PermissionError("identity resolution failed; fail closed") from exc
        if role not in ROLES:
            raise PermissionError("unknown or unauthorized principal; fail closed")
        return actor_id, role

    @staticmethod
    def _audit(con, actor_id, role, event, record_id=None, details=None):
        con.execute(
            """INSERT INTO workspace_audit
               (actor_id,actor_role,event,record_id,details_json,at)
               VALUES(?,?,?,?,?,?)""",
            (actor_id, role, event, record_id, _canonical(details or {}), time.time()),
        )

    def create_record(self, actor_id, *, kind, title, body, visibility="shared",
                      source_ref=None, evidence_ref=None, task_id=None):
        actor_id, role = self._role(actor_id)
        if kind not in KINDS:
            raise ValueError("unsupported record kind")
        if visibility not in VISIBILITIES:
            raise ValueError("visibility must be 'shared' or 'private'")
        title = _required_text(title, "title", 200)
        body = _required_text(body, "body", 100_000)
        optional = {}
        for key, value in (("source_ref", source_ref), ("evidence_ref", evidence_ref),
                           ("task_id", task_id)):
            if value is not None:
                optional[key] = _required_text(value, key, 1000)
            else:
                optional[key] = None

        record_id = str(uuid.uuid4())
        created_at = time.time()
        digest_input = _canonical({
            "owner_role": role, "visibility": visibility, "kind": kind,
            "title": title, "body": body, **optional,
        })
        digest = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute(
                """INSERT INTO workspace_records
                   (record_id,owner_role,visibility,kind,title,body,source_ref,
                    evidence_ref,task_id,content_sha256,created_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (record_id, role, visibility, kind, title, body,
                 optional["source_ref"], optional["evidence_ref"], optional["task_id"],
                 digest, created_at),
            )
            self._audit(con, actor_id, role, "record_created", record_id,
                        {"kind": kind, "visibility": visibility, "content_sha256": digest})
        return record_id

    def search(self, actor_id, query="", *, kind=None, limit=50, offset=0):
        actor_id, role = self._role(actor_id)
        if kind is not None and kind not in KINDS:
            raise ValueError("unsupported record kind")
        if not isinstance(query, str):
            raise ValueError("query must be text")
        query = query.strip()[:500]
        limit = max(1, min(int(limit), 200))
        offset = max(0, int(offset))
        clauses, args = [], []
        if role == "agent":
            clauses.append("(visibility='shared' OR owner_role='agent')")
        if kind is not None:
            clauses.append("kind=?")
            args.append(kind)
        if query:
            escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            clauses.append("(title LIKE ? ESCAPE '\\' OR body LIKE ? ESCAPE '\\' "
                           "OR COALESCE(source_ref,'') LIKE ? ESCAPE '\\' "
                           "OR COALESCE(evidence_ref,'') LIKE ? ESCAPE '\\' "
                           "OR COALESCE(task_id,'') LIKE ? ESCAPE '\\')")
            args.extend([f"%{escaped}%"] * 5)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        with self._connect() as con:
            rows = con.execute(
                "SELECT * FROM workspace_records" + where
                + " ORDER BY created_at DESC, record_id LIMIT ? OFFSET ?",
                (*args, limit, offset),
            ).fetchall()
            self._audit(con, actor_id, role, "records_searched", None,
                        {"query_length": len(query), "kind": kind, "result_count": len(rows)})
        return [dict(row) for row in rows]

    def get_record(self, actor_id, record_id):
        actor_id, role = self._role(actor_id)
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM workspace_records WHERE record_id=?", (record_id,)
            ).fetchone()
            if row is None:
                return None
            if role == "agent" and row["owner_role"] == "owner" and row["visibility"] != "shared":
                self._audit(con, actor_id, role, "record_access_denied", record_id, {})
                return None
            self._audit(con, actor_id, role, "record_read", record_id, {})
            return dict(row)

    def audit_events(self, actor_id, *, limit=100):
        actor_id, role = self._role(actor_id)
        if role != "owner":
            raise PermissionError("audit ledger is owner-only")
        limit = max(1, min(int(limit), 500))
        with self._connect() as con:
            rows = con.execute(
                "SELECT * FROM workspace_audit ORDER BY event_id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]
