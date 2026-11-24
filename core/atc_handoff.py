"""ATC v1 -> Advait 100x portable handoff contract.

ATC plans remain drafts. This bridge only packages a separately reviewed candidate;
it does not authorize or execute anything.
"""
from __future__ import annotations
from hashlib import sha256
import json

SCHEMA_VERSION = "advait.task.v1"

def _canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

def seal(envelope: dict) -> dict:
    body = {k: v for k, v in envelope.items() if k != "integrity"}
    result = dict(body)
    result["integrity"] = sha256(_canonical(body).encode("utf-8")).hexdigest()
    return result

def build_candidate(record: dict, *, task_id: str, title: str, tool: str,
                    action: str, payload: dict, risk: str = "low") -> dict:
    if not isinstance(record, dict) or record.get("status") != "DRAFT_PLAN":
        raise ValueError("only an ATC DRAFT_PLAN can be referenced")
    if record.get("execution_status") != "NOT_EXECUTED":
        raise ValueError("ATC record must remain NOT_EXECUTED")
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    if risk not in ("low", "high"):
        raise ValueError("risk must be low or high")
    for key, value in (("task_id", task_id), ("title", title), ("tool", tool), ("action", action)):
        if not isinstance(value, str) or not value.strip() or len(value) > 200:
            raise ValueError(f"invalid {key}")
    body = {"schema_version": SCHEMA_VERSION, "task_id": task_id,
            "title": title, "tool": tool, "action": action, "payload": payload,
            "risk": risk, "state": "REVIEWED_NOT_AUTHORIZED",
            "source_atc_record": record.get("record_id", "")}
    return seal(body)
