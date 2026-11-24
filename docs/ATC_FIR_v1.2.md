# FIR — First Integration Record: ATC v1.2

**Date:** 2026-11-24
**Project:** My Brain / Advait Autonomous Thinking Core
**Repository branch:** `atc-integration-20261124`
**Status:** Implemented in branch; local tests pending verification; not production-ready.

## Change
ATC is placed as a planning layer in `my-brain/core/atc_planner.py`, using the existing `zero_cost_guard` and optionally storing draft steps in `TaskQueue`. It does not create a second task queue or executor.

## Safety
- Positive/unknown cost and exhausted free quota fail closed.
- Plan steps are `plan_only` and are never executed by this module.
- Sensitive keyword flags require owner review; detection is heuristic and can miss or over-flag.
- The module has no owner authentication, network, shell, model, or external-action adapter.
- SQLite event chain detects tampering if hashes are not recomputed; it is not a tamper-proof log.

## Tests
Test suite intended to cover input validation, five strategy templates, ten reflection questions, heuristics, risk flags, fail-closed cost/quota, plan-only status, ledger round-trip/tamper detection, queue integration, bounded input, and no-live-research disclosure.

## Not verified
Phone/Termux, long-duration/24-hour run, Android resource use, real research, LLM reasoning, real customer tasks, external execution, earnings, secure owner approval, production reliability.

## Reconciliation
The integration map documents where each existing engine fits and the conflicts found in the current My Brain files. No existing policy is silently changed.
