"""One-request OpenRouter free smoke check with reasoning disabled and safe diagnostics."""
from __future__ import annotations
import argparse, hashlib, json, os, re, sqlite3, sys, time, urllib.error, urllib.request
from pathlib import Path

ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
PROMPT = "Reply with exactly the word OK."

def safe_audit(status, http_status, model, latency_ms, usage=None, error_code=None, request_hash=None, response_hash=None):
    path = Path("artifacts")
    path.mkdir(exist_ok=True)
    db = sqlite3.connect(path / "openrouter_smoke_audit_v3.db")
    try:
        db.execute("""CREATE TABLE IF NOT EXISTS smoke_audit (
            id INTEGER PRIMARY KEY, created_at REAL NOT NULL, status TEXT NOT NULL,
            http_status INTEGER, model TEXT NOT NULL, latency_ms INTEGER NOT NULL,
            usage_json TEXT NOT NULL, error_code TEXT, request_sha256 TEXT,
            response_sha256 TEXT)""")
        db.execute("""INSERT INTO smoke_audit
            (created_at,status,http_status,model,latency_ms,usage_json,error_code,request_sha256,response_sha256)
            VALUES(?,?,?,?,?,?,?,?,?)""",
            (time.time(),status,http_status,model,latency_ms,
             json.dumps(usage or {},sort_keys=True),error_code,request_hash,response_hash))
        db.commit()
    finally:
        db.close()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--model",required=True)
    a=p.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9._/-]{1,180}:free",a.model):
        print("BLOCKED: model identifier must end in :free."); return 2
    key=os.environ.get("OPENROUTER_API_KEY","")
    if not key:
        print("BLOCKED: OPENROUTER_API_KEY is missing."); return 2
    payload={
        "model":a.model,
        "messages":[{"role":"user","content":PROMPT}],
        "temperature":0,
        "max_tokens":128,
        "reasoning":{"enabled":False},
    }
    encoded=json.dumps(payload,separators=(",",":"),sort_keys=True).encode()
    request_hash=hashlib.sha256(encoded).hexdigest()
    req=urllib.request.Request(ENDPOINT,data=encoded,headers={
        "Authorization":"Bearer "+key,
        "Content-Type":"application/json",
        "HTTP-Referer":"https://github.com/kautilyamehra4436-cmyk/my-brain",
        "X-Title":"Advait v32.0 smoke v3"},method="POST")
    start=time.monotonic(); http_status=None
    try:
        with urllib.request.urlopen(req,timeout=35) as response:
            http_status=int(response.status)
            raw=response.read(1_000_001)
        if len(raw)>1_000_000:
            raise ValueError("response_too_large")
        data=json.loads(raw.decode("utf-8"))
        api_error=data.get("error")
        choices=data.get("choices") or []
        choice=choices[0] if choices else {}
        api_error=api_error or choice.get("error")
        if api_error:
            code=str(api_error.get("code","provider_error"))[:60] if isinstance(api_error,dict) else "provider_error"
            latency=int((time.monotonic()-start)*1000)
            safe_audit("error",http_status,a.model,latency,data.get("usage"),"api_"+code,request_hash)
            print("SMOKE_TEST_FAILED: provider_api_error_"+code); return 1
        message=choice.get("message") or {}
        content=message.get("content")
        if isinstance(content,str):
            answer=content
        elif isinstance(content,list):
            answer="".join(x.get("text","") for x in content if isinstance(x,dict) and x.get("type") in ("text","output_text") and isinstance(x.get("text"),str))
        else:
            answer=""
        latency=int((time.monotonic()-start)*1000)
        usage=data.get("usage") if isinstance(data.get("usage"),dict) else {}
        if not answer.strip():
            # Record only response shape metadata; never print/store raw model content.
            shape="null" if content is None else type(content).__name__
            finish=str(choice.get("finish_reason") or "unknown")[:40]
            reason_present=bool(message.get("reasoning") or message.get("reasoning_details"))
            error="empty_text_"+shape+"_finish_"+finish+"_reasoning_"+str(reason_present).lower()
            safe_audit("error",http_status,a.model,latency,usage,error,request_hash)
            print("SMOKE_TEST_FAILED:",error); return 1
        response_hash=hashlib.sha256(answer.encode()).hexdigest()
        safe_audit("success",http_status,a.model,latency,usage,None,request_hash,response_hash)
        print("SMOKE_TEST_PASSED")
        print("provider: openrouter")
        print("model:",a.model)
        print("http_status:",http_status)
        print("latency_ms:",latency)
        print("usage_metadata_available:",bool(usage))
        print("response_content: [not displayed]")
        print("audit_database: artifacts/openrouter_smoke_audit_v3.db")
        return 0
    except urllib.error.HTTPError as exc:
        latency=int((time.monotonic()-start)*1000)
        safe_audit("error",int(exc.code),a.model,latency,error_code="http_error",request_hash=request_hash)
        print("SMOKE_TEST_FAILED: provider_http_error_"+str(exc.code)); return 1
    except Exception as exc:
        latency=int((time.monotonic()-start)*1000)
        safe_audit("error",http_status,a.model,latency,error_code=type(exc).__name__,request_hash=request_hash)
        print("SMOKE_TEST_FAILED: safe_transport_or_parse_error_"+type(exc).__name__); return 1

if __name__=="__main__":
    sys.exit(main())
