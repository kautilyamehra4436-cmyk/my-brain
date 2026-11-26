"""ATC-to-worker bridge using the managed SQLite runtime."""
from __future__ import annotations

from pathlib import Path
from core.atc_planner import ATCPlanner
from core.atc_worker_bridge_v1 import ATCWorkerBridgeV1
from core.managed_self_build_runtime_v1 import ManagedSelfBuildRuntimeV1


class ATCWorkerBridgeManagedV1(ATCWorkerBridgeV1):
    """Same explicit allowlisted bridge with deterministic queue connection cleanup."""

    def __init__(self, data_dir: str | Path):
        root = Path(data_dir)
        root.mkdir(parents=True, exist_ok=True)
        self.data_dir = root
        self.planner = ATCPlanner(root / "atc_thinking.db")
        self.runtime = ManagedSelfBuildRuntimeV1(root / "worker")
