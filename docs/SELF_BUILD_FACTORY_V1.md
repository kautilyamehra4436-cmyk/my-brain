# Advait Self-Build Tool Factory v1

## Status
Additive implementation proposal for Advait v32.0. This is a bounded local capability, not a general-purpose autonomous coding agent or 24/7 service.

## What v1 does
- Builds versioned tool entries from a strict declarative specification.
- Supports four built-in operations: text word count, text SHA-256, JSON canonicalization, and CSV profiling.
- Stores tool specifications and hashes in a local SQLite registry.
- Uses append-only update/delete triggers for ordinary SQL operations.
- Exposes one explicit BoundedWorker adapter: `selfbuild.create_execute`.
- Supplies an evidence verifier that checks registered tool identity and result integrity hashes.

## What v1 deliberately does not do
- It does not generate or execute arbitrary Python/JavaScript.
- It does not use eval, exec, shell commands, dynamic imports, browser automation, or network access.
- It does not install packages or modify existing Core files.
- It does not claim semantic correctness merely because a result hash matches.
- It does not provide authentication, a sandbox against a hostile host administrator, a scheduler, or a persistent daemon.

## Worker task contract
Enqueue a task with:
- `execution_mode: bounded_adapter`
- `adapter: selfbuild.create_execute`
- `action: local_analysis`
- `estimated_cost: 0`
- `free_quota_available: true`
- `risk: low`
- `input: { spec: {name, version, operation, description}, input: {...} }`

The host must instantiate `SelfBuildToolFactory`, register `factory.worker_handlers()` in the existing BoundedWorker allowlist, and inject `factory.worker_evidence_verifier()`. The factory does not start the worker itself.

## Security and owner controls
The operation catalogue is a hard allowlist. Unknown operations, extra spec fields, malformed inputs, oversized text, duplicate versions, and unregistered tools fail closed. New versions are additive; prior versions remain. Any future arbitrary-code builder requires a separate isolated execution design, resource limits, filesystem/network policy, dependency review, and owner approval before production use.

## Local tests
Run: `python -m unittest tests.test_self_build_factory_v1 -v`
Full suite: `python -m unittest discover -v`
