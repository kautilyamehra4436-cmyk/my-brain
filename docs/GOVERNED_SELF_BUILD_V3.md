# Governed Self-Build v3

## Correctness/security fixes
1. Preflight the exact tool specification and input before writing to the append-only registry. Invalid input cannot leave an unusable registered tool.
2. Identical retries are idempotent: same name/version and same canonical spec reuses the record.
3. Same name/version with different spec hash fails closed; no overwrite is attempted.
4. Uses ManagedTaskQueueV1 to close SQLite handles deterministically.
5. Only the inherited fixed operation allowlist is executable: text.word_count, text.sha256, json.canonicalize, csv.profile.
6. Bounded manual execution: at most five tasks per run, zero-cost local operations, no network, shell, arbitrary code generation or package installation.

## Limitations
- This is not a daemon, scheduler, distributed lease/recovery system, browser, bounty executor or payment processor.
- Hash/evidence verification proves registry/result integrity, not semantic correctness of a tool's output.
- It does not dynamically sandbox arbitrary third-party repositories. Third-party code remains untrusted and is never executed.
- No production authentication or multi-user isolation is provided by this workflow.
