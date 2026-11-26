"""SQLite task queue with evidence-gated completion and audit metadata."""
import hashlib
import json
import re
import sqlite3
import time
import uuid

from core.managed_sqlite_v1 import managed_connection


MAX_TASK_PAYLOAD_BYTES = 65_536
MAX_TASK_RESULT_BYTES = 65_536
MAX_TASK_TITLE_CHARS = 200
SENSITIVE_KEYS = {
    "approval_token", "owner_token", "api_key", "secret", "password", "token",
    "authorization", "credential", "credentials", "access_token", "access_key",
    "refresh_token", "private_key", "webhook_secret", "client_secret",
    "secret_access_key", "secret_key", "signing_key",
}
SENSITIVE_SUFFIXES = (
    "_token", "_secret", "_password", "_credential", "_private_key",
    "_api_key", "_access_key", "_signing_key",
)
SENSITIVE_TEXT = re.compile(
    r"(?:\bBearer\s+[A-Za-z0-9._~+/=-]{12,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"(?:api[_-]?key|password|secret|authorization)\s*[:=]\s*\S+|"
    r"\b(?:sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b)",
    re.IGNORECASE,
)


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def contains_sensitive_material(value, *, depth=0):
    """Conservative recursive key-name check; task queues must not store credentials."""
    if depth > 12:
        return True
    if isinstance(value, dict):
        if len(value) > 500:
            return True
        for key, item in value.items():
            if not isinstance(key, str):
                return True
            normalized = key.strip().casefold().replace("-", "_").replace(" ", "_")
            if normalized in SENSITIVE_KEYS or any(normalized.endswith(suffix) for suffix in SENSITIVE_SUFFIXES):
                return True
            if contains_sensitive_material(item, depth=depth + 1):
                return True
    elif isinstance(value, list):
        if len(value) > 1000:
            return True
        return any(contains_sensitive_material(item, depth=depth + 1) for item in value)
    return False


def _safe_error_code(error):
    value = str(error).strip()
    return value if re.fullmatch(r"[A-Za-z0-9_.:-]{1,120}", value) else "task_failed"


