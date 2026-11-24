"""ATC Thinking/Planning Core v1.2 for My Brain.
Rule-based, local-first decision support. No LLM, web, shell, external execution,
or owner authentication is implemented. Plans are drafts; queue integration only
stores plan steps and never executes them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from contextlib import closing
import time
import uuid
from pathlib import Path
from typing import Any, Optional

from core.zero_cost_guard import evaluate as zero_cost_evaluate

VERSION = "ATC-1.2.0"
MAX_TEXT = 4000
MAX_CONSTRAINT = 500

SENSITIVE_TERMS = {
    "money": ("payment", "transfer", "withdraw", "payout", "bank", "money", "paise", "rupee", "₹", "invoice payment"),
    "account_security": ("password", "token", "credential", "login", "permission", "security setting", "account change"),
    "legal": ("contract", "sign contract", "sign agreement", "signature", "legal", "tax filing", "compliance declaration"),
    "external_contact": ("send email", "send message", "contact client", "outreach", "publish", "submit bid", "submit bounty"),
    "destructive": ("delete", "erase", "drop database", "overwrite", "remove repository", "force push"),
    "sensitive_data": ("personal data", "customer data", "private file", "medical record", "financial record", "share data"),
}

SELF_QUESTIONS = [
    "क्या लक्ष्य स्पष्ट और मापने योग्य है?",
    "कौन-सी जानकारी अनुपस्थित है और किसे सत्यापन चाहिए?",
    "क्या किसी धारणा को तथ्य समझ लिया गया है?",
    "क्या कम-से-कम पाँच अलग रणनीतियाँ देखी गईं?",
    "क्या लागत/कोटा/संसाधन की सीमा स्पष्ट है?",
    "क्या कानूनी, गोपनीयता या platform जोखिम हैं?",
    "क्या कोई कार्रवाई irreversible या बाहरी प्रभाव वाली है?",
    "क्या योजना के प्रत्येक चरण का सत्यापन प्रमाण है?",
    "क्या असफल होने पर सुरक्षित fallback है?",
    "कौन-सा प्रमाण मेरी सिफारिश को गलत साबित करेगा?",
]

STRATEGY_BASE = [
    ("evidence_first", "प्रमाण-प्रथम", "पहले स्रोत/इनपुट और acceptance criteria सत्यापित करें; उसके बाद छोटा परीक्षण।", 72),
    ("low_resource", "कम-संसाधन", "फोन, स्थानीय processing और verified-free resources को प्राथमिकता; भारी काम टालें।", 70),
    ("risk_first", "जोखिम-प्रथम", "सबसे जोखिमपूर्ण धारणा/permission/data issue पहले जाँचें; safe path तय करें।", 69),
    ("creative_alternative", "मौलिक विकल्प", "समस्या को नए ढंग से परिभाषित कर कम-से-कम एक अलग समाधान खोजें।", 66),
    ("fallback", "Fallback", "मुख्य रास्ता विफल होने पर न्यूनतम उपयोगी परिणाम और recovery path तैयार रखें।", 65),
]


def _clean(value: Any, limit: int = MAX_TEXT) -> str:
    text = str(value or "").strip()
    text = "".join(ch for ch in text if ch in "\n\t" or ord(ch) >= 32)
    return text[:limit]


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def detect_risks(goal: str, context: str, constraints: list[str]) -> list[str]:
    haystack = " ".join([goal, context, *constraints]).casefold()
    flags = []
    for category, terms in SENSITIVE_TERMS.items():
        if any(term.casefold() in haystack for term in terms):
            flags.append(category)
    return sorted(set(flags))


def _adjust_score(strategy_id: str, base: int, goal: str, context: str, constraints: list[str], risk_flags: list[str]) -> int:
    text = " ".join([goal, context, *constraints]).casefold()
    score = base
    if any(x in text for x in ("phone", "mobile", "फोन", "android", "low ram", "कम संसाधन")) and strategy_id == "low_resource":
        score += 10
    if any(x in text for x in ("zero cost", "free", "₹0", "no subscription", "मुफ्त", "शून्य खर्च")) and strategy_id == "low_resource":
        score += 8
    if any(x in text for x in ("verify", "evidence", "accuracy", "test", "proof", "प्रमाण", "जाँच")) and strategy_id == "evidence_first":
        score += 8
    if any(x in text for x in ("unique", "novel", "original", "ultimate", "अनोखा", "मौलिक")) and strategy_id == "creative_alternative":
        score += 18
    if risk_flags and strategy_id == "risk_first":
        score += 15
    if any(x in text for x in ("deadline", "urgent", "time limit", "समय", "जल्दी")) and strategy_id == "fallback":
        score += 7
    return min(100, max(0, score))


class ATCLedger:
    """SQLite append-only event ledger with a hash chain; not tamper-proof against a writer."""
    def __init__(self, path: str | Path = "atc_thinking.db"):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as con, con:
            con.execute("CREATE TABLE IF NOT EXISTS atc_records (record_id TEXT PRIMARY KEY, record_json TEXT NOT NULL, created REAL NOT NULL)")
            con.execute("CREATE TABLE IF NOT EXISTS atc_events (seq INTEGER PRIMARY KEY AUTOINCREMENT, prev_hash TEXT NOT NULL, event_json TEXT NOT NULL, event_hash TEXT NOT NULL UNIQUE, created REAL NOT NULL)")

    def _connect(self):
        con = sqlite3.connect(self.path, timeout=10)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA foreign_keys=ON")
        return con

    def record(self, record: dict[str, Any]) -> str:
        record_digest = hashlib.sha256(_canonical({k: v for k, v in record.items() if k != "ledger_hash"}).encode("utf-8")).hexdigest()
        event = {"type": "thinking_record", "record_id": record["record_id"], "record_digest": record_digest, "version": VERSION}
        event_json = _canonical(event)
        with closing(self._connect()) as con, con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT event_hash FROM atc_events ORDER BY seq DESC LIMIT 1").fetchone()
            previous = row[0] if row else "0" * 64
            digest = hashlib.sha256(_canonical({"prev_hash": previous, "event": event}).encode("utf-8")).hexdigest()
            con.execute("INSERT INTO atc_records VALUES(?,?,?)", (record["record_id"], _canonical(record), time.time()))
            con.execute("INSERT INTO atc_events(prev_hash,event_json,event_hash,created) VALUES(?,?,?,?)", (previous,event_json,digest,time.time()))
        return digest

    def update_record(self, record: dict[str, Any]) -> None:
        with closing(self._connect()) as con, con:
            con.execute("UPDATE atc_records SET record_json=? WHERE record_id=?", (_canonical(record), record["record_id"]))

    def get(self, record_id: str) -> Optional[dict[str, Any]]:
        with closing(self._connect()) as con, con:
            row = con.execute("SELECT record_json FROM atc_records WHERE record_id=?", (record_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def verify(self) -> dict[str, Any]:
        previous = "0" * 64
        count = 0
        with closing(self._connect()) as con, con:
            rows = con.execute("SELECT prev_hash,event_json,event_hash FROM atc_events ORDER BY seq").fetchall()
            records = {row[0]: row[1] for row in con.execute("SELECT record_id,record_json FROM atc_records").fetchall()}
        for stored_prev, event_json, stored_hash in rows:
            event = json.loads(event_json)
            expected = hashlib.sha256(_canonical({"prev_hash": previous, "event": event}).encode("utf-8")).hexdigest()
            stored_record = records.get(event.get("record_id"))
            if not stored_record:
                return {"valid": False, "checked": count, "reason": "record_missing"}
            record = json.loads(stored_record)
            record_digest = hashlib.sha256(_canonical({k: v for k, v in record.items() if k != "ledger_hash"}).encode("utf-8")).hexdigest()
            if stored_prev != previous or stored_hash != expected or event.get("record_digest") != record_digest:
                return {"valid": False, "checked": count, "reason": "hash_chain_or_record_mismatch"}
            previous = stored_hash
            count += 1
        return {"valid": True, "checked": count, "reason": "chain_valid"}


class ATCPlanner:
    def __init__(self, ledger_path: str | Path = "atc_thinking.db"):
        self.ledger = ATCLedger(ledger_path)

    def think(self, goal: str, context: str = "", constraints: Optional[list[str]] = None,
              estimated_cost: Any = 0, free_quota_available: bool = True) -> dict[str, Any]:
        goal = _clean(goal)
        if not goal:
            raise ValueError("Goal must not be blank")
        context = _clean(context)
        clean_constraints = [_clean(x, MAX_CONSTRAINT) for x in (constraints or []) if _clean(x, MAX_CONSTRAINT)]
        cost_gate = zero_cost_evaluate("thinking", estimated_cost, free_quota_available=free_quota_available)
        if not cost_gate.allowed:
            raise PermissionError(f"Zero-cost gate blocked planning: {cost_gate.reason}")

        risks = detect_risks(goal, context, clean_constraints)
        strategies = []
        for sid, name, approach, base in STRATEGY_BASE:
            score = _adjust_score(sid, base, goal, context, clean_constraints, risks)
            strategies.append({"id": sid, "name": name, "approach": approach, "heuristic_score": score,
                              "score_is_validated": False, "selection_reason": "rule-based heuristic; not benchmarked"})
        strategies.sort(key=lambda x: (-x["heuristic_score"], x["id"]))
        recommended = strategies[0]
        requires_owner_approval = bool(risks)
        plan_steps = [
            {"step": 1, "task": "Goal and constraints review", "status": "plan_only", "approval_required": False},
            {"step": 2, "task": "Collect and record evidence/source provenance", "status": "plan_only", "approval_required": False},
            {"step": 3, "task": f"Prototype/test selected approach: {recommended['name']}", "status": "plan_only", "approval_required": False},
            {"step": 4, "task": "Independent quality and risk review", "status": "plan_only", "approval_required": False},
            {"step": 5, "task": "Report verified result, gaps, and next step", "status": "plan_only", "approval_required": False},
        ]
        record = {
            "record_id": _new_id("ATC"), "version": VERSION, "created_at": time.time(),
            "goal": goal, "context": context, "constraints": clean_constraints,
            "cost_gate": {"allowed": True, "reason": cost_gate.reason, "estimated_cost_for_planning": str(estimated_cost),
                          "execution_cost": "UNKNOWN_NOT_ESTIMATED"},
            "risk_flags": risks, "owner_approval_required_for_actions": requires_owner_approval,
            "strategies": strategies, "recommended_strategy": recommended,
            "self_questions": SELF_QUESTIONS.copy(), "plan_steps": plan_steps,
            "critic_findings": [
                "No live research or external evidence was collected by this module.",
                "Strategy scores are heuristics and have not been benchmark-calibrated.",
                "Risk keywords may miss or over-flag; human review remains necessary.",
                "No action was executed; plan is a draft.",
            ],
            "confidence": "LOW — deterministic rules/templates, not an LLM or empirical predictor",
            "execution_status": "NOT_EXECUTED", "evidence_status": "NOT_COLLECTED", "status": "DRAFT_PLAN",
        }
        record["ledger_hash"] = self.ledger.record(record)
        self.ledger.update_record(record)
        return record

    def enqueue_plan(self, queue, record: dict[str, Any]) -> list[str]:
        """Store draft plan steps in existing task queue. Queue workers do not execute payloads."""
        if record.get("version") != VERSION or record.get("status") != "DRAFT_PLAN":
            raise ValueError("Only current-version draft plans may be queued")
        ids = []
        for step in record["plan_steps"]:
            title = f"ATC {record['record_id']} · Step {step['step']}: {step['task']}"
            payload = {"atc_record_id": record["record_id"], "step": step["step"],
                       "status": "plan_only", "approval_required": step["approval_required"],
                       "risk_flags": record.get("risk_flags", [])}
            ids.append(queue.enqueue(title, payload))
        return ids

    def status(self) -> dict[str, Any]:
        return {"version": VERSION, "ledger_path": self.ledger.path, "ledger_integrity": self.ledger.verify(),
                "capabilities": ["rule_based_planning", "heuristic_strategy_comparison", "risk_keyword_flags", "sqlite_audit_chain"],
                "not_implemented": ["LLM reasoning", "live research", "external execution", "secure owner authentication", "background scheduler", "phone runtime verification"]}


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="ATC local-first draft planner (no execution)")
    parser.add_argument("--ledger", default="atc_thinking.db", help="SQLite ledger path")
    sub = parser.add_subparsers(dest="command", required=True)
    think_cmd = sub.add_parser("think", help="Create a draft thinking record")
    think_cmd.add_argument("goal")
    think_cmd.add_argument("--context", default="")
    think_cmd.add_argument("--constraint", action="append", default=[])
    think_cmd.add_argument("--cost", default="0", help="Cost of local planning run; nonzero/unknown blocks")
    think_cmd.add_argument("--quota-exhausted", action="store_true", help="Block if no free quota remains")
    think_cmd.add_argument("--enqueue", action="store_true", help="Store plan-only steps in the existing task queue")
    think_cmd.add_argument("--queue-db", default="brain_tasks.db")
    sub.add_parser("status", help="Show planner capabilities and ledger integrity")
    args = parser.parse_args(argv)
    planner = ATCPlanner(args.ledger)
    if args.command == "think":
        try:
            record = planner.think(args.goal, args.context, args.constraint, estimated_cost=args.cost, free_quota_available=not args.quota_exhausted)
        except (ValueError, PermissionError) as exc:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
            return 2
        if args.enqueue:
            from core.task_queue import TaskQueue
            record["queued_task_ids"] = planner.enqueue_plan(TaskQueue(args.queue_db), record)
        print(json.dumps(record, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps(planner.status(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
