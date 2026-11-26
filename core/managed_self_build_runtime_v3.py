"""Self-build runtime V3 using durable leased queue and managed SQLite."""
from pathlib import Path
from typing import Any
from core.managed_task_queue_v3 import ManagedTaskQueueV3
from core.self_build_factory_v1 import SelfBuildToolFactory
from core.worker import BoundedWorker

class ManagedSelfBuildRuntimeV3:
    """Manual bounded worker runtime with expiring claims and bounded retry recovery."""
    def __init__(self,data_dir: str | Path,*,lease_seconds=60,max_attempts=3):
        root=Path(data_dir)
        root.mkdir(parents=True,exist_ok=True)
        self.data_dir=root
        self.queue=ManagedTaskQueueV3(root/"advait_tasks.db",
            default_lease_seconds=lease_seconds,max_attempts=max_attempts)
        self.factory=SelfBuildToolFactory(root/"advait_tools.db")
        self.worker=BoundedWorker(self.queue,self.factory.worker_handlers(),
            evidence_verifier=self.factory.worker_evidence_verifier())
    def enqueue_tool_build(self,spec:dict[str,Any],tool_input:dict[str,Any],
                           *,title="Build and run a local Advait tool",max_attempts=None):
        payload={"execution_mode":"bounded_adapter","adapter":"selfbuild.create_execute",
            "action":"local_analysis","estimated_cost":0,"free_quota_available":True,
            "risk":"low","input":{"spec":spec,"input":tool_input}}
        return self.queue.enqueue(title,payload,max_attempts=max_attempts)
    def run_once(self):
        return self.worker.run_once()
    def run_until_idle(self,max_tasks=5):
        if not isinstance(max_tasks,int) or isinstance(max_tasks,bool) or not 1<=max_tasks<=20:
            raise ValueError("max_tasks must be an integer from 1 to 20")
        outcomes=[]
        for _ in range(max_tasks):
            item=self.run_once()
            if item.get("status")=="idle": break
            outcomes.append(item)
        return {"processed":len(outcomes),"done":sum(x.get("status")=="done" for x in outcomes),
            "failed":sum(x.get("status")=="failed" for x in outcomes),"outcomes":outcomes,
            "remaining_pending":len(self.queue.list_tasks(status="pending")),
            "lease_status":self.queue.lease_status(),"data_dir":str(self.data_dir),
            "queue_version":"ManagedTaskQueueV3"}
