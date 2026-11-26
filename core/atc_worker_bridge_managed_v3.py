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

    def stage_b2b_csv(
        self, content: bytes, *, owner_consented: bool = False,
        allow_unencrypted_storage: bool = False,
    ):
        return self.runtime.stage_b2b_csv(
            content, owner_consented=owner_consented,
            allow_unencrypted_storage=allow_unencrypted_storage,
        )

    def enqueue_b2b_reconciliation(self, input_artifact_id: str, *, owner_confirmed: bool = False):
        return self.runtime.enqueue_b2b_reconciliation(
            input_artifact_id, owner_confirmed=owner_confirmed
        )
