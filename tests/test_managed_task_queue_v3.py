import tempfile
import time
import unittest
from pathlib import Path
from core.managed_task_queue_v3 import ManagedTaskQueueV3
from core.managed_sqlite_v1 import managed_connection

class ManagedTaskQueueV3Tests(unittest.TestCase):
    def test_claim_adds_lease_and_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            q=ManagedTaskQueueV3(Path(tmp)/"new"/"tasks.db")
            tid=q.enqueue("leased task",{"kind":"test"})
            item=q.claim_next(worker_id="worker-A",lease_seconds=30)
            self.assertEqual(item["id"],tid)
            self.assertEqual(item["attempt"],1)
            self.assertEqual(item["lease_owner"],"worker-A")
            self.assertEqual(q.lease_status()["active_leases"][0]["worker_id"],"worker-A")

    def test_expired_lease_requeues_and_can_be_reclaimed(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/"tasks.db"
            q=ManagedTaskQueueV3(db,default_lease_seconds=10,max_attempts=3)
            tid=q.enqueue("recover me",{})
            q.claim_next(worker_id="worker-A")
            with managed_connection(db) as con:
                con.execute("UPDATE tasks SET lease_expires_at=? WHERE id=?",(time.time()-1,tid))
            result=q.recover_expired_leases()
            self.assertEqual(result,{"recovered":1,"failed":0})
            again=q.claim_next(worker_id="worker-B")
            self.assertEqual(again["id"],tid)
            self.assertEqual(again["attempt"],2)

    def test_expired_lease_fails_after_attempt_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            db=Path(tmp)/"tasks.db"
            q=ManagedTaskQueueV3(db,max_attempts=1)
            tid=q.enqueue("do not loop forever",{})
            q.claim_next(worker_id="worker-A")
            with managed_connection(db) as con:
                con.execute("UPDATE tasks SET lease_expires_at=? WHERE id=?",(time.time()-1,tid))
            self.assertEqual(q.recover_expired_leases(),{"recovered":0,"failed":1})
            row=q.list_tasks()[0]
            self.assertEqual(row["status"],"failed")
            self.assertEqual(row["error"],"lease_expired_max_attempts")
            self.assertEqual(q.lease_status()["active_leases"],[])

    def test_invalid_lease_settings_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            q=ManagedTaskQueueV3(Path(tmp)/"tasks.db")
            q.enqueue("task",{})
            with self.assertRaises(ValueError): q.claim_next(worker_id="",lease_seconds=5)
            with self.assertRaises(ValueError): q.claim_next(worker_id="ok",lease_seconds=0)

    def test_terminal_transition_clears_lease(self):
        with tempfile.TemporaryDirectory() as tmp:
            q=ManagedTaskQueueV3(Path(tmp)/"tasks.db")
            tid=q.enqueue("finish",{})
            q.claim_next(worker_id="worker-A")
            q.complete(tid,{"ok":True},evidence={"proof":"unit"},verifier=lambda *_:True)
            self.assertEqual(q.list_tasks()[0]["status"],"done")
            self.assertEqual(q.lease_status()["active_leases"],[])

if __name__=="__main__":
    unittest.main()
