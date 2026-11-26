# Health Score — Measurement Specification
Status: not computed. Do not report a numerical health score until raw metrics and collection intervals exist.

Proposed dimensions:
- Availability and recovery: measured runtime uptime, crash/restart recovery.
- Task quality: independently verified accepted outputs / completed test cases.
- Compliance and privacy: evidence-backed checklist results and incidents.
- Security: current vulnerability findings, gate tests and permission audit.
- Cost: actual spend and quota consumption.
- Owner satisfaction: explicit feedback.
- Learning: tested improvements that outperform a baseline without regressions.

Do not substitute GitHub CI success for phone uptime, production reliability or customer success. UptimeRobot, Android monitoring and continuous reporting are candidates until configured and verified. If any dimension is unknown, label it UNKNOWN rather than inventing a score.
