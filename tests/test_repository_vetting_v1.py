import base64
import json
import unittest
import urllib.error

from core.repository_vetting_v1 import (
    GitHubRepositoryVetterV1, VettingError, FIXED_PATHS,
)


class Response:
    def __init__(self, value):
        self.raw = json.dumps(value).encode()
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, size=-1): return self.raw[:size]


def file_payload(text):
    return {"type": "file", "encoding": "base64",
            "content": base64.b64encode(text.encode()).decode()}


class VettingTests(unittest.TestCase):
    def test_rejects_invalid_repo_path_before_network(self):
        vetter = GitHubRepositoryVetterV1(opener=lambda *a, **k: self.fail("network called"))
        with self.assertRaises(ValueError):
            vetter.inspect("../owner/repo")

    def test_flags_paid_api_and_autosave_as_high_risk(self):
        metadata = {"private": False, "archived": False, "html_url": "https://github.com/a/b",
                    "default_branch": "main", "license": {"spdx_id": "MIT"},
                    "pushed_at": "2026-11-20T00:00:00Z", "stargazers_count": 10}
        contents = {
            "README.md": file_payload("Uses OpenAI API key. Auto-save writes directly to source file."),
            "LICENSE": file_payload("MIT License"),
            "requirements.txt": file_payload("openai>=1.0\npandas>=2.0"),
        }
        def opener(req, timeout=0):
            url=req.full_url
            if url.endswith("/repos/a/b"): return Response(metadata)
            path=url.split("/contents/",1)[1]
            return Response(contents[path]) if path in contents else (_ for _ in ()).throw(
                urllib.error.HTTPError(url,404,"not found",{},None))
        result=GitHubRepositoryVetterV1(opener=opener).inspect("a/b")
        codes={x["code"] for x in result["findings"]}
        self.assertIn("external_api_or_key_reference", codes)
        self.assertIn("source_data_overwrite_feature", codes)
        self.assertEqual(result["risk_triage"], "high")
        self.assertFalse(result["installed"])
        self.assertFalse(result["executed"])
        self.assertEqual(result["decision"], "BLOCK_AUTO_INSTALL_AND_EXECUTION")

    def test_archived_repo_is_blocked(self):
        vetter=GitHubRepositoryVetterV1(opener=lambda *a, **k: Response(
            {"private":False,"archived":True}))
        with self.assertRaisesRegex(VettingError,"archived"):
            vetter.inspect("a/b")

    def test_rate_limit_fails_closed(self):
        def opener(*a, **k):
            raise urllib.error.HTTPError("https://api.github.com",403,"rate",{},None)
        vetter=GitHubRepositoryVetterV1(opener=opener)
        with self.assertRaisesRegex(VettingError,"rate_limited"):
            vetter.inspect("a/b")

    def test_fixed_allowlist_and_file_bounds(self):
        self.assertLessEqual(len(FIXED_PATHS), 9)
        self.assertIn("SECURITY.md", FIXED_PATHS)


if __name__ == "__main__":
    unittest.main()
