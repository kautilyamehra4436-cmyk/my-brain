# FIR — First Integration Record: ATC v1.2

**Date:** 2026-11-24
**Project:** My Brain / Advait Autonomous Thinking Core
**Repository branch:** atc-integration-20261124 → merged to main by PR #1
**Status:** ATC v1.2 planner and reviewed-only handoff implemented; latest GitHub Actions run #72 passed 38 tests and compile checks; not production-ready.

## Change
ATC is placed as a planning layer in `my-brain/core/atc_planner.py`, using the existing `zero_cost_guard` and optionally storing draft steps in `TaskQueue`. It does not create a second task queue or executor.

## Safety
- Positive/unknown cost and exhausted free quota fail closed.
- Plan steps are `plan_only` and are never executed by this module.
- Sensitive keyword flags require owner review; detection is heuristic and can miss or over-flag.
- The module has no owner authentication, network, shell, model, or external-action adapter.
- SQLite event chain detects tampering if hashes are not recomputed; it is not a tamper-proof log.

## Local tests
- ATC planner tests: 26/26 PASS.
- Existing My Brain runtime tests: 7/7 PASS.
- Combined: 38/38 PASS in GitHub Actions run #67 (26 ATC planner + 7 existing runtime + 5 handoff tests), including compile checks.
- One strategy-selection test initially failed; heuristic weights were adjusted and the regression passed. A false-positive risk keyword test was added and passed.
- Hash-chain and stored-record tampering tests pass.

## Not verified
Phone/Termux, long-duration/24-hour run, Android resource use, real research, LLM reasoning, real customer tasks, external execution, earnings, secure owner approval, and production reliability remain unverified. Gate and bounded-engine security repairs are tracked in their respective repositories.

## Reconciliation
The integration map and repository reconciliation report document placement, conflicts and security findings across the reviewed engines. No existing policy is silently changed.
