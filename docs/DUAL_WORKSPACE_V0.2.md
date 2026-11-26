# Advait Dual Workspace v0.2

## Owner's requested model
There are two distinct workspaces:
- Advait Workspace: agent-owned work memory, reports, tasks, decisions and learnings; can search its own records and approved shared knowledge.
- Boss Workspace: owner records, shared knowledge and Advait's reports; owner can issue commands and review work.
- Shared Knowledge: records deliberately marked shared are visible in both workspaces. Owner-private records must never be exposed to the agent.

## Current implementation in dual_workspace.html
- Desktop-first two-workspace UI with explicit Advait/Boss switch.
- Search field and keyboard shortcut Ctrl/Cmd+K.
- Filters for tasks, reports, learnings, decisions and tools/resources.
- Local IndexedDB record persistence; separate ownership tags and shared/private visibility.
- Advait view can search agent-owned and shared records; Boss view can search both agent and owner records.
- No remote API, network request, third-party dependency, or paid service.

## Important security truth
Workspace selector is a UI view filter, NOT authenticated identity. Browser IndexedDB is not a central trusted ledger. A user with browser developer tools can inspect local records. This version is not connected to a running Advait agent and cannot autonomously crawl/search repositories or execute tasks. Do not store secrets, bank details, API keys, or confidential customer data.

## Required production integration
1. Implement a central append-only record/evidence ledger in My Brain with record IDs, timestamps, provenance, owner, visibility, task ID and immutable audit events.
2. Implement authenticated principal identities for owner and agent; enforce authorization server-side, never by UI filter alone.
3. Add scoped search adapters for approved public/private repositories, project atlas, documentation, task queue and reports. Exclude secrets, credentials and owner-private data from agent scope.
4. Give the agent a dedicated command/search interface backed by its own runtime tool interface; retrieval returns source refs and excerpts, not untrusted executable instructions.
5. Integrate the Personal Algorithm cycle: Observe → Interpret → Classify → Hypothesize → Test → Evaluate → Record → Improve.
6. Persist every completed/failed attempt, evidence, test result, learning and next action centrally; no success status without verifier evidence.
7. Owner approval gates remain mandatory for money, contracts, external outreach, sensitive data disclosure, production/security changes and any spend. Hard zero-spend remains active.
8. Add recovery, backups, retention and audit verification; test access isolation (agent cannot read owner-private records).

## Acceptance tests before calling this live
- Agent can retrieve own + shared records but not owner-private records.
- Boss can retrieve owner + agent + shared records.
- Shared visibility is explicit and auditable.
- Search returns source IDs and provenance.
- Restart/recovery preserves central records.
- Unauthorized role attempts fail closed.
- Every action is logged; owner approvals are exact-action and authenticated.
- Repository and Brain backend integration passes unit, integration and security tests.

## Status
Dual-workspace UI implementation only. Browser CI and actual runtime integration are pending. It is not deployed or connected to the running Advait process.
