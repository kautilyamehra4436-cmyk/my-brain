"""Read-only, bounded GitHub repository vetting for Advait.

Fetches only a fixed set of public metadata/documentation/manifest files. It never
downloads archives, installs packages, imports project code, runs build scripts,
or executes repository content. Findings are triage signals, not a security audit.
"""
from __future__ import annotations

import base64
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any

API = "https://api.github.com/repos/"
MAX_FILE_BYTES = 80_000
MAX_TOTAL_BYTES = 240_000
MAX_FILES = 9
TIMEOUT = 12
FIXED_PATHS = (
    "README.md", "README.rst", "LICENSE", "LICENSE.md", "pyproject.toml",
    "requirements.txt", "setup.cfg", "setup.py", "package.json",
    "SECURITY.md",
)
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class VettingError(RuntimeError):
    """Repository could not be inspected safely."""


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    detail: str
    evidence_file: str | None = None


class GitHubRepositoryVetterV1:
    def __init__(self, *, opener=None, timeout: int = TIMEOUT):
        self.opener = opener or urllib.request.urlopen
        self.timeout = max(2, min(int(timeout), 20))

    def _get_json(self, url: str) -> dict[str, Any] | None:
        req = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "Advait-Repository-Vetter/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        try:
            with self.opener(req, timeout=self.timeout) as response:
                raw = response.read(MAX_FILE_BYTES * 2 + 1)
            if len(raw) > MAX_FILE_BYTES * 2:
                raise VettingError("github_metadata_response_too_large")
            value = json.loads(raw.decode("utf-8"))
            return value if isinstance(value, dict) else None
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            if exc.code in (403, 429):
                raise VettingError("github_api_rate_limited") from None
            raise VettingError(f"github_http_error_{exc.code}") from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise VettingError("github_api_unavailable") from None
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise VettingError("github_metadata_invalid") from None

    @staticmethod
    def _decode_content(payload: dict[str, Any]) -> str | None:
        if payload.get("type") != "file" or payload.get("encoding") != "base64":
            return None
        encoded = payload.get("content")
        if not isinstance(encoded, str):
            return None
        try:
            raw = base64.b64decode(encoded, validate=False)
            if len(raw) > MAX_FILE_BYTES:
                return None
            return raw.decode("utf-8", "replace")
        except (ValueError, UnicodeError):
            return None

    def inspect(self, full_name: str) -> dict[str, Any]:
        if not isinstance(full_name, str) or not REPO_RE.fullmatch(full_name):
            raise ValueError("repository_must_be_owner_slash_name")
        metadata = self._get_json(API + full_name)
        if metadata is None:
            raise VettingError("repository_not_found_or_not_public")
        if metadata.get("private") is not False:
            raise VettingError("repository_is_not_public")
        if metadata.get("archived") is True:
            raise VettingError("repository_is_archived")

        files: dict[str, str] = {}
        total = 0
        for path in FIXED_PATHS[:MAX_FILES]:
            payload = self._get_json(API + full_name + "/contents/" + urllib.parse.quote(path, safe="/"))
            if payload is None:
                continue
            content = self._decode_content(payload)
            if content is None:
                continue
            total += len(content.encode("utf-8"))
            if total > MAX_TOTAL_BYTES:
                raise VettingError("repository_inspection_byte_limit_exceeded")
            files[path] = content

        findings: list[Finding] = []
        license_text = next((v for k, v in files.items() if k.upper().startswith("LICENSE")), "")
        license_name = metadata.get("license") or {}
        spdx = license_name.get("spdx_id") if isinstance(license_name, dict) else None
        if not license_text.strip() or not spdx or spdx in (None, "NOASSERTION"):
            findings.append(Finding("license_not_verified", "high",
                                    "License file or GitHub SPDX identification is missing/unclear.", "LICENSE"))
        else:
            findings.append(Finding("license_present_not_legal_review", "info",
                                    f"GitHub reports SPDX {spdx}; verify full license text, dependencies and obligations.",
                                    next((k for k in files if k.upper().startswith("LICENSE")), None)))

        readme = files.get("README.md", "") + "\n" + files.get("README.rst", "")
        manifests = "\n".join(files.get(k, "") for k in
                               ("pyproject.toml", "requirements.txt", "setup.cfg", "package.json"))
        setup_py = files.get("setup.py", "")
        all_text = readme + "\n" + manifests + "\n" + setup_py

        if re.search(r"\b(openai|anthropic|google-generativeai|google-genai)\b|OPENAI_API_KEY|API key", all_text, re.I):
            findings.append(Finding("external_api_or_key_reference", "high",
                                    "Documentation or manifests mention external AI APIs or API keys; cost, data egress and secret handling need review.",
                                    "README.md"))
        if re.search(r"auto.?save|save directly to the source|overwrite|write back to (?:the )?source", readme, re.I):
            findings.append(Finding("source_data_overwrite_feature", "high",
                                    "Project documents automatic or direct source-file saving; test on copies and require explicit user approval.",
                                    "README.md"))
        if setup_py.strip():
            findings.append(Finding("install_time_python_script", "medium",
                                    "setup.py exists; packaging/build code is executable during some install/build paths. Review before installation.",
                                    "setup.py"))
        if re.search(r"\b(subprocess|os\.system|eval\s*\(|exec\s*\(|pickle\.loads|yaml\.load)\b", setup_py, re.I):
            findings.append(Finding("dangerous_install_script_pattern", "high",
                                    "Potentially dangerous execution/deserialization pattern found in setup.py; inspect exact source before any build.",
                                    "setup.py"))
        if re.search(r"\b(pip|uv)\b.*(?:install|sync)|install_requires|dependencies\s*=", manifests, re.I):
            findings.append(Finding("dependencies_require_review", "medium",
                                    "Dependency declarations exist; resolve exact versions, transitive dependencies, hashes and supported Python versions.",
                                    "pyproject.toml"))
        if not any(k in files for k in ("pyproject.toml", "requirements.txt", "setup.cfg", "setup.py", "package.json")):
            findings.append(Finding("manifest_not_found", "medium",
                                    "No recognized dependency manifest was found in the inspected root files."))
        if not files.get("SECURITY.md", "").strip():
            findings.append(Finding("security_policy_missing", "medium",
                                    "No root SECURITY.md was found in the bounded inspection. This does not prove the project is insecure."))
        if not readme.strip():
            findings.append(Finding("readme_missing", "medium",
                                    "No root README.md or README.rst was found in the bounded inspection."))

        pushed = metadata.get("pushed_at")
        stars = metadata.get("stargazers_count")
        findings.append(Finding("metadata_is_not_quality_proof", "info",
                                f"Stars={stars!r}; pushed_at={pushed!r}. Popularity and recency do not establish security or maintenance quality."))
        findings.append(Finding("source_code_not_executed_or_audited", "high",
                                "This pass reads only a fixed set of root files. It does not audit source code, dependencies, releases, CI behavior or vulnerabilities."))

        severity_rank = {"high": 3, "medium": 2, "low": 1, "info": 0}
        findings.sort(key=lambda f: (-severity_rank[f.severity], f.code))
        risk = "high" if any(f.severity == "high" for f in findings) else (
            "medium" if any(f.severity == "medium" for f in findings) else "low")
        return {
            "schema_version": "ADV-VET-1.0",
            "repository": full_name,
            "html_url": metadata.get("html_url"),
            "default_branch": metadata.get("default_branch"),
            "license_spdx_reported_by_github": spdx,
            "pushed_at": pushed,
            "stars": stars,
            "inspected_files": list(files),
            "inspected_file_count": len(files),
            "inspected_bytes": total,
            "risk_triage": risk,
            "decision": "BLOCK_AUTO_INSTALL_AND_EXECUTION",
            "findings": [asdict(f) for f in findings],
            "installed": False,
            "executed": False,
            "source_code_audited": False,
            "owner_approval_required": True,
            "limitations": [
                "Read-only root-file triage, not a full security audit or legal opinion.",
                "No dependency resolution, vulnerability database, source-tree scan or dynamic sandbox test.",
                "A low triage score is not a safety certification.",
            ],
        }
