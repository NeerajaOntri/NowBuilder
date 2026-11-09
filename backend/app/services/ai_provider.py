"""AI provider verification (Settings → AI provider → Save and verify), for any provider.

One tiny request (1 output token) proves the key, the model and the address work. The response's
rate-limit headers tell us this key's limits for that model, and the provider's model endpoint
(when it has one) tells us the context window and output limit; known models fill gaps from
`providers.MODEL_CATALOG`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import anthropic

from ..ai.providers import model_catalog, resolve

SUPPORTED_PROVIDERS = {"anthropic": "Anthropic (Claude)"}  # kept for older clients; see providers.PRESETS


@dataclass
class VerifyResult:
    ok: bool
    message: str
    limits: dict = field(default_factory=dict)       # this key's rate limits for the model (per minute)
    model_info: dict = field(default_factory=dict)   # context window, max output, display name


def _int(v) -> int | None:
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def rate_limits(headers) -> dict:
    """Per-minute limits from Anthropic's or OpenAI-style rate-limit headers."""
    h = {k.lower(): v for k, v in dict(headers or {}).items()}
    pairs = {
        "requests_per_minute": ("anthropic-ratelimit-requests-limit", "x-ratelimit-limit-requests"),
        "input_tokens_per_minute": ("anthropic-ratelimit-input-tokens-limit",),
        "output_tokens_per_minute": ("anthropic-ratelimit-output-tokens-limit",),
        "tokens_per_minute": ("anthropic-ratelimit-tokens-limit", "x-ratelimit-limit-tokens"),
    }
    out = {}
    for name, keys in pairs.items():
        for k in keys:
            n = _int(h.get(k))
            if n:
                out[name] = n
                break
    return out


def _info_from(data: dict) -> dict:
    """Context window / output limit from a provider's model description, whatever it calls them."""
    out = {}
    for k in ("context_window", "context_length", "max_input_tokens", "input_token_limit", "inputTokenLimit", "max_context_length"):
        if _int(data.get(k)):
            out["context"] = _int(data[k])
            break
    for k in ("max_output_tokens", "output_token_limit", "outputTokenLimit", "max_tokens", "max_completion_tokens"):
        if _int(data.get(k)):
            out["max_output"] = _int(data[k])
            break
    if data.get("display_name"):
        out["display_name"] = str(data["display_name"])[:80]
    return out


def model_info(model: str, found: dict | None = None) -> dict:
    info = {k: v for k, v in (model_catalog(model) or {}).items() if k in ("context", "max_output")}
    info.update({k: v for k, v in (found or {}).items() if v})
    if found and (found.get("context") or found.get("max_output")):
        info["source"] = "provider"
    elif info:
        info["source"] = "nowbuilder"
    return info


def verify(provider: str, api_key: str, model: str, base_url: str | None = None) -> VerifyResult:
    r = resolve(provider, base_url)
    if r.kind == "anthropic":
        return _verify_anthropic(api_key, model, r.base_url)
    if not r.base_url:
        return VerifyResult(False, f"{r.label} needs a base URL (the address of its OpenAI-compatible API).")
    return _verify_openai(r.label, api_key, model, r.base_url, r.auth)


def _verify_anthropic(api_key: str, model: str, base_url: str) -> VerifyResult:
    kw = {"base_url": base_url} if base_url and base_url != "https://api.anthropic.com" else {}
    client = anthropic.Anthropic(api_key=api_key, max_retries=0, timeout=30, **kw)
    try:
        raw = client.messages.with_raw_response.create(model=model, max_tokens=1, messages=[{"role": "user", "content": "ping"}])
        headers = raw.headers
    except anthropic.AuthenticationError:
        return VerifyResult(False, "The API key was rejected. Check that it's copied correctly and still active.")
    except anthropic.PermissionDeniedError:
        return VerifyResult(False, "This API key doesn't have access to that model.")
    except anthropic.NotFoundError:
        return VerifyResult(False, f"Model '{model}' wasn't found. Check the model name.")
    except anthropic.RateLimitError as e:
        return VerifyResult(True, "Key and model are valid (the provider is rate-limiting right now).",
                            rate_limits(getattr(getattr(e, "response", None), "headers", {})), model_info(model))
    except anthropic.APIConnectionError:
        return VerifyResult(False, "Couldn't reach the AI provider. Check your network and try again.")
    except anthropic.APIStatusError as e:
        return VerifyResult(False, f"The provider returned an error ({e.status_code}). Try again shortly.")
    found = {}
    try:
        m = client.models.retrieve(model)
        found = _info_from(m.model_dump() if hasattr(m, "model_dump") else dict(m))
    except Exception:  # noqa: BLE001  (limits are a nice-to-have)
        found = {}
    return VerifyResult(True, f"Connected. nowBuilder can use {model}.", rate_limits(headers), model_info(model, found))


def _verify_openai(label: str, api_key: str, model: str, base_url: str, auth: str, transport=None) -> VerifyResult:
    import httpx

    from ..ai.llm import OpenAICompatLLM, _http_error

    llm = OpenAICompatLLM(api_key, model, base_url, auth, transport=transport)
    body = {"model": model, "messages": [{"role": "user", "content": "ping"}]}
    try:
        with httpx.Client(timeout=httpx.Timeout(30, connect=15), transport=transport) as http:
            r = None
            for _ in range(3):
                body.pop("max_tokens", None)
                body.pop("max_completion_tokens", None)
                body[llm.max_param] = 16
                r = http.post(f"{base_url}/chat/completions", json=body, headers=llm.headers())
                if r.status_code == 400 and llm._adjust(400, r.text, 16) is not None:
                    continue
                break
            if r.status_code == 429:
                return VerifyResult(True, f"Key and model are valid ({label} is rate-limiting right now).", rate_limits(r.headers), model_info(model))
            if r.status_code >= 400:
                return VerifyResult(False, str(_http_error(r.status_code, r.text, model)).replace(" Update it in Settings → AI provider.", ""))
            headers = r.headers
            found = {}
            try:
                m = http.get(f"{base_url}/models/{model}", headers=llm.headers())
                if m.status_code == 200 and isinstance(m.json(), dict):
                    found = _info_from(m.json())
            except (httpx.HTTPError, ValueError):
                found = {}
    except httpx.HTTPError:
        return VerifyResult(False, f"Couldn't reach {label} at {base_url}. Check the base URL and your network.")
    return VerifyResult(True, f"Connected. nowBuilder can use {model} on {label}.", rate_limits(headers), model_info(model, found))
