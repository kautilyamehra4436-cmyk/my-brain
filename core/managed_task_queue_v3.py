"""Durable leased task queue with bounded crash recovery."""
from __future__ import annotations
import json
import time
from contextlib import contextmanager
from core.managed_sqlite_v1 import managed_connection
from core.task_queue import TaskQueue

class ManagedTaskQueueV3(TaskQueue):
    """TaskQueue-compatible queue with leases, attempts and expired-lease recovery."""

    requires_lease_owner = True
    def __init__(self, db_path="brain_tasks.db", *, default_lease_seconds=60, max_attempts=3):
        if not isinstance(default_lease_seconds,(int,float)) or isinstance(default_lease_seconds,bool) or default_lease_seconds<=0:
            raise ValueError("default_lease_seconds_must_be_positive")
        if not isinstance(max_attempts,int) or isinstance(max_attempts,bool) or not 1<=max_attempts<=20:
            raise ValueError("max_attempts_must_be_between_1_and_20")
        self.default_lease_seconds=float(default_lease_seconds)
        self.default_max_attempts=max_attempts
        super().__init__(db_path)

    @contextmanager
    def _connect(self):
        with managed_connection(self.db_path,timeout=10) as con:
            yield con

    def _init(self):
        super()._init()
        with self._connect() as con:
            columns={row[1] for row in con.execute("PRAGMA table_info(tasks)")}
            additions={
                "lease_owner":"TEXT",
                "lease_expires_at":"REAL",
                "attempts":"INTEGER NOT NULL DEFAULT 0",
                "max_attempts":"INTEGER NOT NULL DEFAULT 3",
            }
            for name, declaration in additions.items():
                if name not in columns:
                    con.execute(f"ALTER TABLE tasks ADD COLUMN {name} {declaration}")
            con.execute("""CREATE TRIGGER IF NOT EXISTS tasks_clear_lease_after_terminal
                AFTER UPDATE OF status ON tasks
                WHEN NEW.status IN ('done','failed') AND OLD.status != NEW.status
                BEGIN
                    UPDATE tasks SET lease_owner=NULL, lease_expires_at=NULL
                    WHERE id=NEW.id;
                END""")

    def enqueue(self,title,payload=None,*,max_attempts=None):
        limit=self.default_max_attempts if max_attempts is None else max_attempts
        if not isinstance(limit,int) or isinstance(limit,bool) or not 1<=limit<=20:
            raise ValueError("max_attempts_must_be_between_1_and_20")
        task_id=super().enqueue(title,payload)
        with self._connect() as con:
            con.execute("UPDATE tasks SET max_attempts=? WHERE id=?",(limit,task_id))
        return task_id

    def _recover_expired(self,con,now):
        rows=con.execute("""SELECT id,attempts,max_attempts FROM tasks
            WHERE status='running' AND lease_expires_at IS NOT NULL
            AND lease_expires_at<=? ORDER BY created_at""",(now,)).fetchall()
        recovered=failed=0
        for task_id,attempts,max_attempts in rows:
            if attempts>=max_attempts:
                con.execute("""UPDATE tasks SET status='failed',updated_at=?,error=?,
                    lease_owner=NULL,lease_expires_at=NULL WHERE id=? AND status='running'""",
                    (now,"lease_expired_max_attempts",task_id))
                self._audit(con,"lease_expired_failed",task_id,{"attempts":attempts})
                failed+=1
            else:
                con.execute("""UPDATE tasks SET status='pending',updated_at=?,error=?,
                    lease_owner=NULL,lease_expires_at=NULL WHERE id=? AND status='running'""",
                    (now,"lease_expired_requeued",task_id))
                self._audit(con,"lease_expired_requeued",task_id,{"attempts":attempts})
                recovered+=1
        return {"recovered":recovered,"failed":failed}

    def recover_expired_leases(self):
        now=time.time()
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            return self._recover_expired(con,now)

    def claim_next(self,eligible=None,*,worker_id="worker",lease_seconds=None):
        if not isinstance(worker_id,str) or not worker_id.strip() or len(worker_id)>128:
            raise ValueError("invalid_worker_id")
        duration=self.default_lease_seconds if lease_seconds is None else lease_seconds
        if not isinstance(duration,(int,float)) or isinstance(duration,bool) or duration<=0:
            raise ValueError("lease_seconds_must_be_positive")
        now=time.time()
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            self._recover_expired(con,now)
            rows=con.execute("""SELECT id,title,payload,max_attempts,attempts FROM tasks
                WHERE status='pending' ORDER BY created_at""").fetchall()
            for task_id,title,raw_payload,max_attempts,attempts in rows:
                try:
                    payload=json.loads(raw_payload)
                except (TypeError,ValueError):
                    if eligible is not None:
                        continue
                    payload={}
                if eligible is not None:
                    try:
                        if not eligible(payload):
                            continue
                    except Exception:
                        continue
                cur=con.execute("""UPDATE tasks SET status='running',updated_at=?,
                    lease_owner=?,lease_expires_at=?,attempts=attempts+1,error=NULL
                    WHERE id=? AND status='pending'""",
                    (now,worker_id,now+float(duration),task_id))
                if cur.rowcount!=1:
                    continue
                self._audit(con,"claim_leased",task_id,{"worker_id":worker_id,
                    "attempt":attempts+1,"lease_expires_at":now+float(duration)})
                return {"id":task_id,"title":title,"payload":payload,"status":"running",
                    "lease_owner":worker_id,"lease_expires_at":now+float(duration),
                    "attempt":attempts+1}
        return None

    def lease_status(self):
        with self._connect() as con:
            rows=con.execute("""SELECT status,COUNT(*) FROM tasks
                GROUP BY status ORDER BY status""").fetchall()
            leased=con.execute("""SELECT id,lease_owner,lease_expires_at,attempts,max_attempts
                FROM tasks WHERE status='running' ORDER BY created_at""").fetchall()
        return {"counts":dict(rows),"active_leases":[
            {"task_id":r[0],"worker_id":r[1],"lease_expires_at":r[2],
             "attempts":r[3],"max_attempts":r[4]} for r in leased]}
