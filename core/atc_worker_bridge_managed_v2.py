"""ATC bridge V2 with shared SQLite lifecycle across worker queue operations."""
from pathlib import Path
from core.atc_planner import ATCPlanner
from core.atc_worker_bridge_v1 import ATCWorkerBridgeV1
from core.managed_self_build_runtime_v2 import ManagedSelfBuildRuntimeV2

class ATCWorkerBridgeManagedV2(ATCWorkerBridgeV1):
    """Preserves explicit allowlisted bridge behavior and upgrades queue lifecycle."""
    def __init__(self, data_dir: str | Path):
        root=Path(data_dir)
        root.mkdir(parents=True,exist_ok=True)
        self.data_dir=root
        self.planner=ATCPlanner(root/"atc_thinking.db")
        self.runtime=ManagedSelfBuildRuntimeV2(root/"worker")
