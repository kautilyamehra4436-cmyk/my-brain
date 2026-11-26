# Advait Sovereign AI CEO — Integration Pointer
Date: 2026-11-26

This repository remains the central Brain and ATC implementation for Advait. Do not move or duplicate its planner, task queue, memory conventions or zero-cost guard into another repository as a competing copy.

Canonical cross-project architecture and status:
- https://github.com/kautilyamehra4436-cmyk/advait-100x-research-audit/blob/main/UNIFIED_MASTER_BLUEPRINT.md
- https://github.com/kautilyamehra4436-cmyk/advait-100x-research-audit/blob/main/UNIFIED_INTEGRATION_REGISTRY.md

Current boundary:
- ATC v1.2 is a deterministic planning module. It does not provide LLM reasoning, live web research, external execution or owner authentication.
- TaskQueue stores plan-only tasks; it is not an execution worker.
- ZeroCostGuard must be wired at every future cost-bearing adapter; global enforcement is not yet proven.
- Telegram/Face ID authorization, monitoring, automation and other entries in documentation are not live unless separately installed, authenticated and tested.
- Owner remains final authority for money, legal commitments, credentials, sensitive data, external submissions and security-policy changes.

Integration rule: use versioned contracts and evidence-backed capability states. Never label candidate or planned tools as connected or deployed. Preserve the hard ₹0 policy in config.yml.
