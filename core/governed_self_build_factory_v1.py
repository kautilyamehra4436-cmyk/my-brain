"""Governed self-build factory: preflight before registry mutation, idempotent retries."""
from __future__ import annotations
import hashlib
import json
from typing import Any
from core.self_build_factory_v1 import (
    SelfBuildToolFactory, ToolExecutionError, ToolSpecError,
    MAX_INPUT_BYTES, MAX_OUTPUT_BYTES, canonical_json, sha256_text,
)


class GovernedSelfBuildToolFactoryV1(SelfBuildToolFactory):
    """Only persist a tool after its input is structurally validated.

    Repeated identical task attempts are idempotent; conflicting version reuse fails closed.
    This still executes only the fixed operation catalogue inherited from v1.
    """

    @staticmethod
    def preflight(spec: dict[str, Any], data: dict[str, Any]) -> dict[str, str]:
        clean = SelfBuildToolFactory.validate_spec(spec)
        if not isinstance(data, dict):
            raise ToolExecutionError("input_must_be_object")
        op = clean["operation"]
        if op in {"text.word_count", "text.sha256"}:
            if set(data) != {"text"} or not isinstance(data["text"], str):
                raise ToolExecutionError("input_requires_text_string")
            if len(data["text"].encode("utf-8")) > MAX_INPUT_BYTES:
                raise ToolExecutionError("input_too_large")
        elif op == "json.canonicalize":
            if set(data) != {"value"}:
                raise ToolExecutionError("input_requires_value")
            try:
                encoded = canonical_json(data["value"])
            except (TypeError, ValueError) as exc:
                raise ToolExecutionError("value_is_not_finite_json") from exc
            if len(encoded.encode("utf-8")) > MAX_OUTPUT_BYTES:
                raise ToolExecutionError("output_too_large")
        elif op == "csv.profile":
            if set(data) != {"csv_text"} or not isinstance(data["csv_text"], str):
                raise ToolExecutionError("input_requires_csv_text")
            if len(data["csv_text"].encode("utf-8")) > MAX_INPUT_BYTES:
                raise ToolExecutionError("input_too_large")
        return clean

    def worker_handlers(self):
        def create_and_execute(data: dict[str, Any]) -> dict[str, Any]:
            if not isinstance(data, dict) or set(data) != {"spec", "input"}:
                raise ToolExecutionError("handler_requires_spec_and_input")
            clean = self.preflight(data["spec"], data["input"])
            encoded = canonical_json(clean)
            digest = sha256_text(encoded)
            existing = self.get(clean["name"], clean["version"])
            if existing is not None:
                if existing["spec_sha256"] != digest:
                    raise ToolSpecError("version_conflict_existing_record_not_modified")
                built = existing
            else:
                built = self.build(clean)
            output = self.execute(built["name"], built["version"], data["input"])
            result = {"tool": built["name"], "version": built["version"], "output": output}
            evidence = {
                "tool_name": built["name"], "tool_version": built["version"],
                "spec_sha256": built["spec_sha256"],
                "result_sha256": sha256_text(canonical_json(result)),
                "verification_type": "registry_and_result_integrity",
                "preflight": "passed",
            }
            return {"result": result, "evidence": evidence}
        return {"selfbuild.create_execute": create_and_execute}
