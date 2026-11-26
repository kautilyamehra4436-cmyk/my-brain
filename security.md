# Zero-Trust Security — Verification Register
Status: threat model and proposed controls. A listed control is not verified merely because an older draft marked it complete.

## Threat model
- Spoofing: require authenticated identity and exact-action approval.
- Tampering: integrity-protected logs plus independently anchored evidence where appropriate.
- Repudiation: timestamped audit events and owner approval records.
- Information disclosure: least privilege, secret isolation, data minimization and retention controls.
- Denial of service: bounded work, timeouts, rate limits and safe pause.
- Elevation of privilege: deny by default; planner and workers cannot alter policy or gates.

## Control status
| Control | Current status |
|---|---|
| Fail-closed Advait OS Gate v0.2 | Implemented in separate repository; production verifier absent |
| ATC plan-only separation | Implemented in My Brain |
| Zero-cost helper | Implemented; global adapter wiring unverified |
| 2FA / branch protection / Dependabot / SHA pinning / OIDC | Not independently verified here |
| Central monitoring / 10k daily rate limit | Not verified |
| Secret scanning and incident response | Requires live settings and workflow audit |

Never store credentials in source files, chat, ordinary logs or unencrypted operational SQLite. Every external adapter needs least privilege, idempotency, rate limits, bounded retries, safe logging and reconciliation.
