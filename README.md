# My AI Brain — Advait v9.0

> Hard ₹0 spend • phone-first target • owner authority • evidence-led local execution

## Cost and authority

The hard-zero policy in `config.yml` is controlling. Paid APIs, hosting, subscriptions, credit, loans, paid upgrades and auto-renewals remain disabled. Exhausted or unknown free quota means stop and report; there is no paid fallback. The owner retains final authority over money, legal commitments, credentials, external messages, sensitive data sharing and security/core changes.

## Canonical runtime

- `core/atc_planner.py`: ATC v1.2 deterministic planning and reflection. It is not an LLM and does not perform live web research.
- `core/atc_worker_bridge_managed_v3.py`: canonical managed bridge from an ATC draft to an explicitly selected local tool task.
- `core/governed_self_build_runtime_v3.py`: canonical governed local runtime.
- `core/managed_task_queue_v3.py`: durable SQLite queue with leases, expiry recovery and bounded attempts. Terminal completion/failure is fenced by the active worker identity and unexpired lease.
- `core/worker.py`: bounded host-allowlisted worker with zero-cost, risk and evidence gates. No default network, browser, shell, payment or external-action handlers are shipped.
- `core/governed_self_build_factory_v1.py`: fixed local operation catalogue only: `text.word_count`, `text.sha256`, `json.canonicalize`, `csv.profile`.
- `core/managed_sqlite_v1.py`: shared SQLite connection lifecycle foundation.

The older generic `ManagedSelfBuildRuntimeV3` and V1 bridge remain for compatibility/tests; the canonical governed path is `GovernedSelfBuildRuntimeV3` through `ATCWorkerBridgeManagedV3`. The compatibility-named script `scripts/advait_atc_worker_bridge_v1.py` now exercises that managed V3 path.

## Run and test

Create an ATC draft:

```sh
python -m core.atc_planner --ledger atc.db think "My goal" --constraint "phone-only" --constraint "zero cost"
python -m core.atc_planner --ledger atc.db status
```

Run the local ATC-to-governed-worker integration smoke:

```sh
python scripts/advait_atc_worker_bridge_v1.py
```

Run tests:

```sh
python -m unittest discover -s tests -v
python -m compileall -q core tests
```

## Verified boundary — 2026-11-27

- PR #35 merged the durable leased queue into the governed runtime and routed the ATC integration smoke through the managed V3 bridge.
- GitHub Actions run [45906541842](https://github.com/kautilyamehra4436-cmyk/my-brain/actions/runs/45906541842) passed.
- My Brain PRs #33/#34 fixed SQLite connection lifecycle defects in legacy TaskQueue and ProviderCallLedger.
- Queue lease-owner fencing is tested. Lease heartbeat/renewal and full concurrent stress testing remain pending.
- The runtime is manually invoked and local-only. It is not a persistent agent, scheduler, browser, live bounty executor or payment system.

## Not implemented or not verified

No LLM reasoning runtime, live web research, production customer adapter, outbound outreach, authenticated production owner identity, independent production verifier, Android/Termux run, 24-hour operation, dashboard, payment collection or realized revenue is verified. B2B CSV reconciliation and the Advait OS Gate remain specialist modules in their source repositories and are not yet wired into this runtime.

## Blueprint-only layers

The 22-layer architecture and Self-Evolution vision remain roadmap material until each layer has a tested runtime implementation. Health score remains uncomputed; do not treat a layer list as deployed capability.

## Core boundaries

- Owner remains final authority.
- No spending, paid service, borrowing or automatic reinvestment.
- Legal, payments, account changes, data sharing and irreversible actions require owner control.
- Never claim integration, automation, earnings or 24-hour operation unless actually tested.

License: MIT.
