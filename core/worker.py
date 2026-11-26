"""Bounded, allowlisted worker for My Brain's existing SQLite task queue.

This is an execution framework, not an unrestricted shell or general-purpose agent.
Only host-registered Python handlers can run. No network, browser, payment, shell,
or filesystem handler is shipped by default. Handler code is trusted host code and
must enforce its own data/path/network contract.
"""
from __future__ import annotations

import json
from typing import Any, Callable

from core.zero_cost_guard import evaluate as zero_cost_evaluate


class BoundedWorker:
    """Execute at most one explicitly marked task using an allowlisted handler.

    Task payload contract:
      execution_mode: "bounded_adapter"
      adapter: registered handler key
      action: zero-cost guard action name
      estimated_cost: explicit numeric zero for the current hard-₹0 runtime
      free_quota_available: boolean
      risk: "low" | "high" | "critical"
      approval_token: optional opaque token; never logged by this worker
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
        owner_approval_verifier: Callable[[str, str, dict, str], bool] | None = None,
        max_output_bytes: int = 65536,
    ):
        if not isinstance(handlers, dict):
            raise TypeError("handlers must be an explicit allowlist mapping")
        if max_output_bytes < 1:
            raise ValueError("max_output_bytes must be positive")
        self.queue = queue
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

    def run_once(self) -> dict[str, Any]:
        """Run one eligible task; never executes plan-only queue records."""
        task = self.queue.claim_next(eligible=self._eligible)
        if task is None:
            return {"status": "idle", "reason": "no_bounded_adapter_task"}

        task_id = task["id"]
        payload = task["payload"]
        try:
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
                approval_token = payload.get("approval_token", "")
                safe_payload = {k: v for k, v in payload.items() if k != "approval_token"}
                try:
                    approved = bool(self.owner_approval_verifier(
                        task_id, payload["action"], safe_payload, approval_token
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

            self.queue.complete(
                task_id,
                output["result"],
                evidence=output["evidence"],
                verifier=self.evidence_verifier,
            )
            return {"status": "done", "task_id": task_id, "verified": True}
        except Exception as exc:
            reason = f"{type(exc).__name__}: {exc}"
            self.queue.fail(task_id, reason)
            return {"status": "failed", "task_id": task_id, "reason": reason}
