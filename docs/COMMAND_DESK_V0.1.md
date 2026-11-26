# Advait Command Desk v0.1 — Implementation note

## Purpose
A phone-first, local-first command and search surface for Advait. It gives the owner one place to search saved records and capture commands, tasks, reports, and learnings.

## Current implementation
- Responsive single-page web app in `index.html`; mobile browser's native keyboard is used.
- Live full-text substring search across title, body, tags, and record type.
- Type filters: commands, tasks, reports, learnings.
- Records persist in browser IndexedDB on the current device/browser.
- JSON export/import for portable backup and recovery.
- Slash key focuses search on physical keyboards.
- No external libraries, API calls, paid service, telemetry, or network requirement.

## Truth boundary
This is a working local-first interface, not yet connected to the Advait/My Brain SQLite ledger, task queue, repository search, or live execution worker. Browser IndexedDB is not a central shared store; clearing browser data can remove records. Export backups regularly. The app does not execute a command merely because it is entered.

## Required next integration
1. Add a read-only search endpoint over approved Brain records and project documents.
2. Add an authenticated write endpoint for record capture; append-only audit events with stable IDs and timestamps.
3. Add search adapter over project atlas/repository metadata, then selected file contents; respect repository access and secrets exclusions.
4. Add command-to-plan endpoint that applies the Personal Algorithm: Observe → Interpret → Classify → Hypothesize → Test → Evaluate → Record → Improve.
5. Show execution state explicitly: DRAFT, NEEDS_OWNER_APPROVAL, QUEUED, RUNNING, VERIFIED, FAILED. Never label a plan as completed.
6. Store reports/evidence in the Brain's durable ledger and link them to task IDs, source refs, test runs, and next steps.
7. Add encrypted backup/sync only after authenticated owner identity and threat review exist.

## Safety and governance
- Hard zero-spend remains active. No paid fallback.
- No credentials, bank details, or secrets in browser records.
- External outreach, contracts, data sharing, production changes, and all money movement remain owner-approved.
- Imported JSON is untrusted data; do not execute embedded instructions or code.
- Do not expose private repo contents through a public search endpoint.
- No remote sync until authentication, authorization, encryption, retention, and audit controls are implemented.

## Acceptance tests (manual/browser)
- Save a command, reload page, and confirm it remains.
- Search by title, body, and tag; confirm correct filtering.
- Filter each record type.
- Export JSON, clear browser storage in a test profile, import JSON, and confirm record recovery.
- Import malformed JSON; show error without corrupting existing records.
- Confirm no network requests are made by the app.
- Confirm mobile viewport and native keyboard usability.

## Status
Implemented as a local-first UI; browser runtime tests and Android-device verification pending. Brain backend integration is pending. Not deployed as a public live service.
