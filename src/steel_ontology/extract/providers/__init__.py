"""Model providers behind one small contract (see ``base.Provider``).

``get_provider`` builds one by name. SDK imports happen inside each provider's constructor, so
importing this package never needs an optional dependency.
"""

from __future__ import annotations

import os
from pathlib import Path

from steel_ontology.extract.providers.anthropic import AnthropicProvider
from steel_ontology.extract.providers.base import Provider, ProviderError, Request
from steel_ontology.extract.providers.gemini import GeminiProvider
from steel_ontology.extract.providers.local import LocalProvider
from steel_ontology.extract.providers.openai import OpenAIProvider
from steel_ontology.extract.providers.recorded import RecordedProvider

PROVIDER_ENV = "STEEL_ONTOLOGY_PROVIDER"
PROVIDERS = ("anthropic", "openai", "gemini", "local", "recorded")


def get_provider(
    name: str | None = None,
    *,
    model: str | None = None,
    recorded: str | Path | None = None,
    refusal_fallback: bool | None = None,
) -> Provider:
    """Build the provider called ``name`` (default: ``$STEEL_ONTOLOGY_PROVIDER``).

    ``model`` overrides the provider's default model id. ``recorded`` is the folder of stored
    answers and is required for (and only used by) the ``recorded`` provider.
    ``refusal_fallback`` turns the Anthropic server-side refusal fallback on (``None``: read
    ``STEEL_ONTOLOGY_ANTHROPIC_FALLBACKS``); other providers ignore it.
    """
    name = name or os.environ.get(PROVIDER_ENV)
    if not name:
        raise ProviderError(f"no provider chosen: pass one of {', '.join(PROVIDERS)}")
    if name == "recorded":
        if recorded is None:
            raise ProviderError("the recorded provider needs the folder of stored answers")
        return RecordedProvider(recorded)
    if name == "anthropic":
        return AnthropicProvider(model, refusal_fallback=refusal_fallback)
    if name == "openai":
        return OpenAIProvider(model)
    if name == "gemini":
        return GeminiProvider(model)
    if name == "local":
        return LocalProvider(model)
    raise ProviderError(f"unknown provider {name!r}: choose one of {', '.join(PROVIDERS)}")


__all__ = [
    "PROVIDERS",
    "AnthropicProvider",
    "GeminiProvider",
    "LocalProvider",
    "OpenAIProvider",
    "Provider",
    "ProviderError",
    "RecordedProvider",
    "Request",
    "get_provider",
]
