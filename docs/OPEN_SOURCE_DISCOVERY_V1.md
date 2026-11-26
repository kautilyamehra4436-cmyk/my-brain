# Advait Open Source Discovery v1

## Purpose
Search public GitHub repository metadata for a requested capability, filter to a conservative SPDX license allowlist, exclude private/archived/forked repositories, and rank candidates using transparent relevance, stars, and push-recency heuristics.

## Run
GitHub Actions → Advait Open Source Discovery v1 → Run workflow. Default query: `python csv data processing`; limit: 5.

## Boundaries
- Uses GitHub's public unauthenticated repository-search API; no LLM API key and no paid provider call.
- GitHub rate limits and network availability apply.
- A recognized SPDX license identifier is a discovery filter, not a legal opinion or proof that every dependency is compatible.
- Stars and push dates are weak ranking signals, not security or quality certifications.
- No repository contents, releases, dependencies, or maintainer claims are downloaded or audited.
- No candidate is installed, imported, executed, or added to the tool registry.
- Every candidate remains `needs_owner_review`; integration requires separate review of source, dependencies, license obligations, security, resource footprint, and compatibility.
- The selector only classifies supported capability vocabulary. Ambiguous or unknown requests return `needs_clarification`, not a guessed tool.
