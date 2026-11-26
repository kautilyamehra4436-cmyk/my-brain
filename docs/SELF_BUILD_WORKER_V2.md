# Advait Self-Build Worker v2

## Fix
The v1 file-based CLI invocation exposed a Python import-path issue: Python placed the `scripts/` directory on `sys.path`, so the repository-root `core` package was not importable. V2 explicitly inserts the repository root derived from `__file__` before importing the runtime.

## Run
GitHub Actions → Advait Self-Build Worker v2 → Run workflow → branch `main` → `max_tasks=1`.

## Scope and safety
This remains a manually triggered, bounded, zero-cost worker cycle. It runs the standard-library declarative tool factory and synthetic word-count task. It is not a persistent 24/7 runtime, arbitrary Python code generator, phone installation, browser agent, bounty worker, or payment executor.
