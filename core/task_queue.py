"""Tiny SQLite task queue/audit log; no third-party packages."""
import json
import sqlite3
import time
import uuid

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
            con.execute("CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, title TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL, created_at REAL NOT NULL, updated_at REAL NOT NULL, result TEXT, error TEXT)")
            con.execute("CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT NOT NULL, task_id TEXT, details TEXT NOT NULL, at REAL NOT NULL)")

    def _audit(self, con, event, task_id, details):
        con.execute("INSERT INTO audit(event, task_id, details, at) VALUES(?,?,?,?)", (event, task_id, json.dumps(details, ensure_ascii=False), time.time()))

    def enqueue(self, title, payload=None):
        if not str(title).strip():
            raise ValueError("Task title cannot be blank")
        task_id, now = str(uuid.uuid4()), time.time()
        data = json.dumps(payload or {}, ensure_ascii=False)
        with self._connect() as con:
            con.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?)", (task_id, title.strip(), data, "pending", now, now, None, None))
            self._audit(con, "enqueue", task_id, {"title": title.strip()})
        return task_id

    def list_tasks(self, status=None):
        with self._connect() as con:
            query = "SELECT id,title,payload,status,created_at,updated_at,result,error FROM tasks"
            args = ()
            if status:
                query += " WHERE status=?"; args = (status,)
            query += " ORDER BY created_at"
            rows = con.execute(query, args).fetchall()
        return [dict(zip(("id","title","payload","status","created_at","updated_at","result","error"), r)) for r in rows]

    def claim_next(self):
        now = time.time()
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT id,title,payload FROM tasks WHERE status='pending' ORDER BY created_at LIMIT 1").fetchone()
            if not row:
                return None
            con.execute("UPDATE tasks SET status='running',updated_at=? WHERE id=? AND status='pending'", (now,row[0]))
            self._audit(con, "claim", row[0], {})
            return {"id": row[0], "title": row[1], "payload": json.loads(row[2]), "status": "running"}

    def complete(self, task_id, result=None):
        now = time.time()
        with self._connect() as con:
            cur = con.execute("UPDATE tasks SET status='done',updated_at=?,result=?,error=NULL WHERE id=? AND status='running'", (now,json.dumps(result,ensure_ascii=False),task_id))
            if cur.rowcount != 1: raise ValueError("Task not found or not running")
            self._audit(con, "complete", task_id, {"result": result})

    def fail(self, task_id, error):
        now = time.time()
        with self._connect() as con:
            cur = con.execute("UPDATE tasks SET status='failed',updated_at=?,error=? WHERE id=? AND status='running'", (now,str(error),task_id))
            if cur.rowcount != 1: raise ValueError("Task not found or not running")
            self._audit(con, "fail", task_id, {"error": str(error)})

    def audit_events(self):
        with self._connect() as con:
            rows = con.execute("SELECT id,event,task_id,details,at FROM audit ORDER BY id").fetchall()
        return [dict(zip(("id","event","task_id","details","at"),r)) for r in rows]
