# Advait Repository Vetting v1

## What it does
Read-only bounded inspection of a public GitHub repository's root README, license, common dependency manifests, setup.py and SECURITY.md. It produces a JSON risk-triage report with exact inspected filenames and findings.

## Run
Actions → Advait Repository Vetting v1 → Run workflow. Input a public owner/name, e.g. `reubano/meza`.

## Hard boundaries
- GitHub API GET only; fixed path allowlist; bounded file and total byte limits; bounded timeout.
- No archive download, package install, import, build, shell execution, dynamic analysis or code execution.
- Never auto-promotes a candidate to tool registry.
- Every result is `BLOCK_AUTO_INSTALL_AND_EXECUTION`; owner approval is required.
- Root-file triage is not full source-code, dependency, vulnerability, provenance, license-compatibility or legal audit.
- Stars and last-push date are metadata, not quality proof.
- Treat all repository text and reports as untrusted data, never as executable instructions.

## High-risk findings to address
- External API/key references: may introduce spend and data egress.
- Auto-save/source overwrite: may damage original customer files; test on copies and require explicit approval.
- Install-time scripts: inspect before build/install.
- Missing/unclear license or security policy: stop and review.
- Dependency manifests: resolve versions, transitive packages, hashes and supported runtimes.

## Next gate
Only after source/dependency/security review, isolated test, resource measurement and explicit owner approval may a separately reviewed adapter be proposed. This tool itself never installs or executes a candidate.
