# Repository Reconciliation & Engine Placement — 2026-11-24
## Coverage
The review read the known/reference-linked files and reports from four repositories. GitHub metadata confirms:
- `my-brain`: public
- `advait_pure_sharp`: private
- `advait-100x-research-audit`: public
- `advait_os`: private
The connector currently exposes file fetch/search/commit tools but no directory-tree listing; repository code search returned no indexed results. Therefore this review is a **known-file inventory, not a guaranteed exhaustive file-by-file census**.
## Repositories and what was reviewed
### 1) My Brain v9.0 — public
Reviewed README, START_HERE, onboarding, dashboard, SOUL, rules, config, runtime quickstart, integrations guide/registry, zero-cost guard, task queue, runtime tests, status, revenue, tasks, dreams, compliance, session, authorization, errors/troubleshoot and related workflow/test instructions.
**Current reality:** zero-cost guard exists and has five tests; SQLite task queue exists and has lifecycle/audit tests; the 7-test runtime suite passes in the prior recorded local environment. The guard is not globally wired, queue stores tasks without executing payloads, dashboard/orchestrator/workers are not implemented, Android/Termux and 24-hour tests are not performed. Health score 0/100 is explicitly uncomputed.
### 2) Advait Pure Sharp — private
Reviewed ChatGPT governance file, Master Operating Algorithm, Command Centre, Living Fabric/AELI architecture, PanchTatva-C10 source/tests/workflow and C10 test report.
**Current reality:** Master Algorithm and governance are blueprints/rules; Living Fabric is an architecture proposal. PanchTatva C10 is a rule-based simulation with 10 fixed scenario rows; its generator marks each row PASS. Its three tests verify output structure, sequential scenario IDs, and safety phrases. The report says GitHub Actions pending, device measurements and real-world validation not performed. It is not a measured AI/hardware/self-evolution benchmark.
### 3) Advait 100x Research Audit — public
Reviewed README-linked reports (engine/B2B blueprint, discovery/daily report, status, phone-run notes, benchmark plan, master/source audit), bounded engine, test harness, B2B reconciliation source/tests/sample CSV and workflow, plus local test result record.
**Current reality:** bounded offline/mock engine has strict allowlist/budgets, fail-closed high-risk approval-verifier hook, independent evidence-verifier requirement for DONE, strict payload/risk validation, duplicate-ID rejection, adapter-copy isolation, hash-linked in-memory ledger, and optional atomic SQLite operational ledger. Latest CI passed 31 engine/handoff tests, 10 harness checks and 9 B2B reconciliation tests. No authenticated owner provider, evidence provider, live adapters, Android run, or 24-hour soak test is deployed. SQLite is unencrypted and is not for credentials or source financial/legal records. B2B reconciliation processes CSV and emits exception reports; it is not a live accounting integration.
### 4) Advait OS Gate — private
Reviewed README, `advait_gate_v01.py` and `.github/workflows/run-gate.yml`. No separate test file or gate report was found at the guessed paths; tests are embedded in the script (16 checks).
**Security status after Gate v0.2:** the hardcoded token is removed; symlink/path traversal and overwrite risks are addressed; tests now use TemporaryDirectory; 15 security regression tests and Python compilation passed in GitHub Actions. HIGH/CRITICAL actions still fail closed because no real authenticated owner provider is deployed. This is a local filesystem gate, not a complete OS sandbox or production identity provider.
## Engine placement decision
| Layer | Engine | Keep / use |
|---|---|---|
| Governance | ChatGPT_0.1 + Master Operating Algorithm | Governing rules and task lifecycle |
| Coordination blueprint | Living Fabric / AELI | System-level routing design; not yet runtime |
| Thinking / planning | ATC v1.2 | My Brain core; generate draft plans, alternatives, risk flags, reflection questions |
| Work storage | My Brain TaskQueue | Store plan-only task steps; no executor |
| Cost gate | My Brain ZeroCostGuard | Hard ₹0 gate; fail closed |
| Bounded execution reference | Advait 100x Engine | Future execution adapter only after owner-auth verification and sandbox hardening |
| Security gate | Advait OS Gate v0.2 | Local file gate hardened; keep HIGH/CRITICAL disabled until authenticated provider exists |
| Scenario/regression | PanchTatva C10 | Simulated test scenarios only |
| Specialized business worker | B2B reconciliation | CSV validation/exception reports; no external finance action |
**No duplicate queue, executor, or approval gate is added to ATC.** ATC has no network, shell, model, or external-action adapter.
## Cross-file conflicts
1. Hard ₹0 policy in README/config conflicts with revenue.md's positive caps (₹500/run, ₹2,000/day, ₹10,000/month). Strict ₹0 remains controlling; revenue caps are not authorized budgets.
2. authorization.md describes Telegram/Face ID and monetary tiers, but no such verified runtime exists.
3. compliance.md contains unverified legal/regulatory assertions and a placeholder contact. Re-check authoritative sources before treating them as requirements.
4. dashboard.md describes conversational command routing, not a deployed dashboard or 24/7 service.
5. task list has blank P0 entries and future schedules; these are not active jobs.
## Immediate priorities
- P0: implement and independently review a real authenticated owner provider; keep HIGH/CRITICAL disabled until then.
- P0: connect a separately reviewed evidence verifier to trusted sources; adapter claims alone must not mark work complete.
- P1: wire the zero-cost guard across all actions and make quota exhaustion stop; keep ATC plans draft-only.
- P1: test ATC on phone/Termux, resource use, longer run and regression.
- P1: correct documentation contradictions only with owner-approved changes; don't silently raise the budget.
- P2: implement real research with source provenance, model adapter (if free and approved), task execution sandbox, rollback and notifications only after gates.
- P2: define measurable health metrics and calculate health score; do not reuse 0/100 as a computed metric.
## ATC v1.2 branch status
ATC v1.2 and the shared reviewed-only handoff are now included in My Brain PR #1. Latest GitHub Actions run #67 passed 38 tests (26 planner + 7 runtime + 5 handoff) and compile checks. Android/Termux, 24-hour stability, live research, external execution and earnings remain untested.