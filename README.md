# 🧠 My AI Brain — v9.0 ULTIMATE UNIQUE

> ₹0 खर्च • फोन-ओनली लक्ष्य • Open-Source • मालिक का नियंत्रण • Self-Evolution (अभी blueprint)

## 🚫 Zero-spend rule
**किसी भी स्थिति में ₹0 से अधिक खर्च नहीं।** Paid APIs/hosting/subscriptions/credit/loans/auto-renewals/paid upgrades बंद। Free quota समाप्त होने पर pause + report; paid fallback नहीं। See `config.yml`.

## 🚀 Quick Start
`START_HERE.md` → `onboarding.md`

## 🧪 Runtime / tests

Create a draft plan:
```sh
python -m core.atc_planner --ledger atc.db think "My goal" --constraint "phone-only" --constraint "zero cost"
python -m core.atc_planner --ledger atc.db think "My goal" --quota-exhausted
python -m core.atc_planner --ledger atc.db status
```
Add `--enqueue` only to store plan-only steps in the existing queue; it does not execute them.

- `RUNTIME_QUICKSTART.md`: setup, examples and test command.
- `tests/test_worker.py`: synthetic worker lifecycle, allowlist, cost/quota, approval and evidence-gate tests.
- `core/zero_cost_guard.py`: fail-closed helper for cost/quota/sensitive-action checks.
- `core/task_queue.py`: local SQLite task queue and audit log; it stores/claims tasks but does not execute payloads by itself.
- `core/worker.py`: bounded worker v0.1; executes only explicitly marked tasks through host-registered handlers, with zero-cost, approval and evidence-verification gates. No default external adapters are shipped.
- `core/workspace_ledger.py`: append-only SQLite workspace-record foundation; role-scoped search, source/evidence references and audit events. Requires a trusted host-injected identity resolver; it is not an authentication server or a deployed API.
- `tests/test_workspace_ledger.py`: tests owner/agent visibility, private-record isolation, append-only triggers and audit controls.
- `core/atc_planner.py`: ATC Thinking/Planning Core v1.2, merged to main; rule-based draft plans, risk flags, heuristic strategy comparison, SQLite integrity ledger. No LLM, web research or task execution.
- ATC integration map/FIR: `docs/ATC_INTEGRATION_MAP.md`, `docs/ATC_FIR_v1.2.md`.
- Dual workspace integration checkpoint: `docs/DUAL_WORKSPACE_V0.2.md`. UI and ledger foundation are separate; API/authentication and UI-to-ledger connection remain pending.
- GitHub Actions run #72: 38/38 tests passed (26 planner + 7 runtime + 5 handoff) and compile checks. Android/Termux and 24-hour stability remain untested.

## 🔌 Integrations
- `INTEGRATIONS.md`: open-source/free tools, integration order, caveats, status.
- `integrations/registry.json`: machine-readable registry.
- Verified connected now: GitHub repository access. Other entries are candidates/plans, not live integrations.

## 📊 Health Score
अभी: **0/100** (implementation/metrics not verified; score not yet computed)

## 📁 22 Layers
Foundation → Brain → Orchestrator → Workers → Engine → Memory → Smart → Security → Observability → Compliance → Gates → Revenue → Command → Tasks → Self-Evolve → Zero-Trust → Sovereign → Edge → Scale → Mobile → Soul → Emergence

## 🎯 MVP
Layer list is blueprint only until runtime tests verify it.

## ⚠️ Core boundaries
- Owner remains final authority.
- No spend, no paid service, no borrowing, no automatic reinvestment.
- Legal, payments, account changes, data sharing, and irreversible actions require owner control.
- Never claim integration, automation, earnings, or 24-hour operation unless actually tested.

## 📌 License: MIT
