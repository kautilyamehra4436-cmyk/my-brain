"""Explicit bridge from ATC draft plans to the bounded local-tool worker.

This bridge never executes generic plan steps. A caller must explicitly select a
registered local tool operation and call enqueue_local_tool. Only low-risk,
zero-cost, allowlisted local operations can cross this bridge.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from core.atc_planner import ATCPlanner
from core.self_build_runtime_v1 import SelfBuildRuntimeV1


class ATCWorkerBridgeError(ValueError):
    """A plan or action is not eligible for the bounded local worker."""


class ATCWorkerBridgeV1:
    def __init__(self, data_dir: str | Path):
        root = Path(data_dir)
        root.mkdir(parents=True, exist_ok=True)
        self.data_dir = root
        self.planner = ATCPlanner(root / "atc_thinking.db")
        self.runtime = SelfBuildRuntimeV1(root / "worker")

    def plan(self, goal: str, *, context: str = "",
             constraints: list[str] | None = None) -> dict[str, Any]:
        """Create an ATC draft only; planning itself never queues or executes."""
        return self.planner.think(goal, context=context, constraints=constraints or [],
                                  estimated_cost=0, free_quota_available=True)

    def enqueue_local_tool(self, plan: dict[str, Any], spec: dict[str, Any],
                           tool_input: dict[str, Any], *,
                           title: str = "ATC reviewed local tool task") -> str:
        """Queue one explicitly selected local tool operation from a clean ATC draft."""
        if not isinstance(plan, dict) or plan.get("version") != "ATC-1.2.0":
            raise ATCWorkerBridgeError("current_atc_plan_required")
        if plan.get("status") != "DRAFT_PLAN" or plan.get("execution_status") != "NOT_EXECUTED":
            raise ATCWorkerBridgeError("plan_must_be_unexecuted_draft")
        if plan.get("risk_flags"):
            raise ATCWorkerBridgeError("owner_review_required_for_flagged_plan")
        if not isinstance(tool_input, dict):
            raise ATCWorkerBridgeError("tool_input_must_be_object")
        clean_spec = self.runtime.factory.validate_spec(spec)
        if not isinstance(title, str) or not title.strip() or len(title) > 200:
            raise ATCWorkerBridgeError("invalid_task_title")

        payload = {
            "execution_mode": "bounded_adapter",
            "adapter": "selfbuild.create_execute",
            "action": "local_analysis",
            "estimated_cost": 0,
            "free_quota_available": True,
            "risk": "low",
            "input": {"spec": clean_spec, "input": tool_input},
            "atc_record_id": plan["record_id"],
            "bridge_version": "ATC-WORKER-1.0",
        }
        return self.runtime.queue.enqueue(title.strip(), payload)

    def run_once(self) -> dict[str, Any]:
        return self.runtime.run_once()

    def task_status(self, task_id: str) -> dict[str, Any] | None:
        for task in self.runtime.queue.list_tasks():
            if task["id"] == task_id:
                return task
        return None

    def report(self, task_id: str) -> dict[str, Any]:
        task = self.task_status(task_id)
        if task is None:
            raise ATCWorkerBridgeError("task_not_found")
        import json
        payload = json.loads(task["payload"])
        return {
            "task_id": task_id,
            "status": task["status"],
            "atc_record_id": payload.get("atc_record_id"),
            "result": json.loads(task["result"]) if task.get("result") else None,
            "error": task.get("error"),
            "evidence_sha256": task.get("evidence_sha256"),
        }
