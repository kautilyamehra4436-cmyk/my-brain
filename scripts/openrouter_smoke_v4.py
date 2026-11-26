"""Bounded OpenRouter free smoke test: two attempts, 90s each, metadata-only audit."""
from __future__ import annotations
import argparse, hashlib, json, os, re, sqlite3, sys, time, urllib.error, urllib.request
from pathlib import Path

ENDPOINT="https://openrouter.ai/api/v1/chat/completions"
PROMPT="Reply with exactly the word OK."

def audit(status, model, latency, http_status=None, usage=None, error=None, req_hash=None, res_hash=None, attempt=1):
    d=Path("artifacts"); d.mkdir(exist_ok=True)
    con=sqlite3.connect(d/"openrouter_smoke_audit_v4.db")
    try:
        con.execute("""CREATE TABLE IF NOT EXISTS smoke_audit(
          id INTEGER PRIMARY KEY, created_at REAL, attempt INTEGER, status TEXT,
          http_status INTEGER, model TEXT, latency_ms INTEGER, usage_json TEXT,
          error_code TEXT, request_sha256 TEXT, response_sha256 TEXT)""")
        con.execute("INSERT INTO smoke_audit(created_at,attempt,status,http_status,model,latency_ms,usage_json,error_code,request_sha256,response_sha256) VALUES(?,?,?,?,?,?,?,?,?,?)",
          (time.time(),attempt,status,http_status,model,latency,json.dumps(usage or {},sort_keys=True),error,req_hash,res_hash))
        con.commit()
    finally: con.close()

def main():
    p=argparse.ArgumentParser(); p.add_argument("--model",required=True); a=p.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9._/-]{1,180}:free",a.model):
        print("BLOCKED: model identifier must end in :free."); return 2
    key=os.getenv("OPENROUTER_API_KEY","")
    if not key: print("BLOCKED: OPENROUTER_API_KEY is missing."); return 2
    payload={"model":a.model,"messages":[{"role":"user","content":PROMPT}],
             "temperature":0,"max_tokens":128,"reasoning":{"enabled":False}}
    raw=json.dumps(payload,separators=(",",":"),sort_keys=True).encode()
    req_hash=hashlib.sha256(raw).hexdigest()
    for attempt in (1,2):
        req=urllib.request.Request(ENDPOINT,data=raw,headers={
          "Authorization":"Bearer "+key,"Content-Type":"application/json",
          "HTTP-Referer":"https://github.com/kautilyamehra4436-cmyk/my-brain",
          "X-Title":"Advait v32.0 smoke v4"},method="POST")
        started=time.monotonic(); status=None
        try:
            with urllib.request.urlopen(req,timeout=90) as response:
                status=int(response.status); body=response.read(1_000_001)
            if len(body)>1_000_000: raise ValueError("response_too_large")
            data=json.loads(body.decode("utf-8"))
            api_error=data.get("error"); choices=data.get("choices") or []
            choice=choices[0] if choices else {}
            api_error=api_error or choice.get("error")
            latency=int((time.monotonic()-started)*1000)
            usage=data.get("usage") if isinstance(data.get("usage"),dict) else {}
            if api_error:
                code=str(api_error.get("code","provider_error"))[:60] if isinstance(api_error,dict) else "provider_error"
                audit("error",a.model,latency,status,usage,"api_"+code,req_hash,attempt=attempt)
                print("SMOKE_TEST_FAILED: provider_api_error_"+code); return 1
            message=choice.get("message") or {}; content=message.get("content")
            if isinstance(content,str): answer=content
            elif isinstance(content,list):
                answer="".join(x.get("text","") for x in content if isinstance(x,dict) and x.get("type") in ("text","output_text") and isinstance(x.get("text"),str))
            else: answer=""
            if not answer.strip():
                shape="null" if content is None else type(content).__name__
                finish=str(choice.get("finish_reason") or "unknown")[:40]
                err="empty_text_"+shape+"_finish_"+finish
                audit("error",a.model,latency,status,usage,err,req_hash,attempt=attempt)
                print("SMOKE_TEST_FAILED:",err); return 1
            digest=hashlib.sha256(answer.encode()).hexdigest()
            audit("success",a.model,latency,status,usage,None,req_hash,digest,attempt)
            print("SMOKE_TEST_PASSED")
            print("provider: openrouter"); print("model:",a.model)
            print("http_status:",status); print("latency_ms:",latency)
            print("attempt:",attempt); print("usage_metadata_available:",bool(usage))
            print("response_content: [not displayed]")
            return 0
        except urllib.error.HTTPError as exc:
            latency=int((time.monotonic()-started)*1000)
            audit("error",a.model,latency,int(exc.code),error="http_error",req_hash=req_hash,attempt=attempt)
            print("SMOKE_TEST_FAILED: provider_http_error_"+str(exc.code)); return 1
        except (TimeoutError, urllib.error.URLError) as exc:
            latency=int((time.monotonic()-started)*1000)
            is_timeout=isinstance(exc,TimeoutError) or isinstance(getattr(exc,"reason",None),TimeoutError)
            code="timeout" if is_timeout else "network_error"
            audit("error",a.model,latency,status,error=code,req_hash=req_hash,attempt=attempt)
            if attempt==1:
                print("FIRST_ATTEMPT_"+code.upper()+"; retrying once.")
                time.sleep(3)
                continue
            print("SMOKE_TEST_FAILED: "+code+"_after_2_attempts"); return 1
        except Exception as exc:
            latency=int((time.monotonic()-started)*1000)
            audit("error",a.model,latency,status,error=type(exc).__name__,req_hash=req_hash,attempt=attempt)
            print("SMOKE_TEST_FAILED: safe_parse_error_"+type(exc).__name__); return 1
    return 1

if __name__=="__main__": sys.exit(main())
