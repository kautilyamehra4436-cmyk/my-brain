# Advait v32.0 — Provider Integration and 50-Point Gap Audit v1

Date: 2026-11-27
Branch: advait-provider-router-audit-v1-2026-11-27

## Scope and truth gate

This is a source-level review of the inspected My Brain workspace, SQLite ledger, task queue, bounded worker, configuration and integration registry. It is not a complete line-by-line audit of every Advait repository and is not proof of a deployed runtime. A finding marked "added" means code or policy was added on this branch; it does not mean CI or production behavior has passed.

## Provider architecture

- Advait remains the orchestrator and source of truth. OpenAI and OpenRouter are model providers only; they are not the Boss, scheduler, database, browser or execution host.
- OpenRouter is allowed only with an explicit model identifier ending in :free under the current zero-spend policy.
- OpenAI API calls are blocked by default because API usage is billable. They remain blocked until the owner explicitly authorizes a positive budget and a separately reviewed policy change is implemented.
- There is no automatic paid fallback. Free quota/rate-limit failures must pause and be recorded.
- API keys are read from OPENROUTER_API_KEY and OPENAI_API_KEY at runtime. Never commit keys, print them, place them in browser storage or write them to the audit database.
- The new provider module makes one bounded text call only. It does not browse, book, message customers, move money, execute arbitrary code, run a daemon or provide 24/7 scheduling.
- Audit records store provider, model, request/response hashes, status, HTTP status, latency, usage, reported cost and sanitized error code. Prompt and response bodies are not stored.

## 50-point gap register

| # | Finding / risk | Remediation | Status |
|---:|---|---|---|
| 01 | No runtime provider adapter | Add bounded provider adapter | Added; CI pending |
| 02 | No explicit provider allowlist | Add provider allowlist | Added |
| 03 | OpenAI paid API conflicts with hard-zero policy | Block paid API by default | Added; blocked |
| 04 | OpenRouter paid models could be selected accidentally | Require :free suffix | Added |
| 05 | Provider calls lack durable metadata records | SQLite call ledger | Added |
| 06 | Prompt bodies could leak into logs | Store request hash only | Added |
| 07 | Response bodies could leak into logs | Store response hash only | Added |
| 08 | API key could leak in exception details | Sanitized errors | Added; security test pending |
| 09 | Audit rows could be changed by ordinary SQL | Append-only triggers | Added; DB-file owner can still tamper |
| 10 | Usage/cost not correlated with request | Persist usage and reported cost | Added |
| 11 | Provider latency not measured | Persist latency | Added |
| 12 | HTTP failures not represented | Record sanitized HTTP failure | Added; CI pending |
| 13 | Missing keys could trigger confusing retries | Fail before network call | Added |
| 14 | Free quota exhaustion not centrally monitored | Add quota probe and pause circuit | Pending |
| 15 | Fallback could silently become paid | Prohibit paid fallback | Added |
| 16 | No provider health/circuit breaker | Add bounded health state/cooldown | Pending |
| 17 | No retry/backoff policy | Add capped retry with idempotency rules | Pending |
| 18 | No request idempotency contract | Add request fingerprint/dedupe | Pending |
| 19 | No per-task provider budget ledger | Add daily/task budget accounting | Pending |
| 20 | No exact owner approval for budget changes | Add signed scoped approval record | Pending |
| 21 | No API schema compatibility tests | Add provider contract fixtures | Pending |
| 22 | No structured function/tool-call bridge | Add validated dispatcher | Pending |
| 23 | Model output not independently validated | Add schema and evidence validation | Pending |
| 24 | Provider result not linked to task queue | Add task adapter and correlation ID | Pending |
| 25 | Provider result not linked to workspace ledger | Append provider metadata to shared ledger | Pending |
| 26 | No correlation ID across task/provider/evidence | Propagate immutable ID | Pending |
| 27 | No authenticated runtime identity in provider layer | Inject trusted host identity | Pending |
| 28 | No workspace data isolation at provider boundary | Add classification/redaction | Pending |
| 29 | No secret redaction scanner | Add preflight scanner | Pending |
| 30 | No retention policy for provider metadata | Define retention/export policy | Pending |
| 31 | SQLite audit is not tamper-proof against file owner | Add signed external checkpoints | Pending |
| 32 | No encrypted local database/backup | Add OS-backed encryption/export | Pending |
| 33 | No backup/restore test for provider ledger | Add recovery tests | Pending |
| 34 | No concurrent load test for ledger | Add concurrent read/write stress test | Pending |
| 35 | Queue lacks leases/heartbeat/recovery | Add lease expiry and stale recovery | Pending |
| 36 | Worker has no scheduler | Add owner-configured scheduler | Pending |
| 37 | Worker has no process supervision | Add restart and graceful-stop controls | Pending |
| 38 | Worker has no process/network sandbox | Add OS/container isolation | Pending |
| 39 | No outbound domain allowlist | Enforce host-level egress allowlist | Pending |
| 40 | No browser automation adapter | Evaluate open-source browser agent behind gates | Pending |
| 41 | No customer/bounty discovery adapters | Build read-only sourced adapters | Pending |
| 42 | No maker/tool/license catalog | Record purpose, license, maintenance and risk | Pending |
| 43 | No version-specific license audit | Capture SPDX/license/version/commit evidence | Pending |
| 44 | No dependency vulnerability scan | Add SBOM and dependency scanning | Pending |
| 45 | No supply-chain provenance | Pin dependencies and record hashes | Pending |
| 46 | Workspace switch is not authentication | Enforce server-side identity | Pending |
| 47 | IndexedDB is not central multi-device storage | Connect through authenticated backend | Pending |
| 48 | No browser/API end-to-end security tests | Add role, CSRF, XSS, injection and session tests | Pending |
| 49 | No 24-hour endurance/Android background test | Run measured endurance tests | Pending |
| 50 | No proven business workflow from lead to paid delivery | Prove sourced lead, sandbox task, approved delivery and reconciled payment | Pending |

## Open-source tools to evaluate — not installed or connected

- Browser Use (MIT): browser agent framework. Evaluate local resource use, profile isolation, tool permissions and pinned version before adoption.
- Playwright (Apache-2.0): deterministic browser automation and testing; it is not itself a business agent.
- SQLite (public domain): local ledger/task storage; still needs backup, encryption and trusted host controls.
- Python (PSF license): adapter/runtime language; user-device installation and Android compatibility are not verified.
- Termux (GPLv3+): possible Android shell/Python environment; background execution and battery/OS limits require device testing.
- Do not deploy n8n, Huginn and Activepieces together merely because they are open source. They require a real host and resource, cost and license assessment.

## Verification plan

1. Run the new provider tests and full existing suite in GitHub Actions.
2. Inspect CI logs and record exact commit and run IDs.
3. Never place keys in source files, issue comments or chat. Owner must add secrets through the secure runtime settings.
4. Test OpenRouter with a confirmed :free model only after the owner configures the key.
5. Verify OpenAI remains blocked under the current zero-spend policy.
6. Only after these gates pass, connect model results to the task queue and workspace ledger.
7. Do not call Advait live until a real host process, authenticated identity, queue execution and restart/recovery test are observed.

## Current state

Added on this branch: bounded provider adapter, zero-spend policy template, metadata-only SQLite audit ledger, mocked unit tests and this gap register.

Not verified: CI for this branch, live API connection, provider quota, runtime deployment, browser automation, 24/7 operation, business execution or earnings.

Existing files were not intentionally edited or deleted in this change set. All changes use new paths.
