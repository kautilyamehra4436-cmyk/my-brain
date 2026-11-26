import tempfile
import unittest
from pathlib import Path

from core.self_build_runtime_v1 import SelfBuildRuntimeV1


class SelfBuildRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.runtime = SelfBuildRuntimeV1(Path(self.temp.name))

    def tearDown(self):
        self.temp.cleanup()

    def test_runtime_builds_and_executes_a_tool(self):
        task_id = self.runtime.enqueue_tool_build(
            {
                "name": "text.counter",
                "version": "1.0.0",
                "operation": "text.word_count",
                "description": "Counts words in local text",
            },
            {"text": "Advait makes its own tools"},
        )
        report = self.runtime.run_until_idle(1)
        self.assertEqual(report["processed"], 1)
        self.assertEqual(report["done"], 1)
        self.assertEqual(report["failed"], 0)
        self.assertEqual(report["outcomes"][0]["task_id"], task_id)
        self.assertEqual(report["remaining_pending"], 0)

    def test_runtime_rejects_unbounded_run_count(self):
        for value in (0, 21, True, 1.5):
            with self.assertRaises(ValueError):
                self.runtime.run_until_idle(value)

    def test_runtime_idle_without_tasks(self):
        report = self.runtime.run_until_idle(3)
        self.assertEqual(report["processed"], 0)
        self.assertEqual(report["done"], 0)
        self.assertEqual(report["failed"], 0)


if __name__ == "__main__":
    unittest.main()
