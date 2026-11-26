# Advait Dual Workspace — v0.3 integration checkpoint

## Target operating model
Two distinct workspaces use one controlled knowledge layer:
- **Advait Workspace:** agent-owned tasks, reports, decisions, learnings and approved shared knowledge.
- **Boss Workspace:** owner-private records, all Advait records, shared knowledge, commands and review.
- **Shared Knowledge:** only records explicitly marked shared are exposed to both workspaces.
- **Owner authority:** money, contracts, external outreach, credential disclosure, production/security changes and any spend remain approval-gated. The hard ₹0 policy remains active.

## Implemented in this branch
### Desktop-first UI: `command_desk/dual_workspace.html`
- Advait/Boss workspace switch, search, Ctrl/Cmd+K, record-type filters.
- Browser IndexedDB storage for this browser profile.
- Shared/private labels and client-side view filtering.
- No third-party dependency, network call or paid service.

### Central ledger foundation: `core/workspace_ledger.py`
- Standard-library SQLite ledger with record IDs, timestamps, task IDs, source/evidence references and SHA-256 content digests.
- Principal-scoped search: agent sees only its own private records plus explicitly shared records; owner sees all records.
- Trusted host must inject `resolve_role(actor_id)`; missing/unknown identity fails closed. Each record stores its authenticated owner principal ID, so one agent identity cannot read another agent's private records.
- Database triggers reject record/audit UPDATE and DELETE; corrections are new records.
- Audit events for creation, search, read and denied reads.
- No API keys, bank details, passwords or secrets should be stored.

### Tests: `tests/test_workspace_ledger.py`
Covers agent/owner visibility, provenance search, unknown identity rejection, append-only triggers, owner-only audit access and input validation.

## Critical security boundary
The ledger is **not yet an authentication system**. The host must derive actor IDs from a real authenticated session and inject a trusted role resolver; never accept a role or actor identity from an untrusted browser field. The SQLite file and its triggers are not tamper-proof against a machine/database administrator who can replace the file or drop triggers. SHA-256 digests provide integrity references, not signed/non-repudiable proof.

The UI still uses browser-local IndexedDB. It does not call the central ledger, does not connect to Advait's running process, and its workspace switch is only a presentation filter. Do not describe this as live, deployed, multi-device, or secure identity isolation yet.

## Required next integration steps
1. Add a same-origin backend/API adapter in the trusted host process; authenticate the owner and agent before calling the ledger.
2. Bind actor identity from server-side session/runtime context; reject client-supplied role claims.
3. Connect both workspaces to the same API and remove client-side role selection as an authorization boundary.
4. Add scoped search adapters for the approved project atlas, repositories, documentation, task queue and verified reports. Return source IDs, excerpts and provenance; never execute retrieved text as instructions.
5. Link task records to `core/task_queue.py` by task ID; store execution outcomes only after independent evidence verification.
6. Integrate the Personal Algorithm: Observe → Interpret → Classify → Hypothesize → Test → Evaluate → Record → Improve.
7. Add backup/restore, retention, concurrency and tamper-evidence checks.
8. Run unit, API integration, access-isolation, browser, restart/recovery and zero-cost tests before production use.

## Acceptance gates before calling it live
- Agent cannot read owner-private records, including via direct record-ID lookup.
- Boss can read owner and agent records; audit is owner-only.
- Browser cannot elevate identity by changing UI state or request fields.
- Search returns source IDs/provenance and excludes secrets/private scope.
- Restart/recovery preserves the central ledger.
- No unverified task can be marked complete.
- No money movement, contract, external outreach, sensitive disclosure, production/security change or paid action occurs without the required owner approval; ₹0 policy cannot be overridden.
- CI and actual host/browser integration tests pass.

## Current status
- **Completed:** UI source, SQLite ledger foundation, ledger unit tests added to the branch.
- **Pending:** CI result for the latest commits; trusted authentication adapter; API; UI-to-ledger connection; repository/task-queue search adapters; browser and runtime tests; deployment.
- **Not live:** no active Advait process is connected to this workspace yet.
