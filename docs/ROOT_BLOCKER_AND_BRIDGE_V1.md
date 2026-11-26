# Advait Core Integration Check v1 — Root Blocker Fix

## Root cause established from source
- ATC v1.2 creates heuristic `DRAFT_PLAN` records; every plan step is `plan_only`. Its queue method stores plan-only records, not executable worker tasks.
- BoundedWorker only claims `execution_mode=bounded_adapter` tasks and only dispatches host-registered handlers.
- ProviderRouterV1 is a standalone single-call adapter; it is not registered as a worker handler and does not create tasks or dispatch tools.
- SelfBuildRuntimeV1 registers only the self-build local-tool handler and is a manually invoked bounded runner.
- GitHub Actions workflows are manually dispatched ephemeral jobs, not an always-on host.

## Additive bridge
`ATCWorkerBridgeV1` explicitly links ATC draft planning to the existing bounded local-tool worker. It does not automatically execute generic plan steps. A caller must explicitly select a tool specification; the tool must pass the fixed operation allowlist. Plans with detected risk flags are blocked for owner review. The bridge runs only local analysis at zero estimated cost.

## One-click end-to-end proof
GitHub Actions → **Advait Core Integration Check v1** → Run workflow.
This executes the complete test suite and then a real synthetic ATC-plan → queue → allowlisted local tool → evidence-verified completion path. No API key, model API, paid service, network call, customer data, external contact or payment is used.

## Limits remaining
This proves only the bounded local integration path. It does not add LLM reasoning, live open-source discovery, browser automation, arbitrary code generation, authenticated owner identity, scheduler, crash recovery, Android/Termux runtime, 24/7 operation, bounty execution or payment collection. Those require separate adapters, host and security gates.
