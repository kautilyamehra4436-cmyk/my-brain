"""Additive, bounded provider adapter for Advait v32.0.
Secrets are read from environment only. Prompt/response content is never persisted.
Default policy is USD 0: OpenAI paid API is blocked; OpenRouter :free only.
This is a call adapter, not a daemon, scheduler, browser, or task executor.
"""
from __future__ import annotations
import hashlib, json, os, sqlite3, time, urllib.error, urllib.request, uuid
from dataclasses import dataclass
from typing import Any

DEFAULT_POLICY = {
    "max_cost_usd_per_call": 0.0, "max_cost_usd_per_day": 0.0,
    "allow_paid_api": False, "allow_openrouter_free_only": True,
    "allowed_providers": ["openrouter"], "timeout_seconds": 30,
    "max_response_bytes": 1000000,
}
ENDPOINTS = {
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
    "openai": "https://api.openai.com/v1/chat/completions",
}
ENV_KEYS = {"openrouter": "OPENROUTER_API_KEY", "openai": "OPENAI_API_KEY"}

class ProviderPolicyError(PermissionError): pass
class ProviderRequestError(RuntimeError): pass

@dataclass(frozen=True)
class ProviderResult:
    provider: str
    model: str
    text: str
    status: str
    request_id: str
    usage: dict[str, Any]
    latency_ms: int

def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)

def _sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

