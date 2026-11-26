# Advait Engine Integration Map — ATC v1.2
Date: 2026-11-27 | Status: planner + managed local execution bridge implemented; external integrations remain pending.
## Placement
ATC is the **Thinking/Planning Core** inside `my-brain`; it does not replace the task queue, zero-cost guard, bounded executor, business worker, or governance.
| Component | Canonical location | Responsibility | Relationship |
|---|---|---|---|
| Master Governance | `advait_pure_sharp/ChatGPT_0.1.md` | Authority, cost, security, legal, privacy, consent | Highest project policy |
| Master Operating Algorithm | `advait_pure_sharp/MASTER_OPERATING_ALGORITHM.md` | Work lifecycle, learning, research, test and evolution | Supervises methods |
| Command Centre | `advait_pure_sharp/ADVAIT_COMMAND_CENTRE.md` | Index, work register, activity and next actions | Record and navigation |
| Living Fabric / AELI | `advait_pure_sharp/ADVAIT_LIVING_FABRIC_ARCHITECTURE.md` | Routing, activation and cross-module coordination blueprint | System-level coordinator proposal |
| ATC Thinking Core | `my-brain/core/atc_planner.py` | Goal capture, heuristic strategy comparison, risk flags, plan draft, reflection questions | Planner; no execution |
| Zero-cost guard | `my-brain/core/zero_cost_guard.py` | Fail-closed cost/quota/sensitive-action helper | ATC planning gate; should be wired across future actions |
| Task queue | `my-brain/core/managed_task_queue_v3.py` over `core/task_queue.py` | Durable SQLite queue, leases, expiry recovery and bounded attempts | Canonical governed runtime uses V3; completion/failure is fenced by worker identity and lease expiry |
| Bounded worker | `my-brain/core/worker.py` | Host-allowlisted local handlers, zero-cost/risk/evidence gates | Manually invoked; no network, shell, browser, payment or external adapters by default |
| Governed runtime | `my-brain/core/governed_self_build_runtime_v3.py` | Fixed local tool operations and bounded execution | Uses ManagedTaskQueueV3; no daemon/scheduler/external I/O |
| Managed ATC bridge | `my-brain/core/atc_worker_bridge_managed_v3.py` | Explicitly selected ATC draft → local governed task | CI smoke verified; not an external business executor |
| Bounded execution reference | `advait-100x-research-audit/advait_engine.py` | Allowlist, budgets, approval binding, evidence/reconciliation | Separate reference implementation; no production adapters |
| Owner Approval Gate | advait_os/advait_gate_v01.py | Hardened local file gate with fail-closed verifier hook | v0.2 merged to main; HIGH/CRITICAL remain blocked without a real authenticated provider |
| PanchTatva C10 | `advait_pure_sharp/advait_panch_tatva_c10.py` | Rule-based 10-scenario simulation harness | Regression/scenario test suite, not intelligence proof |
| B2B reconciliation worker | `advait-100x-research-audit/b2b_reconcile.py` | CSV exception detection, normalized output, summary | Specialized task worker; source CSV is not overwritten |
## Safe handoff contract
1. ATC emits a `DRAFT_PLAN` with heuristic scores, risk flags, unknown execution cost, and `NOT_EXECUTED` state.
2. A human or approved planner may review/modify the plan.
3. The queue may store steps as `plan_only`; those remain ineligible for execution.
4. An owner or approved workflow must explicitly select a fixed local operation and provide its bounded input.
5. The managed V3 bridge routes only that selected task to the governed runtime; the worker checks allowlist, cost/quota, risk and evidence.
6. ManagedTaskQueueV3 fences terminal completion/failure by the active worker identity and unexpired lease. Lease heartbeat and multi-process stress remain pending.
7. This path performs no external customer action. Any future network, file-sharing, outreach, payment or contract adapter needs a separate reviewed contract, owner permission and independent evidence.
## Security findings to preserve
- Advait OS Gate v0.2 removed the hardcoded placeholder token, rejects sandbox/target symlinks, uses exclusive no-overwrite writes, and confines tests to TemporaryDirectory. Its 15 regression tests and Python compile check passed in GitHub Actions. No authenticated owner provider is deployed, so HIGH/CRITICAL actions remain denied by default.
- Advait 100x no longer treats a locally computable approval token as owner authentication. HIGH-risk tasks require an injected authenticated exact-task verifier; the offline repository ships no such provider, so they fail closed.
- The bounded engine requires an injected independent evidence verifier before marking a task DONE; adapter success alone is insufficient. Task payload/risk validation, duplicate-ID rejection, and adapter-copy isolation are regression-tested. Its optional SQLite ledger is unencrypted and not externally anchored; do not store credentials or source financial/legal records. No live action adapters exist.
- PanchTatva C10 is a static scenario harness. All 10 scenario rows are labeled PASS by its generator; the tests mostly validate report structure/phrases and do not demonstrate real decision behavior or device measurements.
- My Brain's zero-cost guard is fail-closed but not globally wired; task queue stores work only, and no orchestrator/dashboard/worker execution is verified.
## Conflicts found — preserve, do not silently rewrite
- `my-brain/config.yml` and README enforce hard ₹0; `revenue.md` lists positive cost caps (₹500/run, ₹2,000/day, ₹10,000/month) and margin assumptions. The hard-zero policy is controlling; the revenue document is inconsistent and needs owner-approved correction or archival.
- `authorization.md` describes Telegram/Face ID approval tiers and money thresholds; no such authenticated runtime is verified. Treat these as design claims only. ATC does not accept text approval or perform actions.
- `compliance.md` contains jurisdictional/legal assertions and a placeholder email. These need authoritative legal verification; they are not operational rules or legal advice. Avoid using the placeholder as personal data.
- `dashboard.md` commands are a conversation-level command map, not a deployed dashboard or persistent orchestrator.
- `status.md` health 0/100 is explicitly uncomputed; Android and 24-hour operation are untested.
## Review coverage boundary
Read-back covered the files linked/referenced by repository README/status and the key governing docs, code, tests, workflows and reports across the four accessible repositories. GitHub connector has no directory-tree listing in the currently exposed tools, and code search returned no indexed results, so this is **not a verified exhaustive inventory of every repository file**. Unlinked/unknown files may remain.

## Verified checkpoint — 2026-11-27

- My Brain PR #35 merged and CI run [45906541842](https://github.com/kautilyamehra4436-cmyk/my-brain/actions/runs/45906541842) passed.
- The canonical governed runtime now uses ManagedTaskQueueV3; the active ATC smoke script exercises ATCWorkerBridgeManagedV3.
- Stale-worker completion/failure is rejected by lease-owner and expiry checks.
- No LLM runtime, live research, external adapters, Android run, scheduler or 24-hour operation is verified.
- Four-repository path inventory: 206 files / 226 tree entries; see the canonical snapshot in the 100X repository.
