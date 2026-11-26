"""Governed managed self-build runtime v3."""
from __future__ import annotations
from pathlib import Path
from typing import Any
from core.managed_task_queue_v3 import ManagedTaskQueueV3
from core.governed_self_build_factory_v1 import GovernedSelfBuildToolFactoryV1
from core.worker import BoundedWorker
from core.b2b_reconciliation_adapter_v1 import (
    ADAPTER_NAME as B2B_ADAPTER_NAME,
    VERIFICATION_TYPE as B2B_VERIFICATION_TYPE,
    B2BAdapterUnavailable,
    B2BReconciliationAdapterV1,
)


class GovernedSelfBuildRuntimeV3:
    """Manually invoked bounded runtime; no daemon, scheduler or external I/O."""
    def __init__(self, data_dir: str | Path, *, b2b_reconciler=None):
        root=Path(data_dir)
        root.mkdir(parents=True, exist_ok=True)
        self.data_dir=root
        self.queue=ManagedTaskQueueV3(root/"advait_tasks.db")
        self.factory=GovernedSelfBuildToolFactoryV1(root/"advait_tools.db")
        self.b2b_adapter = None
        try:
            self.b2b_adapter = B2BReconciliationAdapterV1(
                root/"financial_vault_v1", reconciler=b2b_reconciler
            )
        except B2BAdapterUnavailable:
            # The pinned source submodule is optional for the generic Brain runtime.
            # B2B tasks fail closed until the exact submodule is initialized.
            self.b2b_adapter = None
        handlers = self.factory.worker_handlers()
        if self.b2b_adapter is not None:
            handlers.update(self.b2b_adapter.worker_handlers())
        self._factory_evidence_verifier = self.factory.worker_evidence_verifier()
        self.worker=BoundedWorker(
            self.queue, handlers,
            evidence_verifier=self._verify_evidence,
        )

    def _verify_evidence(self, task_id, result, evidence):
        if isinstance(evidence, dict) and evidence.get("verification_type") == B2B_VERIFICATION_TYPE:
            return bool(
                self.b2b_adapter is not None
                and self.b2b_adapter.verify_evidence(task_id, result, evidence)
            )
        return self._factory_evidence_verifier(task_id, result, evidence)

    @property
    def b2b_adapter_available(self) -> bool:
        return self.b2b_adapter is not None

    def stage_b2b_csv(
        self, content: bytes, *, owner_consented: bool = False,
        allow_unencrypted_storage: bool = False,
    ) -> dict[str, Any]:
        """Owner-invoked staging; source bytes go to the separate financial vault."""
        if owner_consented is not True:
            raise PermissionError("explicit_owner_consent_required_to_stage_financial_csv")
        if allow_unencrypted_storage is not True:
            raise PermissionError("explicit_unencrypted_storage_acknowledgement_required")
        if self.b2b_adapter is None:
            raise RuntimeError("pinned_advait_b2b_submodule_unavailable")
        return self.b2b_adapter.stage_csv(content, allow_unencrypted_storage=True)

    def enqueue_b2b_reconciliation(
        self, input_artifact_id: str, *, owner_confirmed: bool = False,
        title: str = "B2B CSV reconciliation",
    ) -> str:
        """Queue only an opaque vault ID; never place source CSV bytes in SQLite."""
        if owner_confirmed is not True:
            raise PermissionError("explicit_owner_confirmation_required_to_run_b2b_csv")
        if self.b2b_adapter is None:
            raise RuntimeError("pinned_advait_b2b_submodule_unavailable")
        self.b2b_adapter.vault.read_input(input_artifact_id)
        payload = {
            "execution_mode": "bounded_adapter",
            "adapter": B2B_ADAPTER_NAME,
            "action": "local_analysis",
            "estimated_cost": 0,
            "free_quota_available": True,
            "risk": "low",
            "input": {"input_artifact_id": input_artifact_id},
        }
        return self.queue.enqueue(title, payload)

    def enqueue_tool_build(self, spec: dict[str, Any], tool_input: dict[str, Any],
                           *, title: str="Governed self-build task") -> str:
        # Validate before enqueue; worker repeats preflight before any registry mutation.
        self.factory.preflight(spec, tool_input)
        payload={"execution_mode":"bounded_adapter","adapter":"selfbuild.create_execute",
                 "action":"local_analysis","estimated_cost":0,
                 "free_quota_available":True,"risk":"low",
                 "input":{"spec":spec,"input":tool_input}}
        return self.queue.enqueue(title,payload)

    def run_once(self)->dict[str,Any]:
        return self.worker.run_once()

    def run_until_idle(self,max_tasks:int=5)->dict[str,Any]:
        if not isinstance(max_tasks,int) or isinstance(max_tasks,bool) or not 1<=max_tasks<=5:
            raise ValueError("max_tasks must be an integer from 1 through 5")
        outcomes=[]
        for _ in range(max_tasks):
            out=self.run_once()
            if out.get("status")=="idle": break
            outcomes.append(out)
        return {"processed":len(outcomes),
                "done":sum(x.get("status")=="done" for x in outcomes),
                "failed":sum(x.get("status")=="failed" for x in outcomes),
                "outcomes":outcomes,
                "remaining_pending":len(self.queue.list_tasks(status="pending")),
                "queue_version":"ManagedTaskQueueV3",
                "lease_status":self.queue.lease_status()}