class ProviderCallLedger:
    """Append-only SQLite metadata ledger; no prompts, outputs, or credentials."""
    def __init__(self, db_path="advait_provider_audit.db"):
        self.db_path = str(db_path)
        with self._connect() as con:
            con.execute("""CREATE TABLE IF NOT EXISTS provider_calls (
                request_id TEXT PRIMARY KEY, provider TEXT NOT NULL, model TEXT NOT NULL,
                request_sha256 TEXT NOT NULL, response_sha256 TEXT, status TEXT NOT NULL,
                http_status INTEGER, latency_ms INTEGER NOT NULL, usage_json TEXT NOT NULL,
                cost_usd REAL, error_code TEXT, created_at REAL NOT NULL)""")
            con.execute("""CREATE TRIGGER IF NOT EXISTS provider_calls_no_update
                BEFORE UPDATE ON provider_calls BEGIN
                SELECT RAISE(ABORT, 'provider audit is append-only'); END""")
            con.execute("""CREATE TRIGGER IF NOT EXISTS provider_calls_no_delete
                BEFORE DELETE ON provider_calls BEGIN
                SELECT RAISE(ABORT, 'provider audit is append-only'); END""")
    def _connect(self):
        con = sqlite3.connect(self.db_path, timeout=10)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA foreign_keys=ON")
        return con
    def append(self, **event):
        with self._connect() as con:
            con.execute("""INSERT INTO provider_calls
                (request_id,provider,model,request_sha256,response_sha256,status,
                 http_status,latency_ms,usage_json,cost_usd,error_code,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (event["request_id"],event["provider"],event["model"],event["request_sha256"],
                 event.get("response_sha256"),event["status"],event.get("http_status"),
                 int(event["latency_ms"]),_canonical(event.get("usage") or {}),
                 event.get("cost_usd"),event.get("error_code"),time.time()))
    def events(self, limit=100):
        limit=max(1,min(int(limit),500))
        with self._connect() as con:
            rows=con.execute("""SELECT request_id,provider,model,request_sha256,response_sha256,
                status,http_status,latency_ms,usage_json,cost_usd,error_code,created_at
                FROM provider_calls ORDER BY created_at DESC LIMIT ?""",(limit,)).fetchall()
        keys=("request_id","provider","model","request_sha256","response_sha256","status",
              "http_status","latency_ms","usage_json","cost_usd","error_code","created_at")
        return [dict(zip(keys,row)) for row in rows]

class ProviderRouterV1:
    """Single-call model adapter; host owns identity, scheduling, approvals and execution."""
    def __init__(self, *, ledger, policy=None, environ=None):
        self.ledger=ledger
        self.policy={**DEFAULT_POLICY,**(policy or {})}
        self.environ=os.environ if environ is None else environ
    def _validate(self, provider, model):
        if provider not in ENDPOINTS: raise ProviderPolicyError("provider_not_allowlisted")
        if provider not in self.policy["allowed_providers"]: raise ProviderPolicyError("provider_disabled_by_policy")
        if not isinstance(model,str) or not model.strip() or len(model)>200:
            raise ProviderPolicyError("invalid_model")
        if provider=="openrouter" and self.policy["allow_openrouter_free_only"] and not model.endswith(":free"):
            raise ProviderPolicyError("openrouter_paid_model_blocked")
        if provider=="openai":
            if not self.policy["allow_paid_api"]: raise ProviderPolicyError("openai_api_disabled_under_zero_spend_policy")
            if float(self.policy["max_cost_usd_per_call"])<=0 or float(self.policy["max_cost_usd_per_day"])<=0:
                raise ProviderPolicyError("positive_budget_required")
        return model.strip()
    def call(self, *, provider, model, messages, temperature=0.2, max_tokens=1200):
        model=self._validate(provider,model)
        if not isinstance(messages,list) or not messages: raise ValueError("messages must be non-empty")
        for m in messages:
            if (not isinstance(m,dict) or set(m)-{"role","content"}
                or m.get("role") not in {"system","user","assistant"}
                or not isinstance(m.get("content"),str)):
                raise ValueError("messages must contain only role/content text entries")
        if not 0<=float(temperature)<=2: raise ValueError("invalid temperature")
        if not 1<=int(max_tokens)<=8000: raise ValueError("invalid max_tokens")
        key=self.environ.get(ENV_KEYS[provider],"")
        if not key: raise ProviderPolicyError("provider_api_key_missing")
        request_id=str(uuid.uuid4())
        body={"model":model,"messages":messages,"temperature":float(temperature),"max_tokens":int(max_tokens)}
        encoded=_canonical(body).encode("utf-8")
        req=urllib.request.Request(ENDPOINTS[provider],data=encoded,headers={
            "Authorization":"Bearer "+key,"Content-Type":"application/json",
            "HTTP-Referer":"https://github.com/kautilyamehra4436-cmyk/my-brain",
            "X-Title":"Advait v32.0"},method="POST")
        started=time.monotonic(); http_status=None
        try:
            with urllib.request.urlopen(req,timeout=max(1,min(int(self.policy["timeout_seconds"]),60))) as response:
                http_status=int(response.status)
                raw=response.read(int(self.policy["max_response_bytes"])+1)
            if len(raw)>int(self.policy["max_response_bytes"]): raise ProviderRequestError("provider_response_too_large")
            data=json.loads(raw.decode("utf-8"))
            answer=data["choices"][0]["message"]["content"]
            if not isinstance(answer,str): raise ProviderRequestError("provider_non_text_response")
            usage=data.get("usage") if isinstance(data.get("usage"),dict) else {}
            cost=usage.get("cost")
            try: cost=None if cost is None else float(cost)
            except (TypeError,ValueError): cost=None
            latency=int((time.monotonic()-started)*1000)
            self.ledger.append(request_id=request_id,provider=provider,model=model,
                request_sha256=_sha(_canonical(body)),response_sha256=_sha(answer),
                status="success",http_status=http_status,latency_ms=latency,usage=usage,cost_usd=cost)
            return ProviderResult(provider,model,answer,"success",request_id,usage,latency)
        except urllib.error.HTTPError as exc:
            latency=int((time.monotonic()-started)*1000)
            self.ledger.append(request_id=request_id,provider=provider,model=model,
                request_sha256=_sha(_canonical(body)),response_sha256=None,status="error",
                http_status=int(exc.code),latency_ms=latency,error_code="http_error")
            raise ProviderRequestError("provider_http_error_"+str(exc.code)) from None
        except ProviderRequestError: raise
        except Exception as exc:
            latency=int((time.monotonic()-started)*1000)
            self.ledger.append(request_id=request_id,provider=provider,model=model,
                request_sha256=_sha(_canonical(body)),response_sha256=None,status="error",
                http_status=http_status,latency_ms=latency,error_code=type(exc).__name__)
            raise ProviderRequestError("provider_request_failed_"+type(exc).__name__) from None
