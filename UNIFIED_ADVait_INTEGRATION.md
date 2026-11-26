# Advait Sovereign AI CEO — Integration Pointer

**Updated:** 2026-11-27  
**Main commit:** `497b41780ad2634ca6498460e96fe3eb739c83d6`

This repository remains the central Brain and ATC implementation. Do not move or duplicate its planner, task queue, worker, memory conventions or zero-cost guard into another repository as a competing copy.

Canonical cross-project architecture and current four-repository snapshot:
- https://github.com/kautilyamehra4436-cmyk/advait-100x-research-audit/blob/main/UNIFIED_MASTER_BLUEPRINT.md
- https://github.com/kautilyamehra4436-cmyk/advait-100x-research-audit/blob/main/UNIFIED_INTEGRATION_REGISTRY.md
- https://github.com/kautilyamehra4436-cmyk/advait-100x-research-audit/blob/main/CURRENT_REPOSITORY_SNAPSHOT_2026-11-27.md

## Current integration boundary

- ATC v1.2 is deterministic planning; it does not provide LLM reasoning or live web research.
- Canonical local path: `ATCWorkerBridgeManagedV3` → `GovernedSelfBuildRuntimeV3` → `ManagedTaskQueueV3` → `BoundedWorker` → fixed local allowlist.
- The 100X B2B reconciler is pinned as `vendor/advait_b2b`; no source copy or runtime network fetch is used.
- B2B CSV tasks store only opaque artifact IDs in operational SQLite. Source and output files stay in a separate permission-restricted financial store.
- The financial store is **not encrypted at rest**; explicit acknowledgement is required. No real customer data has been processed. Do not stage sensitive data until encryption/Android Keystore and authenticated owner identity exist.
- B2B is CSV-only, bounded to 1 MiB input / 10,000 rows / 100 columns / 4 MiB output. It is local analysis, not accounting/tax advice or automatic approval.
- Managed queue terminal updates are fenced by worker identity and lease expiry; heartbeat and multi-process stress tests remain pending.
- The runtime does not ship browser, network, shell, payment, payout, withdrawal, outbound messaging or production customer adapters.
- Advait OS Gate remains separate and is not yet wired into the worker.
- Global zero-cost enforcement across every future adapter is not yet proven.
- Owner remains final authority for money, legal commitments, credentials, sensitive data, external submissions and security-policy changes.

## Integration rule

Use pinned versioned source, reviewed contracts and evidence-backed capability states. Never label candidate or planned tools as connected or deployed. Preserve the hard ₹0 policy in `config.yml`.
