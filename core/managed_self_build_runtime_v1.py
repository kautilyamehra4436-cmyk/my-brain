"""Managed local runtime using deterministic SQLite connection cleanup."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from core.managed_task_queue_v1 import ManagedTaskQueueV1
from core.self_build_factory_v1 import SelfBuildToolFactory
from core.worker import BoundedWorker


class ManagedSelfBuildRuntimeV1:
    """Manual bounded runner; not a daemon, scheduler, or 24/7 host."""

    def __init__(self, data_dir: str | Path):
        root = Path(data_dir)
        root.mkdir(parents=True, exist_ok=True)
        self.data_dir = root
        self.queue = ManagedTaskQueueV1(root / "advait_tasks.db")
        self.factory = SelfBuildToolFactory(root / "advait_tools.db")
        self.worker = BoundedWorker(
            self.queue,
            self.factory.worker_handlers(),
            evidence_verifier=self.factory.worker_evidence_verifier(),
        )

    def enqueue_tool_build(self, spec: dict[str, Any], tool_input: dict[str, Any],
                           *, title: str = "Build and run a local Advait tool") -> str:
        payload = {
            "execution_mode": "bounded_adapter",
            "adapter": "selfbuild.create_execute",
            "action": "local_analysis",
            "estimated_cost": 0,
            "free_quota_available": True,
            "risk": "low",
            "input": {"spec": spec, "input": tool_input},
        }
        return self.queue.enqueue(title, payload)

    def run_once(self) -> dict[str, Any]:
        return self.worker.run_once()

    def run_until_idle(self, max_tasks: int = 5) -> dict[str, Any]:
        if not isinstance(max_tasks, int) or isinstance(max_tasks, bool) or not 1 <= max_tasks <= 20:
            raise ValueError("max_tasks must be an integer from 1 to 20")
        outcomes = []
        for _ in range(max_tasks):
            outcome = self.run_once()
            if outcome.get("status") == "idle":
                break
            outcomes.append(outcome)
        return {
            "processed": len(outcomes),
            "done": sum(item.get("status") == "done" for item in outcomes),
            "failed": sum(item.get("status") == "failed" for item in outcomes),
            "outcomes": outcomes,
            "remaining_pending": len(self.queue.list_tasks(status="pending")),
            "data_dir": str(self.data_dir),
        }
