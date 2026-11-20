# Zero-Cost Integration Register

**Hard policy: ₹0 spend.** This register separates confirmed connections from open-source candidates and planned work. A candidate is not connected merely because it is listed here.

## Confirmed
- **GitHub repository access:** verified for this repo; can read/write repository files. This is the only external connection currently verified here.

## Open-source candidates
| Tool | Use | Status | Caveat |
|---|---|---|---|
| Termux | Android phone local runtime | Not installed/verified | Requires user-side installation; Android background limits apply |
| Python | lightweight scripts | Candidate | Runtime not yet tested on user's phone |
| SQLite | local task/ledger/audit database | Candidate | Not yet implemented in this repo |
| Git | version history/rollback | Candidate | Local installation not verified |
| n8n | workflow automation | Not deployed | Self-hosting only; no paid cloud |
| Huginn | event monitoring/automation | Not deployed | Self-hosting needs runtime/hosting; phone practicality to test |
| Activepieces | workflow automation alternative | Not deployed | Community/self-host route only; compare licensing/resource needs first |
| Ollama | local LLM runtime | Not suitable by default for phone-only | Only consider after device capability test; not required |

## Integration order (phone-first)
1. **GitHub + repository-based source of truth** (already connected): keep changes versioned.
2. **Termux + Python + SQLite**: only if user installs; build a small local runtime, offline-first.
3. **Free GitHub Actions**: test/schedule only within the free quota. No billing/paid usage; pause if quota is exhausted.
4. **Automation tool comparison**: n8n vs Huginn vs Activepieces. Do not deploy all three; choose one only after a resource/cost feasibility test.
5. **External accounts/APIs**: defer; any account or credential connection requires explicit owner action and must have a genuinely free option.

## Non-negotiable safeguards
- ₹0 total spend: paid APIs, hosting, subscription, credit, purchases, auto-renewal are prohibited.
- Never store secrets in repository files or chat; use local secret storage if a runtime is implemented.
- No payment, transfers, paid upgrades, signing, account creation, or irreversible actions.
- Status labels: **verified-connected**, **installed-verified**, **runtime-tested**, **candidate**, **planned**, **blocked**. Do not overstate status.
- If a free limit is reached, pause and report instead of switching to paid.

## Current limitation
This repository is currently documentation/configuration-first; no executable integration adapters or orchestrator are verified. This register is the first integration map, not proof that the listed open-source software is running.
