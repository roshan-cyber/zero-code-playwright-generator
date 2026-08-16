"""Dynamic LLM client router for multiple providers."""
from __future__ import annotations

import os
from typing import Optional

from openai import AsyncOpenAI


def _get_api_key(provider: str, user_api_key: Optional[str]) -> str:
    """Return the API key to use: user supplied key takes precedence, otherwise env var."""
    if user_api_key:
        return user_api_key
    # Fallback to environment variables per provider
    env_map = {
        "NVIDIA NIM": "NVIDIA_API_KEY",
        "OpenRouter": "OPENROUTER_API_KEY",
        "OpenAI": "OPENAI_API_KEY",
        "Anthropic": "ANTHROPIC_API_KEY",
    }
    env_var = env_map.get(provider)
    if env_var:
        key = os.environ.get(env_var)
        if key:
            return key
    raise RuntimeError(f"API key for provider '{provider}' not found. Set {env_var} or provide user_api_key.")


def _get_base_url(provider: str) -> str:
    """Base URL for the provider's OpenAI‑compatible endpoint."""
    urls = {
        "NVIDIA NIM": "https://integrate.api.nvidia.com/v1",
        "OpenRouter": "https://openrouter.ai/api/v1",
        "OpenAI": "https://api.openai.com/v1",
        "Anthropic": "https://api.anthropic.com/v1",  # Anthropic also offers OpenAI‑compatible endpoint
    }
    return urls.get(provider, "https://api.openai.com/v1")


def _extra_headers(provider: str, api_key: str) -> dict:
    """Additional headers required by some providers (e.g., OpenRouter)."""
    if provider == "OpenRouter":
        return {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://zero-code-playwright.example",
            "X-Title": "Zero‑Code Playwright Generator",
        }
    # For other providers the Authorization header is handled by the client automatically.
    return {}


def _should_enable_reasoning(model: str) -> bool:
    """Enable reasoning / thinking budget only for Nemotron models."""
    return "nemotron" in model.lower()


def create_async_client(provider: str, model: str, user_api_key: Optional[str] = None) -> AsyncOpenAI:
    """Create an AsyncOpenAI client configured for the given provider and model."""
    api_key = _get_api_key(provider, user_api_key)
    base_url = _get_base_url(provider)
    extra_headers = _extra_headers(provider, api_key)

    client = AsyncOpenAI(
        base_url=base_url,
        api_key=api_key,
        default_headers=extra_headers,
    )
    # Attach metadata for later use (reasoning flags)
    client._provider = provider
    client._model = model
    client._reasoning_enabled = _should_enable_reasoning(model)
    return client