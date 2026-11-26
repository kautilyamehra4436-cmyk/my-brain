# Managed SQLite Runtime v1

## Root cause
Python's sqlite3 connection context manager commits or rolls back transactions but does not close the connection. The existing `core/task_queue.py` uses `with self._connect() as con`, and CI has repeatedly emitted ResourceWarning for unclosed SQLite connections. Long-lived/repeated queue use can accumulate file descriptors and database handles.

## Additive mitigation
- `ManagedTaskQueueV1` subclasses the existing queue API and deterministically closes every SQLite connection in a finally block.
- `ManagedSelfBuildRuntimeV1` wires the existing bounded worker/factory to the managed queue.
- `ATCWorkerBridgeManagedV1` keeps the same ATC draft and allowlisted tool boundary but uses the managed runtime.
- Tests verify task lifecycle and absence of ResourceWarning during queue operations.

## Limits
This mitigates the queue-connection leak only for callers using the new managed classes. Existing runtimes that instantiate the original TaskQueue remain unchanged. This is not a persistent scheduler, crash recovery, multi-process lease system, or 24/7 deployment.


## Path-safety hardening — 2026-11-27

The shared manager now rejects direct database-file and immediate parent-directory symlinks, rejects arbitrary `file:` URI paths, creates missing parent directories with restrictive mode, sets database files to mode `0600`, validates timeout bounds, and still guarantees commit/rollback/close. This is path hardening, not a defense against a hostile process racing the filesystem between checks and SQLite open.
