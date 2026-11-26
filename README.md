# My AI Brain — Advait v9.0

> Hard ₹0 spend • owner authority • evidence-led local execution • phone-first target

## Cost and authority

The hard-zero policy in \`config.yml\` is controlling. Paid APIs, hosting, subscriptions, credit, loans, paid upgrades and auto-renewals remain disabled. Exhausted or unknown free quota means stop and report; there is no paid fallback. The owner retains final authority over money, legal commitments, credentials, external messages, sensitive data sharing and security/core changes.

## Canonical runtime

- \`core/atc_planner.py\`: ATC v1.2 deterministic planning and reflection. It is not an LLM and does not perform live web research.
- \`core/atc_worker_bridge_managed_v3.py\`: canonical managed bridge from an ATC draft to explicitly selected local tool tasks.
- \`core/governed_self_build_runtime_v3.py\`: canonical governed local runtime.
- \`core/managed_task_queue_v3.py\`: durable SQLite queue with leases, expiry recovery and bounded attempts. Terminal completion/failure is fenced by active worker identity and unexpired lease.
- \`core/worker.py\`: bounded host-allowlisted worker with zero-cost, risk and evidence gates. No default network, browser, shell, payment or external-action handlers.
- \`core/governed_self_build_factory_v1.py\`: fixed local operations: \`text.word_count\`, \`text.sha256\`, \`json.canonicalize\`, \`csv.profile\`.
- \`core/b2b_reconciliation_adapter_v1.py\`: CSV-only local reconciliation adapter that uses the pinned 100X submodule \`vendor/advait_b2b\`.
- \`core/financial_record_vault_v1.py\`: separate file storage for financial CSV inputs and reports; source rows do not enter task-queue payloads/results.
- \`core/managed_sqlite_v1.py\`: shared SQLite connection lifecycle foundation.

The canonical B2B source is pinned at submodule commit \`e6b52df9f7e9a2e8690217ace813e2e29b65b244\`; it is not copied into this repository. Clone with \`git clone --recurse-submodules\` or initialize using \`git submodule update --init\`.

## B2B CSV boundary

The adapter stages source bytes only after explicit local owner-consent and explicit acknowledgement that the vault is **not encrypted at rest**. The queue stores only an opaque artifact ID and metadata; normalized CSV, exceptions CSV and summary stay in the separate vault. The worker recomputes the report and verifies output artifacts before completion.

- CSV only; max 1 MiB input, 10,000 rows, 100 columns, 4 MiB output.
- Synthetic CI sample: 5 rows, 7 review flags; source rows were not persisted in the operational task queue.
- No real customer data has been processed.
- The vault uses restrictive OS permissions and symlink checks, but is not encrypted. Do not stage sensitive customer records on a shared/untrusted device until encryption/Android Keystore is implemented.
- Consent/confirmation booleans are manual intent checks, not authenticated owner identity.
- The output is a review aid, not an accounting/tax conclusion or automatic approval.

## Run and test

Create an ATC draft:

\`\`\`sh
python -m core.atc_planner --ledger atc.db think "My goal" --constraint "phone-only" --constraint "zero cost"
python -m core.atc_planner --ledger atc.db status
\`\`\`

Run local ATC and B2B integration checks:

\`\`\`sh
python scripts/advait_atc_worker_bridge_v1.py
python scripts/advait_b2b_integration_smoke_v1.py
\`\`\`

Run tests:

\`\`\`sh
python -m unittest discover -v
python -m compileall -q core tests scripts
\`\`\`

## Verified boundary — 2026-11-27

- My Brain PR #35 merged durable lease integration; PR #37 merged B2B CSV adapter integration.
- B2B workflow [45908960326](https://github.com/kautilyamehra4436-cmyk/my-brain/actions/runs/45908960326) passed 131 unit tests, compilation and end-to-end synthetic smoke (5 rows / 7 flags).
- My Brain CI verifies the pinned submodule revision and keeps source rows outside operational queue data.
- My Brain PRs #33/#34 fixed legacy TaskQueue and ProviderCallLedger SQLite connection lifecycle.
- Lease heartbeat/renewal and full multi-process stress testing remain pending.
- The runtime is manually invoked and local-only. It is not a persistent agent, scheduler, browser, live bounty executor or payment system.

## Not implemented or not verified

No LLM reasoning runtime, live web research, production customer delivery, outbound outreach, authenticated production owner identity, independent production verifier, encrypted financial vault, Android/Termux run, 24-hour operation, dashboard, payment collection or realized revenue is verified. Advait OS Gate remains a separate specialist module and is not yet wired into this runtime.

## Blueprint-only layers

The 22-layer architecture and Self-Evolution vision remain roadmap material until each layer has a tested runtime implementation. Health score remains uncomputed; do not treat a layer list as deployed capability.

## Core boundaries

- Owner remains final authority.
- No spending, paid service, borrowing or automatic reinvestment.
- Legal, payments, account changes, external messages and sensitive data sharing require owner control.
- Never claim integration, automation, earnings or 24-hour operation unless actually tested.

License: MIT.
