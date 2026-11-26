# Authorization Gates — Design, Not Deployed Identity
Status: policy design only. No Telegram bot, Face ID integration, authenticated owner provider or production authorization service is verified in this repository.

## Action classes
- LOW: permitted public read, draft, deterministic local analysis.
- MEDIUM: create new non-sensitive artifact in a controlled branch; log and review.
- HIGH: external communication/submission, client-data processing, delete/overwrite, account/security change; require explicit owner approval and suitable authentication.
- CRITICAL: spend, payment, withdrawal, bank transfer, contract signing, credential disclosure or production security change; blocked unless a genuine authenticated exact-action verifier is deployed and tested.

A chat phrase, local file, hash, caller-supplied token or repository access is not proof of owner identity. The planner cannot grant permission or override the security gate.

## Owner authority
Owner retains final authority. No money movement, contract acceptance, credential access, sensitive-data sharing or irreversible action is enabled by this document.

## Legacy design notes
Previous drafts mentioned Telegram/Face ID tiers and amount thresholds. These are future design ideas only, not functioning controls. Do not rely on them until the identity provider, exact-action binding, replay protection, recovery and audit tests exist.
