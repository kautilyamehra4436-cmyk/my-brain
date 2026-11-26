"""Additive, bounded provider adapter for Advait v32.0.
Secrets are read from environment only. Prompt/response content is never persisted.
Hard-zero policy is immutable: OpenRouter :free only; no paid provider or fallback.
This is a single-call adapter, not a daemon, scheduler, browser, or task executor.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Any

from core.managed_sqlite_v1 import managed_connection


MAX_RESPONSE_BYTES = 1_000_000
MAX_REQUEST_BYTES = 65_536
MAX_MESSAGES = 16
MAX_TOKENS = 4_000
MODEL_PATTERN = re.compile(r"^[A-Za-z0-9._/-]{1,180}:free$")

DEFAULT_POLICY = {
    "max_cost_usd_per_call": 0.0,
    "max_cost_usd_per_day": 0.0,
    "allow_paid_api": False,
    "allow_openrouter_free_only": True,
    "allowed_providers": ["openrouter"],
    "timeout_seconds": 30,
    "max_response_bytes": MAX_RESPONSE_BYTES,
    "max_request_bytes": MAX_REQUEST_BYTES,
    "max_messages": MAX_MESSAGES,
    "max_tokens": MAX_TOKENS,
}
ENDPOINTS = {
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
    "openai": "https://api.openai.com/v1/chat/completions",
}
ENV_KEYS = {"openrouter": "OPENROUTER_API_KEY", "openai": "OPENAI_API_KEY"}


class ProviderPolicyError(PermissionError):
    pass


class ProviderRequestError(RuntimeError):
    pass


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
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    )


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
        return managed_connection(self.db_path, timeout=10)

    def append(self, **event):
        with self._connect() as con:
            con.execute("""INSERT INTO provider_calls
                (request_id,provider,model,request_sha256,response_sha256,status,
                 http_status,latency_ms,usage_json,cost_usd,error_code,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (event["request_id"], event["provider"], event["model"],
                 event["request_sha256"], event.get("response_sha256"),
                 event["status"], event.get("http_status"), int(event["latency_ms"]),
                 _canonical(event.get("usage") or {}), event.get("cost_usd"),
                 event.get("error_code"), time.time()))

    def events(self, limit=100):
        limit = max(1, min(int(limit), 500))
        with self._connect() as con:
            rows = con.execute("""SELECT request_id,provider,model,request_sha256,response_sha256,
                status,http_status,latency_ms,usage_json,cost_usd,error_code,created_at
                FROM provider_calls ORDER BY created_at DESC LIMIT ?""", (limit,)).fetchall()
        keys = ("request_id", "provider", "model", "request_sha256", "response_sha256",
                "status", "http_status", "latency_ms", "usage_json", "cost_usd",
                "error_code", "created_at")
        return [dict(zip(keys, row)) for row in rows]


