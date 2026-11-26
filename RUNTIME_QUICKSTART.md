# Runtime v0.1 — phone-first, ₹0

This is a small first executable slice. It uses Python's standard library only.

## What it does
- Fails closed on unknown costs, any positive estimated cost, and paid/sensitive actions.
- Stops when free quota is exhausted.
- Stores a task queue and audit trail locally using SQLite.
- No API keys, network calls, subscriptions, hosting, or payment features.

## Run tests
From the repository folder:
```sh
python -m unittest discover -v
```

## Quick example
```python
from core.zero_cost_guard import evaluate
from core.task_queue import TaskQueue

print(evaluate("research", 0))
q = TaskQueue("brain_tasks.db")
task_id = q.enqueue("Check a public README", {"url": "https://example.org"})
task = q.claim_next()
if task:
    # This queue does not execute task payloads; a human/worker must handle them.
    # Completion requires explicit evidence and an independent verifier.
    q.complete(
        task["id"],
        {"note": "handled manually"},
        evidence={"fixture": "manual-example", "acceptance": "checked"},
        verifier=lambda task_id, result, evidence: (
            task_id == task["id"] and evidence.get("acceptance") == "checked"
        ),
    )
print(q.list_tasks())
print(q.audit_events())
```

## Important limitations
- The guard is a helper; nothing else in the repo is wired through it yet.
- It is not a sandbox, malware scanner, payment-control integration, or proof of phone installation.
- The queue stores tasks but deliberately does not execute scripts or arbitrary payloads.
- Do not store credentials, private client data, or sensitive records in task payloads.
- Android Termux setup and on-device testing remain pending.
