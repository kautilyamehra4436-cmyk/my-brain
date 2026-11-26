"""SQLite task queue with evidence-gated completion and audit metadata."""
import hashlib
import json
import sqlite3
import time
import uuid


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


class TaskQueue:
    def __init__(self, db_path="brain_tasks.db"):
        self.db_path = str(db_path)
        self._init()

    def _connect(self):
        con = sqlite3.connect(self.db_path, timeout=10)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA foreign_keys=ON")
        return con

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
        if not str(title).strip():
            raise ValueError("Task title cannot be blank")
        task_id, now = str(uuid.uuid4()), time.time()
        data = _canonical(payload if payload is not None else {})
        with self._connect() as con:
            con.execute(
                "INSERT INTO tasks "
                "(id,title,payload,status,created_at,updated_at,result,error,evidence_sha256) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (task_id, title.strip(), data, "pending", now, now, None, None, None),
            )
            self._audit(con, "enqueue", task_id, {"title": title.strip()})
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

    def claim_next(self):
        now = time.time()
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(
                "SELECT id,title,payload FROM tasks WHERE status='pending' "
                "ORDER BY created_at LIMIT 1"
            ).fetchone()
            if not row:
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
                "payload": json.loads(row[2]), "status": "running",
            }

    def complete(self, task_id, result=None, *, evidence=None, verifier=None):
        """Mark a task done only after an injected independent verifier accepts evidence.

        The verifier receives (task_id, result, evidence). Raw evidence is not
        persisted; only its SHA-256 digest is stored for audit correlation.
        """
        if not callable(verifier):
            raise PermissionError("independent evidence verifier unavailable; fail-closed")
        if evidence is None:
            raise ValueError("verification evidence is required")
        result_json = _canonical(result if result is not None else {})
        evidence_json = _canonical(evidence)
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
            cur = con.execute(
                "UPDATE tasks SET status='done',updated_at=?,result=?,error=NULL,evidence_sha256=? "
                "WHERE id=? AND status='running'",
                (now, result_json, evidence_digest, task_id),
            )
            if cur.rowcount != 1:
                raise ValueError("Task not found or not running")
            self._audit(
                con, "complete_verified", task_id,
                {"result_sha256": result_digest, "evidence_sha256": evidence_digest,
                 "verification": "accepted"},
            )

    def fail(self, task_id, error):
        now = time.time()
        with self._connect() as con:
            cur = con.execute(
                "UPDATE tasks SET status='failed',updated_at=?,error=? "
                "WHERE id=? AND status='running'",
                (now, str(error), task_id),
            )
            if cur.rowcount != 1:
                raise ValueError("Task not found or not running")
            self._audit(con, "fail", task_id, {"error": str(error)})

    def audit_events(self):
        with self._connect() as con:
            rows = con.execute(
                "SELECT id,event,task_id,details,at FROM audit ORDER BY id"
            ).fetchall()
        return [
            dict(zip(("id", "event", "task_id", "details", "at"), row))
            for row in rows
        ]
