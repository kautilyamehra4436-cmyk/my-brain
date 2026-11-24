import tempfile
import unittest
from pathlib import Path
from contextlib import closing
from core.atc_planner import ATCPlanner, VERSION
from core.task_queue import TaskQueue

class ATCPlannerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "atc.db"
        self.planner = ATCPlanner(self.db)
    def tearDown(self): self.tmp.cleanup()

    def test_blank_goal_rejected(self):
        with self.assertRaises(ValueError): self.planner.think("   ")
    def test_five_strategy_options(self):
        r = self.planner.think("Plan a small business validation workflow")
        self.assertEqual(len(r["strategies"]), 5)
    def test_ten_self_questions(self):
        self.assertEqual(len(self.planner.think("test")["self_questions"]), 10)
    def test_low_cost_mobile_constraints_boost_low_resource(self):
        r = self.planner.think("Create phone workflow", constraints=["phone-only", "zero cost"])
        self.assertEqual(r["recommended_strategy"]["id"], "low_resource")
    def test_evidence_words_boost_evidence_strategy(self):
        r = self.planner.think("Test accuracy and verify evidence")
        self.assertEqual(r["recommended_strategy"]["id"], "evidence_first")
    def test_novelty_words_boost_creative(self):
        r = self.planner.think("Find an original unique approach")
        self.assertEqual(r["recommended_strategy"]["id"], "creative_alternative")
    def test_sensitive_risk_flags_money(self):
        r = self.planner.think("Transfer money to vendor")
        self.assertIn("money", r["risk_flags"])
        self.assertTrue(r["owner_approval_required_for_actions"])
    def test_design_word_does_not_false_flag_legal_sign(self):
        r = self.planner.think("Design a workflow")
        self.assertNotIn("legal", r["risk_flags"])
    def test_sensitive_risk_flags_external_contact(self):
        r = self.planner.think("Send email to client")
        self.assertIn("external_contact", r["risk_flags"])
    def test_gate_does_not_authorize_action(self):
        r = self.planner.think("Sign contract")
        self.assertEqual(r["status"], "DRAFT_PLAN")
        self.assertEqual(r["execution_status"], "NOT_EXECUTED")
        self.assertTrue(r["owner_approval_required_for_actions"])
    def test_positive_cost_fail_closed(self):
        with self.assertRaises(PermissionError): self.planner.think("Plan", estimated_cost="0.01")
    def test_unknown_cost_fail_closed(self):
        with self.assertRaises(PermissionError): self.planner.think("Plan", estimated_cost="unknown")
    def test_quota_exhaustion_blocks(self):
        with self.assertRaises(PermissionError): self.planner.think("Plan", free_quota_available=False)
    def test_negative_cost_rejected(self):
        with self.assertRaises(PermissionError): self.planner.think("Plan", estimated_cost="-1")
    def test_plan_has_five_steps_and_plan_only(self):
        r = self.planner.think("Do something")
        self.assertEqual(len(r["plan_steps"]), 5)
        self.assertTrue(all(s["status"] == "plan_only" for s in r["plan_steps"]))
    def test_ledger_round_trip(self):
        r = self.planner.think("save record")
        self.assertEqual(self.planner.ledger.get(r["record_id"])["goal"], "save record")
        self.assertTrue(self.planner.ledger.verify()["valid"])
    def test_ledger_tamper_detected(self):
        self.planner.think("first")
        with closing(sqlite_connect(self.db)) as con:
            con.execute("UPDATE atc_events SET event_json='{}' WHERE seq=1")
            con.commit()
        self.assertFalse(self.planner.ledger.verify()["valid"])
    def test_record_tamper_detected(self):
        r = self.planner.think("record integrity")
        with closing(sqlite_connect(self.db)) as con:
            con.execute("UPDATE atc_records SET record_json='{}' WHERE record_id=?", (r["record_id"],))
            con.commit()
        self.assertFalse(self.planner.ledger.verify()["valid"])
    def test_queue_integration_only_stores_steps(self):
        queue = TaskQueue(Path(self.tmp.name) / "tasks.db")
        record = self.planner.think("prepare test plan")
        ids = self.planner.enqueue_plan(queue, record)
        self.assertEqual(len(ids), 5)
        tasks = queue.list_tasks()
        self.assertEqual(len(tasks), 5)
        self.assertTrue(all(t["status"] == "pending" for t in tasks))
        self.assertTrue(all(json_payload(t)["status"] == "plan_only" for t in tasks))
    def test_queue_rejects_wrong_version_or_status(self):
        r = self.planner.think("test")
        r["status"] = "EXECUTED"
        with self.assertRaises(ValueError): self.planner.enqueue_plan(TaskQueue(Path(self.tmp.name)/"q.db"), r)
    def test_input_is_bounded(self):
        r = self.planner.think("x"*9000, context="y"*9000, constraints=["z"*900])
        self.assertLessEqual(len(r["goal"]), 4000)
        self.assertLessEqual(len(r["context"]), 4000)
        self.assertLessEqual(len(r["constraints"][0]), 500)
    def test_no_live_research_claim(self):
        r = self.planner.think("research a topic")
        self.assertEqual(r["evidence_status"], "NOT_COLLECTED")
        self.assertIn("No live research", r["critic_findings"][0])
    def test_version(self): self.assertEqual(VERSION, "ATC-1.2.0")

def sqlite3_connect(path):
    import sqlite3
    return sqlite3.connect(path)
def json_payload(task):
    import json
    return json.loads(task["payload"])

if __name__ == "__main__": unittest.main(verbosity=2)