class ProviderRouterV1:
    """Single-call OpenRouter :free adapter; caller policy can tighten, never loosen."""

    def __init__(self, *, ledger, policy=None, environ=None):
        self.ledger = ledger
        requested = {} if policy is None else policy
        if not isinstance(requested, dict):
            raise ProviderPolicyError("hard_zero_policy_must_be_a_mapping")
        unknown = set(requested) - set(DEFAULT_POLICY)
        if unknown:
            raise ProviderPolicyError("unknown_provider_policy_keys")
        if requested.get("allow_paid_api", False) is not False:
            raise ProviderPolicyError("hard_zero_policy_cannot_be_relaxed")
        if requested.get("allow_openrouter_free_only", True) is not True:
            raise ProviderPolicyError("hard_zero_policy_cannot_be_relaxed")
        for key in ("max_cost_usd_per_call", "max_cost_usd_per_day"):
            value = requested.get(key, 0.0)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value != 0:
                raise ProviderPolicyError("hard_zero_policy_cannot_be_relaxed")
        allowed = requested.get("allowed_providers", ["openrouter"])
        if not isinstance(allowed, list) or any(item != "openrouter" for item in allowed):
            raise ProviderPolicyError("hard_zero_policy_cannot_be_relaxed")
        response_limit = requested.get("max_response_bytes", MAX_RESPONSE_BYTES)
        if isinstance(response_limit, bool) or not isinstance(response_limit, int) or not 1 <= response_limit <= MAX_RESPONSE_BYTES:
            raise ProviderPolicyError("response_limit_out_of_bounds")
        request_limit = requested.get("max_request_bytes", MAX_REQUEST_BYTES)
        if isinstance(request_limit, bool) or not isinstance(request_limit, int) or not 1 <= request_limit <= MAX_REQUEST_BYTES:
            raise ProviderPolicyError("request_limit_out_of_bounds")
        message_limit = requested.get("max_messages", MAX_MESSAGES)
        if isinstance(message_limit, bool) or not isinstance(message_limit, int) or not 1 <= message_limit <= MAX_MESSAGES:
            raise ProviderPolicyError("message_limit_out_of_bounds")
        token_limit = requested.get("max_tokens", MAX_TOKENS)
        if isinstance(token_limit, bool) or not isinstance(token_limit, int) or not 1 <= token_limit <= MAX_TOKENS:
            raise ProviderPolicyError("token_limit_out_of_bounds")
        timeout = requested.get("timeout_seconds", 30)
        if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 60:
            raise ProviderPolicyError("timeout_limit_out_of_bounds")
        self.policy = {
            **DEFAULT_POLICY,
            **requested,
            "allow_paid_api": False,
            "allow_openrouter_free_only": True,
            "max_cost_usd_per_call": 0.0,
            "max_cost_usd_per_day": 0.0,
            "allowed_providers": list(allowed),
            "max_response_bytes": response_limit,
            "max_request_bytes": request_limit,
            "max_messages": message_limit,
            "max_tokens": token_limit,
            "timeout_seconds": timeout,
        }
        self.environ = os.environ if environ is None else environ

    def _validate(self, provider, model):
        if provider not in ENDPOINTS:
            raise ProviderPolicyError("provider_not_allowlisted")
        if provider != "openrouter" or provider not in self.policy["allowed_providers"]:
            raise ProviderPolicyError("provider_disabled_by_policy_under_hard_zero")
        if not isinstance(model, str) or not MODEL_PATTERN.fullmatch(model):
            raise ProviderPolicyError("openrouter_paid_model_blocked_or_invalid_model")
        return model

    def call(self, *, provider, model, messages, temperature=0.2, max_tokens=1200):
        model = self._validate(provider, model)
        if not isinstance(messages, list) or not messages or len(messages) > self.policy["max_messages"]:
            raise ValueError("messages must be a non-empty bounded list")
        for message in messages:
            if (
                not isinstance(message, dict)
                or set(message) - {"role", "content"}
                or message.get("role") not in {"system", "user", "assistant"}
                or not isinstance(message.get("content"), str)
            ):
                raise ValueError("messages must contain only role/content text entries")
        if isinstance(temperature, bool) or not isinstance(temperature, (int, float)) or not 0 <= float(temperature) <= 2:
            raise ValueError("invalid temperature")
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or not 1 <= max_tokens <= self.policy["max_tokens"]:
            raise ValueError("invalid max_tokens")
        body = {
            "model": model,
            "messages": messages,
            "temperature": float(temperature),
            "max_tokens": max_tokens,
        }
        encoded = _canonical(body).encode("utf-8")
        if len(encoded) > self.policy["max_request_bytes"]:
            raise ValueError("provider_request_too_large")
        key = self.environ.get("OPENROUTER_API_KEY", "")
        if not key:
            raise ProviderPolicyError("provider_api_key_missing")
        request_id = str(uuid.uuid4())
        request = urllib.request.Request(
            ENDPOINTS["openrouter"],
            data=encoded,
            headers={
                "Authorization": "Bearer " + key,
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/kautilyamehra4436-cmyk/my-brain",
                "X-Title": "Advait v32.0",
            },
            method="POST",
        )
        started = time.monotonic()
        http_status = None
        request_sha256 = _sha(_canonical(body))
        try:
            with urllib.request.urlopen(request, timeout=self.policy["timeout_seconds"]) as response:
                http_status = int(response.status)
                raw = response.read(self.policy["max_response_bytes"] + 1)
            if len(raw) > self.policy["max_response_bytes"]:
                raise ProviderRequestError("provider_response_too_large")
            data = json.loads(raw.decode("utf-8"))
            answer = data["choices"][0]["message"]["content"]
            if not isinstance(answer, str):
                raise ProviderRequestError("provider_non_text_response")
            provider_usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
            raw_cost = provider_usage.get("cost")
            try:
                cost = None if raw_cost is None else float(raw_cost)
            except (TypeError, ValueError):
                cost = None
            safe_usage = {
                key: provider_usage[key]
                for key in ("prompt_tokens", "completion_tokens", "total_tokens", "cost")
                if key in provider_usage and isinstance(provider_usage[key], (int, float, str))
            }
            latency = int((time.monotonic() - started) * 1000)
            response_sha256 = _sha(answer)
            if cost is None or not math.isfinite(cost) or cost < 0:
                self.ledger.append(
                    request_id=request_id, provider=provider, model=model,
                    request_sha256=request_sha256, response_sha256=response_sha256,
                    status="cost_unverified", http_status=http_status, latency_ms=latency,
                    usage=safe_usage, cost_usd=None, error_code="provider_cost_unverified",
                )
                raise ProviderPolicyError("provider_cost_unverified")
            if cost > 0:
                self.ledger.append(
                    request_id=request_id, provider=provider, model=model,
                    request_sha256=request_sha256, response_sha256=response_sha256,
                    status="positive_cost_reported", http_status=http_status,
                    latency_ms=latency, usage=safe_usage, cost_usd=cost,
                    error_code="positive_cost_reported",
                )
                raise ProviderPolicyError("provider_positive_cost_reported")
            self.ledger.append(
                request_id=request_id, provider=provider, model=model,
                request_sha256=request_sha256, response_sha256=response_sha256,
                status="success", http_status=http_status, latency_ms=latency,
                usage=safe_usage, cost_usd=0.0,
            )
            return ProviderResult(
                provider, model, answer, "success", request_id, safe_usage, latency
            )
        except ProviderPolicyError:
            raise
        except urllib.error.HTTPError as exc:
            latency = int((time.monotonic() - started) * 1000)
            self.ledger.append(
                request_id=request_id, provider=provider, model=model,
                request_sha256=request_sha256, response_sha256=None, status="error",
                http_status=int(exc.code), latency_ms=latency, error_code="http_error",
            )
            raise ProviderRequestError("provider_http_error_" + str(exc.code)) from None
        except ProviderRequestError:
            raise
        except Exception as exc:
            latency = int((time.monotonic() - started) * 1000)
            self.ledger.append(
                request_id=request_id, provider=provider, model=model,
                request_sha256=request_sha256, response_sha256=None, status="error",
                http_status=http_status, latency_ms=latency,
                error_code=type(exc).__name__,
            )
            raise ProviderRequestError("provider_request_failed_" + type(exc).__name__) from None
