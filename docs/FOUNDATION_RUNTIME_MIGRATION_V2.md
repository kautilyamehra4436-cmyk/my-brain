# Foundation Runtime Migration V2

## Scope
This additive migration introduces managed queue use in new runtime entry points:
- ManagedSelfBuildRuntimeV2 uses ManagedTaskQueueV2.
- ATCWorkerBridgeManagedV2 uses the V2 runtime.
- ManagedATCQueueAdapterV1 stores only ATC draft plan steps via the managed queue.

## Why
Old SelfBuildRuntimeV1 and the original ATC CLI enqueue path instantiate legacy TaskQueue, whose base SQLite connection lifecycle is not deterministic. New entry points use the shared managed connection policy.

## Safety and compatibility
- Existing files and APIs are preserved.
- No automatic migration or database rewrite is performed.
- ATC queue adapter accepts only current-version DRAFT_PLAN records.
- Plan entries remain plan_only; the adapter does not execute them.
- Runtime remains manually invoked and bounded; no daemon/24x7 claim.

## Verification
Dedicated tests cover nested directory creation, managed runtime queue selection, bounded idle behavior, five plan-only queue entries, and rejection of non-draft records.

## Remaining
- Existing legacy scripts and consumers must be migrated individually.
- Inventory other SQLite users across repositories.
- Add lease/recovery semantics before concurrent or persistent workers.
- Do not enable automatic self-patching based on model output.
