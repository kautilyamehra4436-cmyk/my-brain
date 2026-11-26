import json, sqlite3, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from core.provider_router_v1 import ProviderCallLedger, ProviderPolicyError, ProviderRouterV1

class FakeResponse:
    status=200
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self,size=-1):
        return json.dumps({"choices":[{"message":{"content":"fixture answer"}}],
                           "usage":{"prompt_tokens":4,"completion_tokens":2,"cost":0.0}}).encode()

class ProviderRouterTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.ledger=ProviderCallLedger(str(Path(self.tmp.name)/"provider.db"))
        self.router=ProviderRouterV1(ledger=self.ledger,environ={"OPENROUTER_API_KEY":"secret-fixture"})
    def tearDown(self): self.tmp.cleanup()
    def test_openai_blocked_by_zero_spend(self):
        with self.assertRaisesRegex(ProviderPolicyError,"openai_api_disabled"):
            self.router.call(provider="openai",model="gpt-model",messages=[{"role":"user","content":"hi"}])
        self.assertEqual(self.ledger.events(),[])
    def test_openrouter_paid_model_blocked(self):
        with self.assertRaisesRegex(ProviderPolicyError,"paid_model_blocked"):
            self.router.call(provider="openrouter",model="vendor/model",messages=[{"role":"user","content":"hi"}])
    def test_missing_key_fails_before_network(self):
        router=ProviderRouterV1(ledger=self.ledger,environ={})
        with self.assertRaisesRegex(ProviderPolicyError,"key_missing"):
            router.call(provider="openrouter",model="vendor/model:free",messages=[{"role":"user","content":"hi"}])
    @patch("core.provider_router_v1.urllib.request.urlopen",return_value=FakeResponse())
    def test_success_is_audited_without_secret_or_prompt(self,mock):
        result=self.router.call(provider="openrouter",model="vendor/model:free",
            messages=[{"role":"user","content":"private prompt fixture"}])
        self.assertEqual(result.text,"fixture answer")
        events=self.ledger.events()
        self.assertEqual(len(events),1)
        serialized=json.dumps(events)
        self.assertNotIn("private prompt fixture",serialized)
        self.assertNotIn("secret-fixture",serialized)
        self.assertEqual(events[0]["cost_usd"],0.0)
    def test_audit_is_append_only(self):
        self.ledger.append(request_id="fixture",provider="openrouter",model="x:free",
            request_sha256="a",response_sha256="b",status="success",http_status=200,latency_ms=1)
        with sqlite3.connect(self.ledger.db_path) as con:
            with self.assertRaises(sqlite3.IntegrityError): con.execute("UPDATE provider_calls SET status='x'")
            with self.assertRaises(sqlite3.IntegrityError): con.execute("DELETE FROM provider_calls")
    def test_message_extra_fields_rejected(self):
        with self.assertRaises(ValueError):
            self.router.call(provider="openrouter",model="x:free",
                messages=[{"role":"user","content":"hi","secret":"no"}])

if __name__=="__main__": unittest.main()
