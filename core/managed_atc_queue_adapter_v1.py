"""ATC draft-plan queue adapter using shared managed TaskQueue V2."""
from pathlib import Path
from typing import Any
from core.managed_task_queue_v2 import ManagedTaskQueueV2

class ManagedATCQueueAdapterV1:
    """Only stores ATC plan-only steps; it does not execute plan contents."""
    def __init__(self, db_path: str | Path):
        self.queue=ManagedTaskQueueV2(db_path)
    def enqueue_plan(self, record: dict[str, Any]) -> list[str]:
        if record.get("version")!="ATC-1.2.0" or record.get("status")!="DRAFT_PLAN":
            raise ValueError("Only current-version draft plans may be queued")
        ids=[]
        for step in record.get("plan_steps",[]):
            title=f"ATC {record['record_id']} · Step {step['step']}: {step['task']}"
            payload={"atc_record_id":record["record_id"],"step":step["step"],
                "status":"plan_only","approval_required":bool(step.get("approval_required")),
                "risk_flags":record.get("risk_flags",[])}
            ids.append(self.queue.enqueue(title,payload))
        return ids