class TaskQueue:
    requires_lease_owner = False

    def __init__(self, db_path="brain_tasks.db"):
        self.db_path = str(db_path)
        self._init()

    def _connect(self):
        """Return a managed connection context that always closes its handle."""
        return managed_connection(self.db_path, timeout=10)

    def _init(self):
        with self._connect() as con:
            con.execute(
                "CREATE TABLE IF NOT EXISTS tasks ("
                "id TEXT PRIMARY KEY, title TEXT NOT NULL, payload TEXT NOT NULL, "
                "status TEXT NOT NULL, created_at REAL NOT NULL, updated_at REAL NOT NULL, "
                "result TEXT, error TEXT, evidence_sha256 TEXT)"
            )
            columns = {row[1] for row in con.execute("PRAGMA table_info(tasks)")}
            if "evidence_sha256" not in columns:
                con.execute("ALTER TABLE tasks ADD COLUMN evidence_sha256 TEXT")
            con.execute(
                "CREATE TABLE IF NOT EXISTS audit ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT NOT NULL, "
                "task_id TEXT, details TEXT NOT NULL, at REAL NOT NULL)"
            )

    def _audit(self, con, event, task_id, details):
        con.execute(
            "INSERT INTO audit(event, task_id, details, at) VALUES(?,?,?,?)",
            (event, task_id, _canonical(details), time.time()),
        )

    def enqueue(self, title, payload=None):
        title_text = str(title).strip()
        if not title_text:
            raise ValueError("Task title cannot be blank")
        if len(title_text) > MAX_TASK_TITLE_CHARS:
            raise ValueError("task_title_too_long")
        if SENSITIVE_TEXT.search(title_text):
            raise ValueError("sensitive_material_must_not_be_persisted")
        task_payload = payload if payload is not None else {}
        if not isinstance(task_payload, dict):
            raise ValueError("task_payload_must_be_object")
        if contains_sensitive_material(task_payload):
            raise ValueError("sensitive_material_must_not_be_persisted")
        try:
            data = _canonical(task_payload)
        except (TypeError, ValueError):
            raise ValueError("task_payload_must_be_json") from None
        if len(data.encode("utf-8")) > MAX_TASK_PAYLOAD_BYTES:
            raise ValueError("task_payload_too_large")
        task_id, now = str(uuid.uuid4()), time.time()
        with self._connect() as con:
            con.execute(
                "INSERT INTO tasks "
                "(id,title,payload,status,created_at,updated_at,result,error,evidence_sha256) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (task_id, title_text, data, "pending", now, now, None, None, None),
            )
            self._audit(con, "enqueue", task_id, {"title": title_text})
        return task_id

    def list_tasks(self, status=None):
        with self._connect() as con:
            query = (
                "SELECT id,title,payload,status,created_at,updated_at,result,error,evidence_sha256 "
                "FROM tasks"
            )
            args = ()
            if status:
                query += " WHERE status=?"
                args = (status,)
            query += " ORDER BY created_at"
            rows = con.execute(query, args).fetchall()
        keys = (
            "id", "title", "payload", "status", "created_at", "updated_at",
            "result", "error", "evidence_sha256",
        )
        return [dict(zip(keys, row)) for row in rows]

    def claim_next(self, eligible=None):
        """Atomically claim the oldest pending task accepted by an optional predicate.

        The predicate receives the decoded payload. Non-matching tasks remain pending;
        this lets an execution worker leave ATC plan-only records untouched.
        """
        now = time.time()
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            rows = con.execute(
                "SELECT id,title,payload FROM tasks WHERE status='pending' "
                "ORDER BY created_at"
            ).fetchall()
            row = None
            payload = None
            for candidate in rows:
                try:
                    candidate_payload = json.loads(candidate[2])
                except (TypeError, ValueError):
                    if eligible is not None:
                        continue
                    candidate_payload = {}
                if eligible is not None:
                    try:
                        if not eligible(candidate_payload):
                            continue
                    except Exception:
                        continue
                row = candidate
                payload = candidate_payload
                break
            if row is None:
                return None
            cur = con.execute(
                "UPDATE tasks SET status='running',updated_at=? "
                "WHERE id=? AND status='pending'",
                (now, row[0]),
            )
            if cur.rowcount != 1:
                return None
            self._audit(con, "claim", row[0], {})
            return {
                "id": row[0], "title": row[1],
                "payload": payload, "status": "running",
            }

    def complete(self, task_id, result=None, *, evidence=None, verifier=None, worker_id=None):
        """Mark a task done only after an injected independent verifier accepts evidence.

        The verifier receives (task_id, result, evidence). Raw evidence is not
        persisted; only its SHA-256 digest is stored for audit correlation.
        """
        if self.requires_lease_owner and worker_id is None:
            raise PermissionError("lease_owner_required_for_completion")
        if worker_id is not None and (
            not isinstance(worker_id, str) or not worker_id.strip() or len(worker_id) > 128
        ):
            raise PermissionError("invalid_lease_owner")
        if not callable(verifier):
            raise PermissionError("independent evidence verifier unavailable; fail-closed")
        if evidence is None:
            raise ValueError("verification evidence is required")
        safe_result = result if result is not None else {}
        if not isinstance(safe_result, dict) or not isinstance(evidence, dict):
            raise ValueError("result_and_evidence_must_be_objects")
        if contains_sensitive_material(safe_result) or contains_sensitive_material(evidence):
            raise ValueError("sensitive_material_must_not_be_persisted")
        result_json = _canonical(safe_result)
        evidence_json = _canonical(evidence)
        if len(result_json.encode("utf-8")) > MAX_TASK_RESULT_BYTES:
            raise ValueError("task_result_too_large")
        if len(evidence_json.encode("utf-8")) > MAX_TASK_RESULT_BYTES:
            raise ValueError("task_evidence_too_large")
        try:
            verified = bool(verifier(task_id, json.loads(result_json), json.loads(evidence_json)))
        except Exception:
            verified = False
        if not verified:
            raise PermissionError("independent evidence verification failed; task remains running")
        evidence_digest = hashlib.sha256(evidence_json.encode("utf-8")).hexdigest()
        result_digest = hashlib.sha256(result_json.encode("utf-8")).hexdigest()
        now = time.time()
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            if worker_id is None:
                cur = con.execute(
                    "UPDATE tasks SET status='done',updated_at=?,result=?,error=NULL,evidence_sha256=? "
                    "WHERE id=? AND status='running'",
                    (now, result_json, evidence_digest, task_id),
                )
            else:
                cur = con.execute(
                    "UPDATE tasks SET status='done',updated_at=?,result=?,error=NULL,evidence_sha256=? "
                    "WHERE id=? AND status='running' AND lease_owner=? AND lease_expires_at>?",
                    (now, result_json, evidence_digest, task_id, worker_id, now),
                )
            if cur.rowcount != 1:
                if worker_id is not None:
                    raise PermissionError("task_lease_lost_or_expired")
                raise ValueError("Task not found or not running")
            self._audit(
                con, "complete_verified", task_id,
                {"result_sha256": result_digest, "evidence_sha256": evidence_digest,
                 "verification": "accepted"},
            )

    def fail(self, task_id, error, *, worker_id=None):
        if self.requires_lease_owner and worker_id is None:
            raise PermissionError("lease_owner_required_for_failure")
        if worker_id is not None and (
            not isinstance(worker_id, str) or not worker_id.strip() or len(worker_id) > 128
        ):
            raise PermissionError("invalid_lease_owner")
        now = time.time()
        safe_error = _safe_error_code(error)
        scrub_payload = safe_error == "sensitive_task_payload_blocked"
        with self._connect() as con:
            if worker_id is None:
                if scrub_payload:
                    cur = con.execute(
                        "UPDATE tasks SET status='failed',updated_at=?,error=?,payload='{}' "
                        "WHERE id=? AND status='running'",
                        (now, safe_error, task_id),
                    )
                else:
                    cur = con.execute(
                        "UPDATE tasks SET status='failed',updated_at=?,error=? "
                        "WHERE id=? AND status='running'",
                        (now, safe_error, task_id),
                )
            else:
                if scrub_payload:
                    cur = con.execute(
                        "UPDATE tasks SET status='failed',updated_at=?,error=?,payload='{}' "
                        "WHERE id=? AND status='running' AND lease_owner=? AND lease_expires_at>?",
                        (now, safe_error, task_id, worker_id, now),
                    )
                else:
                    cur = con.execute(
                        "UPDATE tasks SET status='failed',updated_at=?,error=? "
                        "WHERE id=? AND status='running' AND lease_owner=? AND lease_expires_at>?",
                        (now, safe_error, task_id, worker_id, now),
                    )
            if cur.rowcount != 1:
                if worker_id is not None:
                    raise PermissionError("task_lease_lost_or_expired")
                raise ValueError("Task not found or not running")
            self._audit(con, "fail", task_id, {"error": safe_error})
        if scrub_payload:
            try:
                with self._connect() as con:
                    con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except sqlite3.Error:
                pass

    def audit_events(self):
        with self._connect() as con:
            rows = con.execute(
                "SELECT id,event,task_id,details,at FROM audit ORDER BY id"
            ).fetchall()
        return [
            dict(zip(("id", "event", "task_id", "details", "at"), row))
            for row in rows
        ]
