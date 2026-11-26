"""Run governed, zero-cost local self-build tasks."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from core.governed_self_build_runtime_v3 import GovernedSelfBuildRuntimeV3

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument("--db-dir",required=True)
 p.add_argument("--max-tasks",type=int,default=1)
 p.add_argument("--enqueue-sample",action="store_true")
 a=p.parse_args()
 if not 1<=a.max_tasks<=5: p.error("--max-tasks must be 1 through 5")
 rt=GovernedSelfBuildRuntimeV3(a.db_dir)
 if a.enqueue_sample:
  existing=rt.factory.list_tools()
  version=f"1.0.{len(existing)+1}"
  rt.enqueue_tool_build({"name":"text.counter","version":version,
   "operation":"text.word_count","description":"Counts bounded local text"},
   {"text":"Advait validates before registry mutation"})
 result=rt.run_until_idle(a.max_tasks)
 print(json.dumps(result,sort_keys=True))
 return 0 if result["failed"]==0 else 1
if __name__=="__main__": raise SystemExit(main())
