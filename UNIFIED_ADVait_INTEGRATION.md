# Advait Sovereign AI CEO — Integration Pointer

**Updated:** 2026-11-27  
**Main commit:** `068a1cd2190c7665c9d25dc0c8ea3c73fb3f4b5c`

This repository remains the central Brain and ATC implementation. Do not move or duplicate its planner, task queue, worker, memory conventions or zero-cost guard into another repository as a competing copy.

Canonical cross-project architecture and current four-repository snapshot:
- https://github.com/kautilyamehra4436-cmyk/advait-100x-research-audit/blob/main/UNIFIED_MASTER_BLUEPRINT.md
- https://github.com/kautilyamehra4436-cmyk/advait-100x-research-audit/blob/main/UNIFIED_INTEGRATION_REGISTRY.md
- https://github.com/kautilyamehra4436-cmyk/advait-100x-research-audit/blob/main/CURRENT_REPOSITORY_SNAPSHOT_2026-11-27.md

## Current integration boundary

- ATC v1.2 is deterministic planning; it does not provide LLM reasoning or live web research.
- The canonical local execution path is `ATCWorkerBridgeManagedV3` → `GovernedSelfBuildRuntimeV3` → `ManagedTaskQueueV3` → `BoundedWorker` → fixed local operation allowlist.
- The managed queue applies leases and stale-worker fencing to terminal completion/failure. Lease heartbeat and multi-process stress tests remain pending.
- Queue plan-only entries remain drafts; only explicitly selected bounded-adapter tasks can reach the worker.
- The runtime does not ship browser, network, shell, payment, payout, withdrawal, outbound messaging or production customer adapters.
- B2B CSV reconciliation and Advait OS Gate remain separate specialist modules; neither is integrated into the Brain runtime yet.
- Global zero-cost enforcement across every future adapter is not yet proven.
- Telegram/Face ID authorization, monitoring, automation and other registry entries are not live unless separately installed, authenticated and tested.
- Owner remains final authority for money, legal commitments, credentials, sensitive data, external submissions and security-policy changes.

## Integration rule

Use versioned contracts and evidence-backed capability states. Never label candidate or planned tools as connected or deployed. Preserve the hard ₹0 policy in `config.yml`.
