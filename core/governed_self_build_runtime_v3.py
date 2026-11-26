"""Governed managed self-build runtime v3."""
from __future__ import annotations
from pathlib import Path
from typing import Any
from core.managed_task_queue_v1 import ManagedTaskQueueV1
from core.governed_self_build_factory_v1 import GovernedSelfBuildToolFactoryV1
from core.worker import BoundedWorker


class GovernedSelfBuildRuntimeV3:
    """Manually invoked bounded runtime; no daemon, scheduler or external I/O."""
    def __init__(self, data_dir: str | Path):
        root=Path(data_dir)
        root.mkdir(parents=True, exist_ok=True)
        self.data_dir=root
        self.queue=ManagedTaskQueueV1(root/"advait_tasks.db")
        self.factory=GovernedSelfBuildToolFactoryV1(root/"advait_tools.db")
        self.worker=BoundedWorker(
            self.queue, self.factory.worker_handlers(),
            evidence_verifier=self.factory.worker_evidence_verifier(),
        )

    def enqueue_tool_build(self, spec: dict[str, Any], tool_input: dict[str, Any],
                           *, title: str="Governed self-build task") -> str:
        # Validate before enqueue; worker repeats preflight before any registry mutation.
        self.factory.preflight(spec, tool_input)
        payload={"execution_mode":"bounded_adapter","adapter":"selfbuild.create_execute",
                 "action":"local_analysis","estimated_cost":0,
                 "free_quota_available":True,"risk":"low",
                 "input":{"spec":spec,"input":tool_input}}
        return self.queue.enqueue(title,payload)

    def run_until_idle(self,max_tasks:int=5)->dict[str,Any]:
        if not isinstance(max_tasks,int) or isinstance(max_tasks,bool) or not 1<=max_tasks<=5:
            raise ValueError("max_tasks must be an integer from 1 through 5")
        outcomes=[]
        for _ in range(max_tasks):
            out=self.worker.run_once()
            if out.get("status")=="idle": break
            outcomes.append(out)
        return {"processed":len(outcomes),
                "done":sum(x.get("status")=="done" for x in outcomes),
                "failed":sum(x.get("status")=="failed" for x in outcomes),
                "outcomes":outcomes,
                "remaining_pending":len(self.queue.list_tasks(status="pending"))}
