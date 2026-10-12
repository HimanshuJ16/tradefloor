"""User-selected model endpoints. Credentials never enter research records."""
from __future__ import annotations

import ipaddress
import json
import os
import re
import socket
import time
import uuid
from urllib.parse import urlsplit

import httpx
import keyring

from . import research, runs, settings, validation as v
from .evidence import text
from .storage import canonical, connect

PROTOCOLS = {"openai", "anthropic"}
FIELDS = {"name", "protocol", "base_url", "model", "key_env", "input_price", "output_price", "token_parameter", "stream_usage"}


def endpoint(value, resolve=False):
    value = text(value, "base_url", 1000).rstrip("/")
    if any(c.isspace() for c in value):
        raise ValueError("Model base URL cannot contain whitespace")
    u = urlsplit(value)
    if u.scheme not in ("https", "http") or not u.hostname or u.username or u.password or u.query or u.fragment:
        raise ValueError("Use an HTTP(S) base URL without credentials, query or fragment")
    local = u.hostname in ("localhost", "127.0.0.1", "::1")
    if u.scheme != "https" and not local:
        raise ValueError("HTTP is allowed only for a loopback model server")
    if not local:
        try:
            addresses = [ipaddress.ip_address(u.hostname)]
        except ValueError:
            addresses = []
        if resolve:
            try:
                addresses = [ipaddress.ip_address(row[4][0]) for row in socket.getaddrinfo(u.hostname, u.port or 443, type=socket.SOCK_STREAM)]
            except OSError:
                raise ValueError("Model endpoint DNS lookup failed") from None
        if any(not a.is_global for a in addresses):
            raise ValueError("Use a public HTTPS endpoint or an explicit loopback address")
    return value


def _vault():
    backend = keyring.get_keyring()
    # Explicit OS backends only; never silently accept a plaintext/custom fallback.
    if type(backend).__module__ not in ("keyring.backends.Windows", "keyring.backends.macOS", "keyring.backends.SecretService"):
        raise ValueError("An OS credential store is unavailable. Use an environment-variable key instead.")
    return backend


def _service():
    return "tradefloor-models-" + runs.digest(str(settings.home().resolve()))[:16]


def _secret(profile):
    if profile.get("key_env"):
        value = os.environ.get(profile["key_env"], "")
        if not value or "${" in value:
            raise ValueError(f"API-key environment variable {profile['key_env']} is not set")
        return value
    if profile.get("has_key"):
        try:
            value = _vault().get_password(_service(), profile.get("key_ref", profile["id"]))
        except Exception:
            raise ValueError("Cannot read the OS credential store; unlock it or use an environment key") from None
        if not value:
            raise ValueError("The profile's stored API key is missing")
        return value
    return ""


