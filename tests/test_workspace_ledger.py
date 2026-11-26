import tempfile
import unittest
from pathlib import Path

from core.workspace_ledger import WorkspaceLedger


class WorkspaceLedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "workspace.sqlite3")
        roles = {"owner-session": "owner", "agent-session": "agent"}
        self.ledger = WorkspaceLedger(self.db, resolve_role=roles.get)

    def tearDown(self):
        self.tmp.cleanup()

    def test_agent_sees_own_private_and_shared_but_not_owner_private(self):
        owner_private = self.ledger.create_record(
            "owner-session", kind="decision", title="Private owner decision",
            body="not for agent", visibility="private")
        agent_private = self.ledger.create_record(
            "agent-session", kind="learning", title="Agent notes",
            body="agent-only", visibility="private")
        shared = self.ledger.create_record(
            "owner-session", kind="resource", title="Approved tool",
            body="shared reference", visibility="shared")
        visible = {r["record_id"] for r in self.ledger.search("agent-session")}
        self.assertEqual(visible, {agent_private, shared})
        self.assertIsNone(self.ledger.get_record("agent-session", owner_private))

    def test_owner_can_search_all_records_and_provenance(self):
        private_id = self.ledger.create_record(
            "agent-session", kind="report", title="Run report", body="passed",
            visibility="private", source_ref="ci://run/123", evidence_ref="sha256:abc",
            task_id="task-42")
        rows = self.ledger.search("owner-session", query="ci://run/123")
        self.assertEqual([r["record_id"] for r in rows], [private_id])
        self.assertEqual(rows[0]["evidence_ref"], "sha256:abc")
        self.assertEqual(rows[0]["task_id"], "task-42")

    def test_unknown_identity_and_missing_resolver_fail_closed(self):
        with self.assertRaises(PermissionError):
            self.ledger.search("intruder")
        unconfigured = WorkspaceLedger(str(Path(self.tmp.name) / "empty.sqlite3"))
        with self.assertRaises(PermissionError):
            unconfigured.create_record(
                "agent-session", kind="task", title="x", body="y")

    def test_records_and_audit_are_append_only(self):
        record_id = self.ledger.create_record(
            "agent-session", kind="learning", title="Immutable", body="v1")
        import sqlite3
        with sqlite3.connect(self.db) as con:
            with self.assertRaises(sqlite3.IntegrityError):
                con.execute("UPDATE workspace_records SET body='tampered' WHERE record_id=?",
                            (record_id,))
            with self.assertRaises(sqlite3.IntegrityError):
                con.execute("DELETE FROM workspace_records WHERE record_id=?", (record_id,))
        self.assertEqual(self.ledger.get_record("owner-session", record_id)["body"], "v1")

    def test_agent_cannot_read_owner_audit(self):
        with self.assertRaises(PermissionError):
            self.ledger.audit_events("agent-session")
        events = self.ledger.audit_events("owner-session")
        self.assertTrue(any(e["event"] == "record_created" for e in events))

    def test_input_validation_and_search_filters(self):
        self.ledger.create_record(
            "agent-session", kind="task", title="Build index", body="Search adapter")
        self.ledger.create_record(
            "agent-session", kind="report", title="Test result", body="All good")
        self.assertEqual(len(self.ledger.search("agent-session", kind="task")), 1)
        self.assertEqual(len(self.ledger.search("agent-session", query="index")), 1)
        with self.assertRaises(ValueError):
            self.ledger.create_record(
                "agent-session", kind="unknown", title="x", body="y")
        with self.assertRaises(ValueError):
            self.ledger.create_record(
                "agent-session", kind="task", title="", body="y")


if __name__ == "__main__":
    unittest.main()
