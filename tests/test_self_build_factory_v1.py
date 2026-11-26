import tempfile
import unittest
from pathlib import Path

from core.self_build_factory_v1 import (
    SelfBuildToolFactory, ToolExecutionError, ToolSpecError,
)
from core.task_queue import TaskQueue
from core.worker import BoundedWorker


class SelfBuildFactoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "tools.db"
        self.factory = SelfBuildToolFactory(self.db)

    def tearDown(self):
        self.temp.cleanup()

    def spec(self, operation="text.word_count", name="text.counter", version="1.0.0"):
        return {"name": name, "version": version, "operation": operation,
                "description": "A bounded local utility"}

    def test_build_and_execute_word_count(self):
        self.factory.build(self.spec())
        self.assertEqual(
            self.factory.execute("text.counter", "1.0.0", {"text": "one two\nthree"}),
            {"characters": 13, "words": 3, "lines": 2},
        )

    def test_build_rejects_unknown_operation(self):
        spec = self.spec()
        spec["operation"] = "python.eval"
        with self.assertRaises(ToolSpecError):
            self.factory.build(spec)

    def test_build_rejects_extra_spec_fields(self):
        spec = self.spec()
        spec["source_code"] = "import os"
        with self.assertRaises(ToolSpecError):
            self.factory.build(spec)

    def test_duplicate_version_is_rejected(self):
        self.factory.build(self.spec())
        with self.assertRaises(ToolSpecError):
            self.factory.build(self.spec())

    def test_new_version_is_additive(self):
        self.factory.build(self.spec(version="1.0.0"))
        self.factory.build(self.spec(version="1.1.0"))
        self.assertEqual(len(self.factory.list_tools()), 2)

    def test_registry_is_append_only(self):
        self.factory.build(self.spec())
        import sqlite3
        with sqlite3.connect(self.db) as con:
            with self.assertRaises(sqlite3.IntegrityError):
                con.execute("DELETE FROM tool_versions")

    def test_text_sha256(self):
        self.factory.build(self.spec("text.sha256", "text.hasher"))
        result = self.factory.execute("text.hasher", "1.0.0", {"text": "abc"})
        self.assertEqual(result["sha256"],
                         "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")

    def test_json_canonicalize(self):
        self.factory.build(self.spec("json.canonicalize", "json.canonical"))
        result = self.factory.execute("json.canonical", "1.0.0", {"value": {"b": 2, "a": 1}})
        self.assertEqual(result["canonical_json"], '{"a":1,"b":2}')

    def test_csv_profile(self):
        self.factory.build(self.spec("csv.profile", "csv.profiler"))
        result = self.factory.execute("csv.profiler", "1.0.0",
                                      {"csv_text": "name,score\nA,4\nB,5\n"})
        self.assertEqual(result["headers"], ["name", "score"])
        self.assertEqual(result["data_rows"], 2)

    def test_csv_rejects_inconsistent_rows(self):
        self.factory.build(self.spec("csv.profile", "csv.profiler"))
        with self.assertRaises(ToolExecutionError):
            self.factory.execute("csv.profiler", "1.0.0",
                                 {"csv_text": "a,b\n1\n"})

    def test_worker_runs_only_registered_factory_handler(self):
        queue = TaskQueue(Path(self.temp.name) / "tasks.db")
        payload = {
            "execution_mode": "bounded_adapter",
            "adapter": "selfbuild.create_execute",
            "action": "local_analysis",
            "estimated_cost": 0,
            "free_quota_available": True,
            "risk": "low",
            "input": {"spec": self.spec(), "input": {"text": "advait builds tools"}},
        }
        task_id = queue.enqueue("Build and run a local word counter", payload)
        worker = BoundedWorker(
            queue, self.factory.worker_handlers(),
            evidence_verifier=self.factory.worker_evidence_verifier(),
        )
        outcome = worker.run_once()
        self.assertEqual(outcome["status"], "done")
        self.assertEqual(outcome["task_id"], task_id)
        self.assertEqual(queue.list_tasks(status="done")[0]["result"] and
                         __import__("json").loads(queue.list_tasks(status="done")[0]["result"])["output"]["words"], 4)

    def test_worker_evidence_tampering_is_rejected(self):
        self.factory.build(self.spec())
        verify = self.factory.worker_evidence_verifier()
        result = {"tool": "text.counter", "version": "1.0.0", "output": {"words": 99}}
        evidence = {"tool_name": "text.counter", "tool_version": "1.0.0",
                    "spec_sha256": self.factory.get("text.counter", "1.0.0")["spec_sha256"],
                    "result_sha256": "bad", "verification_type": "registry_and_result_integrity"}
        self.assertFalse(verify("task", result, evidence))


if __name__ == "__main__":
    unittest.main()