def profiles(action="list", profile_id=None, body=None, api_key=None):
    if action == "list":
        with connect(research.database()) as db:
            rows = db.execute("SELECT body FROM config WHERE key LIKE 'model:%' ORDER BY key").fetchall()
        try:
            _vault()
            vault = True
        except Exception:
            vault = False
        return {"profiles": [json.loads(r[0]) for r in rows], "credential_store_available": vault}
    if action == "get":
        runs.identity(profile_id)
        with connect(research.database()) as db:
            row = db.execute("SELECT body FROM config WHERE key=?", ("model:" + profile_id,)).fetchone()
        if not row:
            raise ValueError("Model profile not found")
        return json.loads(row[0])
    if action == "test":
        profile = profiles("get", profile_id)
        result = complete(profile, "Reply with the word connected.", "Connection test; no research data.", 16)
        return {"connected": bool(result["text"]), "profile_id": profile_id, "latency_ms": result["latency_ms"], "usage": result["usage"], "note": "This test makes one potentially billable API request."}
    if action == "delete":
        p = profiles("get", profile_id)
        if p.get("has_key"):
            try:
                _vault().delete_password(_service(), p.get("key_ref", profile_id))
            except Exception:
                raise ValueError("Could not remove the stored credential; profile was retained") from None
        with connect(research.database()) as db:
            db.execute("DELETE FROM config WHERE key=?", ("model:" + profile_id,))
        return {"deleted": profile_id}
    if action != "save" or not isinstance(body, dict) or set(body) - FIELDS:
        raise ValueError("Unsupported model profile action or fields")
    old = profiles("get", profile_id) if profile_id else {}
    identifier = profile_id or uuid.uuid4().hex
    protocol = body.get("protocol", "openai")
    if protocol not in PROTOCOLS:
        raise ValueError("Use openai or anthropic protocol")
    p = {"id": identifier, "name": text(body.get("name"), "name", 80), "protocol": protocol,
         "base_url": endpoint(body.get("base_url")), "model": text(body.get("model"), "model", 160),
         "key_env": body.get("key_env", ""), "has_key": old.get("has_key", False), "key_ref": old.get("key_ref", identifier),
         "input_price": None if body.get("input_price") is None else v.number(body["input_price"], "input_price", 0, 10000),
         "output_price": None if body.get("output_price") is None else v.number(body["output_price"], "output_price", 0, 10000),
         "token_parameter": body.get("token_parameter", "max_tokens"), "stream_usage": body.get("stream_usage", False)}
    if p["token_parameter"] not in ("max_tokens", "max_completion_tokens") or type(p["stream_usage"]) is not bool:
        raise ValueError("Invalid token parameter or stream_usage")
    if not isinstance(p["key_env"], str) or (p["key_env"] and not re.fullmatch(r"[A-Z][A-Z0-9_]{0,79}", p["key_env"])):
        raise ValueError("key_env must be an environment-variable name")
    if old and p["base_url"] != old["base_url"] and old.get("has_key") and api_key is None:
        raise ValueError("Re-enter the credential when changing its destination")
    new_key_ref = None
    if api_key is not None:
        if p["key_env"]:
            raise ValueError("Choose a stored key or an environment key, not both")
        if not isinstance(api_key, str) or len(api_key) > 4096 or "\n" in api_key or "\r" in api_key:
            raise ValueError("Invalid API key")
        try:
            vault = _vault()
            if api_key:
                # Stage a new slot. A failed SQLite update must never associate a
                # replacement credential with the previous endpoint destination.
                new_key_ref = uuid.uuid4().hex
                vault.set_password(_service(), new_key_ref, api_key)
                p["key_ref"] = new_key_ref
        except Exception:
            raise ValueError("Could not update the OS credential store; use an environment key") from None
        p["has_key"] = bool(api_key)
    try:
        with connect(research.database()) as db:
            db.execute("INSERT OR REPLACE INTO config(key,body) VALUES (?,?)", ("model:" + identifier, canonical(p)))
    except Exception:
        if new_key_ref:
            try:
                _vault().delete_password(_service(), new_key_ref)
            except Exception:
                pass
        raise ValueError("Profile metadata could not be saved; the previous connection was retained") from None
    if api_key is not None and old.get("has_key"):
        try:
            _vault().delete_password(_service(), old.get("key_ref", identifier))
        except Exception:
            p["credential_cleanup_note"] = "The active connection was saved, but a retired OS credential slot could not be removed."
    return p


