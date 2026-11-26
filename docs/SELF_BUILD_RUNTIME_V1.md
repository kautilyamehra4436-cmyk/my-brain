# Advait Self-Build Runtime v1

## What is now wired
- `SelfBuildRuntimeV1` connects the existing SQLite TaskQueue, BoundedWorker, and SelfBuildToolFactory.
- A host-allowlisted handler builds a versioned declarative tool and executes it.
- The worker requires the zero-cost guard and registry/result-integrity evidence verifier.
- `run_until_idle` has a hard maximum of 20 tasks and stops when no eligible work remains.
- A manual GitHub Actions workflow runs tests, compiles the code, and executes one synthetic tool-build task.

## One-click cloud validation
Open Actions → **Advait Self-Build Worker v1** → Run workflow. Choose 1 task for the first run. The job runs in an ephemeral GitHub-hosted runner and uploads SQLite records for 7 days.

## Local invocation
```sh
python scripts/advait_self_build_worker_v1.py --db-dir ./advait-data --enqueue-sample --max-tasks 1
```

To process tasks already queued in the selected data directory, omit `--enqueue-sample`.

## Important boundary
This is a manually invoked, bounded worker cycle. GitHub Actions is not a permanent Advait host; the hosted runner stops when the job ends. No 24/7 daemon, Android/Termux installation, scheduler, browser automation, arbitrary source-code generation, customer outreach, bounty execution, payment processing, or income is activated by this change. The current tool factory creates declarative tools from a strict allowlist; it does not write and execute arbitrary new Python code.

No secrets or AI API keys are needed for this workflow. It uses only Python's standard library and local SQLite.
