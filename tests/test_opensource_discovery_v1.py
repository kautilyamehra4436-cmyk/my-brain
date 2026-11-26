import json
import unittest
from unittest.mock import patch

from core.opensource_discovery_v1 import (
    ALLOWED_LICENSES, DiscoveryError, GitHubOpenSourceDiscoveryV1,
    classify_capability,
)


def repo(name="example/tool", license_id="MIT", stars=1200, **extra):
    item = {
        "private": False, "archived": False, "fork": False,
        "full_name": name, "html_url": "https://github.com/" + name,
        "owner": {"login": name.split("/")[0]},
        "license": {"spdx_id": license_id},
        "stargazers_count": stars, "pushed_at": "2026-11-20T00:00:00Z",
        "description": "A python csv data processing utility",
        "language": "Python", "topics": ["csv", "data-processing"],
    }
    item.update(extra)
    return item


class FakeResponse:
    def __init__(self, payload):
        self.raw = json.dumps(payload).encode()
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, size=-1):
        return self.raw[:size]


class DiscoveryTests(unittest.TestCase):
    def test_capability_classification(self):
        self.assertEqual(classify_capability("find python csv data processing tools"), "csv_data")
        self.assertEqual(classify_capability("find browser automation tools"), "browser_automation")
        self.assertIsNone(classify_capability("find me something useful"))

    def test_search_filters_non_open_or_untrusted_license_candidates(self):
        payload = {"items": [
            repo("good/tool"),
            repo("bad/copyleft", "GPL-3.0"),
            repo("bad/archived", archived=True),
            repo("bad/fork", fork=True),
            repo("bad/private", private=True),
        ]}
        discovery = GitHubOpenSourceDiscoveryV1(opener=lambda *a, **k: FakeResponse(payload))
        result = discovery.search("python csv data processing", limit=5)
        self.assertEqual(result["status"], "candidates_found")
        self.assertEqual([x["full_name"] for x in result["candidates"]], ["good/tool"])
        self.assertIn(result["candidates"][0]["license_spdx"], ALLOWED_LICENSES)
        self.assertFalse(result["installed"])
        self.assertFalse(result["executed"])
        self.assertTrue(result["owner_approval_required_before_install_or_use"])

    def test_unknown_request_does_not_guess(self):
        discovery = GitHubOpenSourceDiscoveryV1(opener=lambda *a, **k: self.fail("network should not be called"))
        result = discovery.search("do something amazing")
        self.assertEqual(result["status"], "needs_clarification")
        self.assertEqual(result["candidates"], [])

    def test_rate_limit_is_reported_cleanly(self):
        import urllib.error
        def fail(*args, **kwargs):
            raise urllib.error.HTTPError("https://api.github.com", 403, "rate", {}, None)
        discovery = GitHubOpenSourceDiscoveryV1(opener=fail)
        with self.assertRaisesRegex(DiscoveryError, "rate_limited"):
            discovery.search("python csv")

    def test_invalid_query_length_is_rejected(self):
        with self.assertRaises(ValueError):
            classify_capability("x" * 161)


if __name__ == "__main__":
    unittest.main()