def complete(profile, system, prompt, max_tokens, on_delta=None, cancelled=None):
    """Bounded SSE transport, no redirects/retries/proxy credentials or exception-body logging."""
    max_tokens = v.integer(max_tokens, "max_tokens", 16, 8192)
    base = endpoint(profile["base_url"], resolve=True)
    key = _secret(profile)
    protocol = profile["protocol"]
    headers = {"Content-Type": "application/json"}
    if protocol == "anthropic":
        url = base + "/messages"
        headers.update({"anthropic-version": "2023-06-01", "x-api-key": key})
        payload = {"model": profile["model"], "max_tokens": max_tokens, "stream": True, "system": system,
                   "messages": [{"role": "user", "content": prompt}]}
    else:
        url = base + "/chat/completions"
        if key:
            headers["Authorization"] = "Bearer " + key
        payload = {"model": profile["model"], profile["token_parameter"]: max_tokens, "stream": True,
                   "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}
        if profile.get("stream_usage"):
            payload["stream_options"] = {"include_usage": True}
    started = time.monotonic()
    if cancelled:
        cancelled()
    content, usage, size, finished = [], {}, 0, False
    pending = ""
    try:
        with httpx.Client(timeout=httpx.Timeout(20, connect=10), follow_redirects=False, trust_env=False) as client:
            with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    raise ValueError(f"Model endpoint returned HTTP {response.status_code}; check protocol, model and credential")
                for line in _lines(response):
                    if cancelled:
                        cancelled()
                    if time.monotonic() - started > 120:
                        raise ValueError("Model call exceeded its 120-second time limit")
                    size += len(line.encode())
                    if size > 1_000_000:
                        raise ValueError("Model stream exceeded its 1 MB limit")
                    if not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if raw == "[DONE]":
                        finished = True
                        break
                    try:
                        event = json.loads(raw)
                    except ValueError:
                        raise ValueError("Model endpoint returned malformed stream data") from None
                    delta = ""
                    if protocol == "anthropic":
                        if event.get("type") == "error":
                            raise ValueError("Provider reported a stream error")
                        if event.get("type") == "message_start":
                            usage.update(event.get("message", {}).get("usage", {}))
                        if event.get("type") == "message_delta":
                            usage.update(event.get("usage", {}))
                        if event.get("type") == "message_stop":
                            finished = True
                            break
                        delta = event.get("delta", {}).get("text", "")
                    else:
                        if event.get("error"):
                            raise ValueError("Provider reported a stream error")
                        usage.update(event.get("usage") or {})
                        choices = event.get("choices") or []
                        if choices:
                            delta = choices[0].get("delta", {}).get("content") or ""
                    if not isinstance(delta, str):
                        raise ValueError("Model returned unsupported content")
                    if delta:
                        # Model output must not leak an accidentally echoed credential.
                        content.append(delta)
                        if sum(map(len, content)) > 64000:
                            raise ValueError("Model output exceeded its text limit")
                        if on_delta:
                            pending = (pending + delta).replace(key, "[credential redacted]") if key else pending + delta
                            hold = len(key) - 1 if key else 0
                            if len(pending) > hold:
                                emit_length = len(pending) - hold
                                on_delta(pending[:emit_length])
                                pending = pending[emit_length:]
    except httpx.HTTPError:
        raise ValueError("Model request failed or timed out; endpoint details and credentials were omitted") from None
    if not finished or not content:
        raise ValueError("Model stream ended without a complete text response")
    output = "".join(content)
    if key and key in output:
        output = output.replace(key, "[credential redacted]")
    if on_delta and pending:
        on_delta(pending)
    return {"text": output, "usage": usage, "latency_ms": (time.monotonic() - started) * 1000}


def _lines(response):
    pending, total = b"", 0
    for chunk in response.iter_bytes():
        total += len(chunk)
        if total > 1_000_000:
            raise ValueError("Model stream exceeded its 1 MB limit")
        pending += chunk
        while b"\n" in pending:
            raw, pending = pending.split(b"\n", 1)
            if len(raw) > 100000:
                raise ValueError("Model stream line exceeds 100 KB")
            try:
                yield raw.rstrip(b"\r").decode("utf-8")
            except UnicodeDecodeError:
                raise ValueError("Model stream contains invalid UTF-8") from None
        if len(pending) > 100000:
            raise ValueError("Model stream line exceeds 100 KB")
    if pending:
        try:
            yield pending.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("Model stream contains invalid UTF-8") from None
