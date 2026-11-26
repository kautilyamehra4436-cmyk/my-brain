"""ATC bridge V3 backed by leased, crash-recoverable task queue."""
from pathlib import Path
from core.atc_planner import ATCPlanner
from core.atc_worker_bridge_v1 import ATCWorkerBridgeV1
from core.governed_self_build_runtime_v3 import GovernedSelfBuildRuntimeV3

class ATCWorkerBridgeManagedV3(ATCWorkerBridgeV1):
    def __init__(self,data_dir: str | Path):
        root=Path(data_dir)
        root.mkdir(parents=True,exist_ok=True)
        self.data_dir=root
        self.planner=ATCPlanner(root/"atc_thinking.db")
        self.runtime=GovernedSelfBuildRuntimeV3(root/"worker")
