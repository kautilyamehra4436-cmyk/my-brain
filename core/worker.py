"""Bounded, allowlisted worker for My Brain's existing SQLite task queue.

This is an execution framework, not an unrestricted shell or general-purpose agent.
Only host-registered Python handlers can run. No network, browser, payment, shell,
or filesystem handler is shipped by default. Handler code is trusted host code and
must enforce its own data/path/network contract.
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Callable

from core.zero_cost_guard import evaluate as zero_cost_evaluate
from core.task_queue import contains_sensitive_material


class BoundedWorker:
    """Execute at most one explicitly marked task using an allowlisted handler.

    Task payload contract:
      execution_mode: "bounded_adapter"
      adapter: registered handler key
      action: zero-cost guard action name
      estimated_cost: explicit numeric zero for the current hard-₹0 runtime
      free_quota_available: boolean
      risk: "low" | "high" | "critical"
      no credentials, approval tokens, API keys or passwords; the queue rejects these
      input: handler-specific JSON object

    Handler contract:
      handler(input) -> {"result": dict, "evidence": dict}

    Evidence and high-risk approval verifiers must be injected by the trusted host.
    Missing verifiers fail closed. This worker does not provide authentication,
    sandboxing, a scheduler, background execution, or production adapters.
    """

    def __init__(
        self,
        queue,
        handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]],
        *,
        evidence_verifier: Callable[[str, dict, dict], bool] | None,
        owner_approval_verifier: Callable[[str, str, dict], bool] | None = None,
        max_output_bytes: int = 65536,
        worker_id: str | None = None,
        lease_seconds: float = 300.0,
    ):
        if not isinstance(handlers, dict):
            raise TypeError("handlers must be an explicit allowlist mapping")
        if max_output_bytes < 1:
            raise ValueError("max_output_bytes must be positive")
        if not isinstance(lease_seconds, (int, float)) or isinstance(lease_seconds, bool) or lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        self.queue = queue
        self.lease_aware = bool(getattr(queue, "requires_lease_owner", False))
        if worker_id is None:
            worker_id = uuid.uuid4().hex
        if not isinstance(worker_id, str) or not worker_id.strip() or len(worker_id) > 128:
            raise ValueError("invalid worker_id")
        self.worker_id = worker_id
        self.lease_seconds = float(lease_seconds)
        self.handlers = dict(handlers)
        self.evidence_verifier = evidence_verifier
        self.owner_approval_verifier = owner_approval_verifier
        self.max_output_bytes = max_output_bytes

    @staticmethod
    def _eligible(payload: dict) -> bool:
        return isinstance(payload, dict) and payload.get("execution_mode") == "bounded_adapter"

    @staticmethod
    def _canonical_bytes(value: Any) -> bytes:
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")

    @staticmethod
    def _safe_reason(exc: Exception) -> str:
        message = str(exc)
        permission_codes = {
            "authenticated exact-action owner verifier unavailable": "owner_verifier_unavailable",
            "exact-action owner approval rejected": "owner_approval_rejected",
            "independent evidence verifier unavailable": "evidence_verifier_unavailable",
            "independent evidence verification failed; task remains running": "evidence_verification_failed",
            "sensitive_task_payload_blocked": "sensitive_task_payload_blocked",
            "unknown risk; fail closed": "unknown_risk",
        }
        value_codes = {
            "handler output exceeds configured byte limit": "handler_output_too_large",
            "handler must return exactly result and evidence objects": "invalid_handler_output",
            "result and evidence must be JSON objects": "invalid_handler_output",
            "handler input must be a JSON object": "invalid_handler_input",
            "free_quota_available must be boolean": "invalid_quota_state",
        }
        if isinstance(exc, PermissionError):
            return permission_codes.get(message, "permission_denied")
        if isinstance(exc, ValueError):
            return value_codes.get(message, "invalid_task_or_handler_output")
        return f"{type(exc).__name__.lower()}_execution_failed"

    def run_once(self) -> dict[str, Any]:
        """Run one eligible task; never executes plan-only queue records."""
        if self.lease_aware:
            task = self.queue.claim_next(
                eligible=self._eligible, worker_id=self.worker_id,
                lease_seconds=self.lease_seconds,
            )
        else:
            task = self.queue.claim_next(eligible=self._eligible)
        if task is None:
            return {"status": "idle", "reason": "no_bounded_adapter_task"}

        task_id = task["id"]
        payload = task["payload"]
        try:
            if contains_sensitive_material(payload):
                raise PermissionError("sensitive_task_payload_blocked")
            required = ("adapter", "action", "estimated_cost", "free_quota_available", "risk", "input")
            missing = [key for key in required if key not in payload]
            if missing:
                raise ValueError("missing task fields: " + ", ".join(missing))
            if not isinstance(payload["free_quota_available"], bool):
                raise ValueError("free_quota_available must be boolean")
            if not isinstance(payload["input"], dict):
                raise ValueError("handler input must be a JSON object")

            decision = zero_cost_evaluate(
                payload["action"],
                payload["estimated_cost"],
                free_quota_available=payload["free_quota_available"],
            )
            if not decision.allowed:
                raise PermissionError(decision.reason)

            risk = payload["risk"]
            if risk not in ("low", "high", "critical"):
                raise PermissionError("unknown risk; fail closed")
            if risk in ("high", "critical"):
                if not callable(self.owner_approval_verifier):
                    raise PermissionError("authenticated exact-action owner verifier unavailable")
                # Approval proof must be fetched by the trusted verifier out-of-band.
                # It must never be persisted in the operational task queue.
                try:
                    approved = bool(self.owner_approval_verifier(
                        task_id, payload["action"], payload
                    ))
                except Exception:
                    approved = False
                if not approved:
                    raise PermissionError("exact-action owner approval rejected")

            adapter_name = payload["adapter"]
            handler = self.handlers.get(adapter_name)
            if not isinstance(adapter_name, str) or not callable(handler):
                raise PermissionError("adapter is not in the host allowlist")

            output = handler(payload["input"])
            if not isinstance(output, dict) or set(output) != {"result", "evidence"}:
                raise ValueError("handler must return exactly result and evidence objects")
            if not isinstance(output["result"], dict) or not isinstance(output["evidence"], dict):
                raise ValueError("result and evidence must be JSON objects")
            output_size = len(self._canonical_bytes(output))
            if output_size > self.max_output_bytes:
                raise ValueError("handler output exceeds configured byte limit")
            if not callable(self.evidence_verifier):
                raise PermissionError("independent evidence verifier unavailable")

            completion = {
                "evidence": output["evidence"],
                "verifier": self.evidence_verifier,
            }
            if self.lease_aware:
                completion["worker_id"] = self.worker_id
            self.queue.complete(task_id, output["result"], **completion)
            return {"status": "done", "task_id": task_id, "verified": True}
        except Exception as exc:
            reason = self._safe_reason(exc)
            try:
                if self.lease_aware:
                    self.queue.fail(task_id, reason, worker_id=self.worker_id)
                else:
                    self.queue.fail(task_id, reason)
            except Exception as lease_exc:
                if self.lease_aware:
                    return {
                        "status": "lease_lost", "task_id": task_id,
                        "reason": reason,
                        "lease_error": "lease_state_changed_or_unavailable",
                    }
                raise
            return {"status": "failed", "task_id": task_id, "reason": reason}
