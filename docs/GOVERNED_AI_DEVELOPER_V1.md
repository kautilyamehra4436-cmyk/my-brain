# Advait Governed AI Developer v1

## Purpose
This is the first model-backed AI Developer capability for Advait v32.0. It uses one bounded OpenRouter request to inspect a fixed allowlist of public source files and produce evidence-linked engineering findings.

## Capabilities
- Read four explicitly allowlisted source files.
- Exclude files exceeding byte limits, failing UTF-8 decoding, or matching conservative secret-like patterns.
- Send bounded source excerpts to an explicitly selected OpenRouter model ending in :free.
- Require JSON output with exact file paths, line ranges and verbatim source evidence.
- Reject findings whose path, line range or evidence cannot be validated locally.
- Mark every suggestion REVIEW_REQUIRED and auto_patch=false.
- Store provider-call metadata without prompts, responses or credentials. The provider ledger uses deterministic SQLite connection closure.

## Hard limits
- No repository writes, patches, shell execution, package installation, arbitrary paths, browser, customer contact, bids, contracts, or money movement.
- Cannot change owner policy, security gates, workflow permissions or release authority.
- Model findings are hypotheses, not confirmed defects; they require independent review and reproduction.
- Manual GitHub Actions dispatch only; not a daemon or 24/7 service.
- Free model may be unavailable or rate-limited. No paid fallback.

## Run
1. Confirm repository secret OPENROUTER_API_KEY is configured in GitHub Actions settings. Never put its value in source, chat, workflow inputs or logs.
2. Open Actions, select Advait Governed AI Developer v1, then Run workflow.
3. Keep the model ID ending in :free. Default: nvidia/nemotron-3.5-lightning:free.
4. Download artifact advait-ai-developer-v1-report.
5. Independently verify every finding before creating a repair task.

## Security
- contents: read only.
- Manual dispatch only; no push, pull-request or schedule trigger.
- Fixed file allowlist and strict size caps.
- Conservative secret-pattern exclusion before source leaves the runner.
- Model output treated as untrusted and validated against schema and exact source evidence.
- No automatic patching or deployment.
- No paid provider fallback; zero-spend policy remains.

## Verification boundary
Unit tests cover report schema, allowlisted paths, verbatim evidence and managed SQLite lifecycle. They do not prove OpenRouter credentials, provider availability, model quality or a successful live model run. Only a successful manual workflow run with an uploaded report proves that specific live run completed.
