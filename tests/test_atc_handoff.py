import unittest
from core.atc_handoff import build_candidate, seal, SCHEMA_VERSION

class HandoffContractTests(unittest.TestCase):
    def record(self):
        return {"record_id":"ATC-1","status":"DRAFT_PLAN","execution_status":"NOT_EXECUTED"}
    def test_candidate_has_shared_schema_and_is_not_authorized(self):
        env=build_candidate(self.record(),task_id="T1",title="Review",tool="local",action="review",payload={})
        self.assertEqual(env["schema_version"],SCHEMA_VERSION)
        self.assertEqual(env["state"],"REVIEWED_NOT_AUTHORIZED")
        self.assertTrue(env["integrity"])
    def test_non_draft_rejected(self):
        r=self.record(); r["status"]="DONE"
        with self.assertRaises(ValueError):
            build_candidate(r,task_id="T1",title="Review",tool="local",action="review",payload={})
    def test_executed_record_rejected(self):
        r=self.record(); r["execution_status"]="DONE"
        with self.assertRaises(ValueError):
            build_candidate(r,task_id="T1",title="Review",tool="local",action="review",payload={})
    def test_bad_risk_rejected(self):
        with self.assertRaises(ValueError):
            build_candidate(self.record(),task_id="T1",title="Review",tool="local",action="review",payload={},risk="critical")
    def test_seal_detects_payload_change(self):
        env=build_candidate(self.record(),task_id="T1",title="Review",tool="local",action="review",payload={"a":1})
        env["payload"]["a"]=2
        expected=seal({k:v for k,v in env.items() if k!="integrity"})["integrity"]
        self.assertNotEqual(env["integrity"],expected)

if __name__=="__main__": unittest.main()
