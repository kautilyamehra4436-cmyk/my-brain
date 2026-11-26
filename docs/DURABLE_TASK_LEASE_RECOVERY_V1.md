# Durable Task Lease and Recovery V1

## Problem
A worker that crashes after claiming a task can leave it permanently in running state. The original queue had no lease expiry, attempt counter or bounded recovery rule.

## New additive queue
ManagedTaskQueueV3 adds:
- owner and expiry on every claim;
- attempt counter and per-task maximum attempts;
- atomic claim and expiry recovery under BEGIN IMMEDIATE;
- expired tasks return to pending while attempts remain;
- expired tasks become failed at the configured attempt limit;
- terminal done/failed transitions clear lease metadata;
- shared managed SQLite lifecycle for parent creation, commit/rollback and close.

Defaults: 60-second lease and 3 attempts. Callers can supply bounded overrides. This is a queue primitive, not a scheduler or proof of exactly-once execution.

## Important semantics
A lease prevents stale claims from remaining forever, but it does not guarantee exactly-once side effects. Handlers must be idempotent or use external idempotency keys. Long-running handlers need lease renewal before expiry; renewal is not implemented in v1. Concurrent multi-process stress testing remains pending.

## Verification
Tests cover lease creation, expired requeue, max-attempt terminal failure, invalid settings, and lease cleanup on successful verified completion.

## Migration
Existing V1/V2 classes remain untouched. New worker/runtime entry points should opt into V3 only after handler idempotency and lease-duration suitability are reviewed.
