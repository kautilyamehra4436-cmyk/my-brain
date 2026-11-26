import tempfile, unittest
from pathlib import Path
from core.governed_self_build_factory_v1 import GovernedSelfBuildToolFactoryV1
from core.governed_self_build_runtime_v3 import GovernedSelfBuildRuntimeV3
from core.self_build_factory_v1 import ToolExecutionError, ToolSpecError

SPEC={"name":"text.counter","version":"1.0.0","operation":"text.word_count","description":"Counts text"}

class GovernedFactoryTests(unittest.TestCase):
 def test_invalid_input_does_not_mutate_registry(self):
  with tempfile.TemporaryDirectory() as d:
   f=GovernedSelfBuildToolFactoryV1(Path(d)/"tools.db")
   with self.assertRaises(ToolExecutionError):
    f.worker_handlers()["selfbuild.create_execute"]({"spec":SPEC,"input":{"wrong":"x"}})
   self.assertEqual(f.list_tools(),[])

 def test_identical_retry_is_idempotent(self):
  with tempfile.TemporaryDirectory() as d:
   f=GovernedSelfBuildToolFactoryV1(Path(d)/"tools.db")
   h=f.worker_handlers()["selfbuild.create_execute"]
   data={"spec":SPEC,"input":{"text":"one two"}}
   first=h(data); second=h(data)
   self.assertEqual(first,second)
   self.assertEqual(len(f.list_tools()),1)

 def test_conflicting_version_fails_closed(self):
  with tempfile.TemporaryDirectory() as d:
   f=GovernedSelfBuildToolFactoryV1(Path(d)/"tools.db")
   h=f.worker_handlers()["selfbuild.create_execute"]
   h({"spec":SPEC,"input":{"text":"ok"}})
   changed={**SPEC,"description":"Different meaning"}
   with self.assertRaisesRegex(ToolSpecError,"version_conflict"):
    h({"spec":changed,"input":{"text":"ok"}})
   self.assertEqual(len(f.list_tools()),1)

 def test_runtime_builds_sample_with_managed_queue(self):
  with tempfile.TemporaryDirectory() as d:
   rt=GovernedSelfBuildRuntimeV3(d)
   task=rt.enqueue_tool_build(SPEC,{"text":"safe and bounded"})
   result=rt.run_until_idle(1)
   self.assertEqual(result["done"],1)
   self.assertEqual(rt.queue.list_tasks()[0]["id"],task)

 def test_task_limit_is_bounded(self):
  with tempfile.TemporaryDirectory() as d:
   rt=GovernedSelfBuildRuntimeV3(d)
   with self.assertRaises(ValueError): rt.run_until_idle(6)

if __name__=="__main__": unittest.main()
