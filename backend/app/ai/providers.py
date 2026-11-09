"""AI providers (26 Oct 2026): any provider, API key and model.

Two kinds of connection cover nearly every provider:
- "anthropic": Anthropic's own API (Claude), with prompt caching.
- "openai": the OpenAI Chat Completions format, which OpenAI, Google Gemini, Azure OpenAI, Groq,
  DeepSeek, Mistral, OpenRouter, xAI, Together and local servers (Ollama, LM Studio) all accept.

The Provider field is free text. A known name (or an alias such as "claude" or "google") fills in
the base URL; anything else is treated as an OpenAI-compatible service and needs a base URL.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

PRESETS: dict[str, dict] = {
    "anthropic": {"label": "Anthropic (Claude)", "kind": "anthropic", "base_url": "https://api.anthropic.com",
                  "aliases": ["claude", "anthropic claude"], "model_hint": "claude-sonnet-5-5", "key_hint": "sk-ant-…"},
    "openai": {"label": "OpenAI", "kind": "openai", "base_url": "https://api.openai.com/v1",
               "aliases": ["chatgpt", "gpt", "open ai"], "model_hint": "gpt-5", "key_hint": "sk-…"},
    "gemini": {"label": "Google Gemini", "kind": "openai", "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
               "aliases": ["google", "google gemini", "google ai"], "model_hint": "gemini-2.5-pro", "key_hint": "AIza…"},
    "azure": {"label": "Azure OpenAI", "kind": "openai", "base_url": "", "auth": "api-key",
              "aliases": ["azure openai", "microsoft", "azure ai"], "model_hint": "your deployment name",
              "key_hint": "Azure key", "base_url_hint": "https://<resource>.openai.azure.com/openai/v1"},
    "groq": {"label": "Groq", "kind": "openai", "base_url": "https://api.groq.com/openai/v1", "aliases": [], "model_hint": "llama-3.3-70b-versatile", "key_hint": "gsk_…"},
    "deepseek": {"label": "DeepSeek", "kind": "openai", "base_url": "https://api.deepseek.com/v1", "aliases": [], "model_hint": "deepseek-chat", "key_hint": "sk-…"},
    "mistral": {"label": "Mistral", "kind": "openai", "base_url": "https://api.mistral.ai/v1", "aliases": ["mistral ai"], "model_hint": "mistral-large-latest", "key_hint": ""},
    "openrouter": {"label": "OpenRouter", "kind": "openai", "base_url": "https://openrouter.ai/api/v1", "aliases": [], "model_hint": "anthropic/claude-sonnet-4.5", "key_hint": "sk-or-…"},
    "xai": {"label": "xAI (Grok)", "kind": "openai", "base_url": "https://api.x.ai/v1", "aliases": ["grok", "x.ai"], "model_hint": "grok-4", "key_hint": "xai-…"},
    "together": {"label": "Together AI", "kind": "openai", "base_url": "https://api.together.xyz/v1", "aliases": ["together ai"], "model_hint": "", "key_hint": ""},
    "ollama": {"label": "Ollama (your own server)", "kind": "openai", "base_url": "http://localhost:11434/v1", "aliases": ["local"], "model_hint": "llama3.1", "key_hint": "any text"},
}

# Context window and longest answer (plus published prices, kept for reference) for models nowBuilder knows,
# used when the provider does not report them. The usage view counts credits, not money.
# Matched by the longest prefix of the model name, so dated names (claude-sonnet-4-20250514) match.
MODEL_CATALOG: dict[str, dict] = {
    "claude-opus-4-5": {"input": 5.0, "output": 25.0, "context": 200_000, "max_output": 64_000},
    "claude-opus-4-1": {"input": 15.0, "output": 75.0, "context": 200_000, "max_output": 32_000},
    "claude-opus-4": {"input": 15.0, "output": 75.0, "context": 200_000, "max_output": 32_000},
    "claude-sonnet-4-5": {"input": 3.0, "output": 15.0, "context": 200_000, "max_output": 64_000},
    "claude-sonnet-4": {"input": 3.0, "output": 15.0, "context": 200_000, "max_output": 64_000},
    "claude-haiku-4-5": {"input": 1.0, "output": 5.0, "context": 200_000, "max_output": 64_000},
    "claude-3-5-haiku": {"input": 0.8, "output": 4.0, "context": 200_000, "max_output": 8_192},
    "gpt-5-mini": {"input": 0.25, "output": 2.0, "context": 400_000, "max_output": 128_000},
    "gpt-5": {"input": 1.25, "output": 10.0, "context": 400_000, "max_output": 128_000},
    "gpt-4.1-mini": {"input": 0.4, "output": 1.6, "context": 1_047_576, "max_output": 32_768},
    "gpt-4.1": {"input": 2.0, "output": 8.0, "context": 1_047_576, "max_output": 32_768},
    "gpt-4o-mini": {"input": 0.15, "output": 0.6, "context": 128_000, "max_output": 16_384},
    "gpt-4o": {"input": 2.5, "output": 10.0, "context": 128_000, "max_output": 16_384},
    "gemini-2.5-flash": {"input": 0.3, "output": 2.5, "context": 1_048_576, "max_output": 65_536},
    "gemini-2.5-pro": {"input": 1.25, "output": 10.0, "context": 1_048_576, "max_output": 65_536},
}


# AI credits (owner, 26 Oct 2026: show credit consumption, not money; no allowance, since an API
# key is pay-as-you-go and has no monthly credits).
TOKENS_PER_CREDIT = 1000      # 1 credit = 1,000 tokens read or written by the model
CACHE_READ_WEIGHT = 0.1       # re-read (cached) prompt tokens count 10%


def credits_for(usage: dict) -> float:
    """Credits used by one model call."""
    t = (usage.get("input", 0) + usage.get("output", 0) + usage.get("cache_write", 0)
         + usage.get("cache_read", 0) * CACHE_READ_WEIGHT)
    return round(t / TOKENS_PER_CREDIT, 3)


@dataclass
class Resolved:
    key: str            # preset key, or "custom"
    label: str          # what the page shows
    kind: str           # "anthropic" | "openai"
    base_url: str       # "" = the provider's default (Anthropic)
    auth: str = "bearer"


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9.]+", " ", (s or "").lower()).strip()


def find_preset(provider: str) -> str | None:
    p = _norm(provider)
    for key, pre in PRESETS.items():
        if p in (key, _norm(pre["label"]), *(_norm(a) for a in pre["aliases"])):
            return key
    return None


def resolve(provider: str, base_url: str | None) -> Resolved:
    """What to connect to for a provider name typed by the user (+ optional base URL)."""
    url = (base_url or "").strip().rstrip("/")
    key = find_preset(provider)
    if key:
        pre = PRESETS[key]
        return Resolved(key, pre["label"], pre["kind"], url or pre["base_url"].rstrip("/"), pre.get("auth", "bearer"))
    name = (provider or "").strip() or "Custom provider"
    return Resolved("custom", name, "openai", url)


def model_catalog(model: str) -> dict | None:
    m = (model or "").lower().strip()
    m = m.split("/")[-1]  # OpenRouter-style "anthropic/claude-…"
    m = m.replace(".", "-") if m.startswith("claude") else m
    best = None
    for prefix in MODEL_CATALOG:
        if m.startswith(prefix) and (best is None or len(prefix) > len(best)):
            best = prefix
    return dict(MODEL_CATALOG[best], matched=best) if best else None


def options() -> list[dict]:
    return [{"key": k, "label": p["label"], "aliases": p["aliases"], "kind": p["kind"], "base_url": p["base_url"], "model_hint": p["model_hint"],
             "key_hint": p["key_hint"], "base_url_hint": p.get("base_url_hint", ""), "needs_base_url": not p["base_url"]}
            for k, p in PRESETS.items()]
