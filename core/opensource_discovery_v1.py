"""Public GitHub discovery and conservative tool-candidate ranking for Advait.

Discovery uses GitHub's unauthenticated public repository-search endpoint. It does
not install, download, import, execute, or grant trust to discovered repositories.
Candidates remain review-only until a separate owner-approved integration exists.
"""
from __future__ import annotations

import json
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any

GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"
ALLOWED_LICENSES = {
    "MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "MPL-2.0",
}
MAX_RESULTS = 10
MAX_QUERY_LENGTH = 160
MAX_RESPONSE_BYTES = 1_000_000
TIMEOUT_SECONDS = 12

# Conservative capability vocabulary. Unknown requests do not receive a guessed match.
CAPABILITY_RULES: dict[str, tuple[str, ...]] = {
    "csv_data": ("csv", "tabular", "dataframe", "spreadsheet", "delimited"),
    "json_data": ("json", "schema", "serialization", "yaml"),
    "text_processing": ("text", "string", "document", "tokeniz", "natural language"),
    "browser_automation": ("browser", "playwright", "selenium", "web automation"),
    "pdf_documents": ("pdf", "document parsing", "pypdf", "pdfplumber"),
    "image_processing": ("image", "pillow", "opencv", "computer vision"),
    "testing": ("test", "pytest", "unittest", "testing framework"),
}


class DiscoveryError(RuntimeError):
    """Public discovery failed or returned an invalid response."""


@dataclass(frozen=True)
class ToolCandidate:
    full_name: str
    owner: str
    description: str
    url: str
    license_spdx: str
    stars: int
    pushed_at: str
    language: str
    topics: tuple[str, ...]
    capability: str
    score: int
    status: str = "needs_owner_review"
    installed: bool = False
    executed: bool = False


def classify_capability(request: str) -> str | None:
    if not isinstance(request, str) or not request.strip() or len(request) > MAX_QUERY_LENGTH:
        raise ValueError("request_must_be_1_to_160_characters")
    text = request.casefold()
    matches = []
    for capability, terms in CAPABILITY_RULES.items():
        hits = sum(1 for term in terms if term in text)
        if hits:
            matches.append((hits, capability))
    if not matches:
        return None
    matches.sort(key=lambda item: (-item[0], item[1]))
    # Refuse ambiguous top matches instead of silently selecting a category.
    if len(matches) > 1 and matches[0][0] == matches[1][0]:
        return None
    return matches[0][1]


def _score(stars: int, pushed_at: str, topics: list[str], description: str,
           capability: str) -> int:
    text = " ".join(topics) + " " + description
    terms = CAPABILITY_RULES[capability]
    relevance = min(40, sum(8 for term in terms if term in text.casefold()))
    popularity = min(25, int(math.log10(max(1, stars)) * 5))
    freshness = 0
    try:
        # Date is used as a coarse recency signal, not proof of maintenance quality.
        from datetime import date
        age_days = max(0, (date.today() - date.fromisoformat(pushed_at[:10])).days)
        freshness = max(0, 20 - age_days // 90)
    except (TypeError, ValueError):
        freshness = 0
    return min(85, relevance + popularity + freshness)


def _normalize_repo(item: dict[str, Any], capability: str) -> ToolCandidate | None:
    if not isinstance(item, dict):
        return None
    if item.get("private") is not False or item.get("archived") is True or item.get("fork") is True:
        return None
    full_name = item.get("full_name")
    html_url = item.get("html_url")
    owner = item.get("owner") or {}
    license_info = item.get("license") or {}
    spdx = license_info.get("spdx_id") if isinstance(license_info, dict) else None
    if not isinstance(full_name, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", full_name):
        return None
    if not isinstance(owner, dict) or not isinstance(owner.get("login"), str):
        return None
    if not isinstance(html_url, str) or not html_url.startswith("https://github.com/"):
        return None
    if spdx not in ALLOWED_LICENSES:
        return None
    stars = item.get("stargazers_count")
    if not isinstance(stars, int) or stars < 0:
        return None
    pushed = item.get("pushed_at") or ""
    if not isinstance(pushed, str):
        pushed = ""
    description = item.get("description") or ""
    if not isinstance(description, str):
        description = ""
    language = item.get("language") or ""
    if not isinstance(language, str):
        language = ""
    topics = item.get("topics") or []
    if not isinstance(topics, list) or not all(isinstance(x, str) for x in topics):
        topics = []
    score = _score(stars, pushed, topics, description, capability)
    return ToolCandidate(
        full_name=full_name, owner=owner["login"], description=description[:500],
        url=html_url, license_spdx=spdx, stars=stars, pushed_at=pushed,
        language=language, topics=tuple(topics[:20]), capability=capability, score=score,
    )


class GitHubOpenSourceDiscoveryV1:
    """Bounded public repository search; never fetches source archives or executes code."""

    def __init__(self, *, opener=None, timeout: int = TIMEOUT_SECONDS):
        self.opener = opener or urllib.request.urlopen
        self.timeout = max(2, min(int(timeout), 20))

    def search(self, request: str, *, limit: int = 5) -> dict[str, Any]:
        capability = classify_capability(request)
        if capability is None:
            return {
                "status": "needs_clarification",
                "reason": "request_category_unknown_or_ambiguous",
                "query": request[:MAX_QUERY_LENGTH] if isinstance(request, str) else "",
                "candidates": [],
                "installed": False,
                "executed": False,
            }
        limit = max(1, min(int(limit), MAX_RESULTS))
        query = f"{request} in:name,description,topics"
        params = urllib.parse.urlencode({
            "q": query, "sort": "stars", "order": "desc", "per_page": limit,
        })
        url = GITHUB_SEARCH_URL + "?" + params
        req = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "Advait-v32-OpenSourceDiscovery/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        try:
            with self.opener(req, timeout=self.timeout) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise DiscoveryError("github_response_too_large")
            payload = json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 403 or exc.code == 429:
                raise DiscoveryError("github_search_rate_limited") from None
            raise DiscoveryError(f"github_http_error_{exc.code}") from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise DiscoveryError("github_search_unavailable") from None
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise DiscoveryError("github_response_invalid_json") from None
        if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
            raise DiscoveryError("github_response_schema_invalid")
        candidates = []
        seen = set()
        for item in payload["items"]:
            candidate = _normalize_repo(item, capability)
            if candidate and candidate.full_name.casefold() not in seen:
                seen.add(candidate.full_name.casefold())
                candidates.append(candidate)
        candidates.sort(key=lambda c: (-c.score, -c.stars, c.full_name.casefold()))
        return {
            "status": "candidates_found" if candidates else "no_verified_license_candidates",
            "capability": capability,
            "query": query,
            "searched_at_epoch": int(time.time()),
            "source": "GitHub public repository search API",
            "license_filter": sorted(ALLOWED_LICENSES),
            "candidates": [asdict(c) for c in candidates[:limit]],
            "installed": False,
            "executed": False,
            "owner_approval_required_before_install_or_use": True,
        }
