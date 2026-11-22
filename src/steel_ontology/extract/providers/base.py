"""The provider contract: one structured completion call.

Everything the package asks of a language model goes through ``Provider.complete``: a system
text, a user prompt, optional page images and a JSON Schema the answer must follow. The answer
comes back as JSON text. Keeping the contract this small is what lets five very different back
ends (three vendor SDKs, a local server and a replay of stored answers) sit behind it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


class ProviderError(RuntimeError):
    """A provider could not produce an answer (missing SDK or key, refusal, bad response)."""


@dataclass(frozen=True)
class Request:
    """One call to a model.

    ``key`` names the call in a stable way (``page-001``, ``ask-3f2a...``). The recorded provider
    replays by it, and ``--save-responses`` stores answers under it. ``images`` are PNG bytes.
    The schema uses only what every provider's structured-output mode accepts: objects with all
    properties required and ``additionalProperties: false``, arrays, strings, enums, ``anyOf``.
    """

    key: str
    system: str
    prompt: str
    schema: dict[str, Any]
    schema_name: str
    images: tuple[bytes, ...] = ()


@runtime_checkable
class Provider(Protocol):
    """A model back end. ``name`` is the registry name, ``model`` the model id in use.

    A provider whose API may answer with another model than ``model`` (the Anthropic refusal
    fallback) also sets ``last_model`` after each call; callers read it with ``getattr`` and
    fall back to ``model``.
    """

    name: str
    model: str

    def complete(self, request: Request) -> str:
        """Return JSON text that follows ``request.schema``; raise ``ProviderError`` otherwise."""
        ...


def parse_json(text: str, provider: str) -> dict[str, Any]:
    """Parse a provider's answer; a non-object or invalid JSON is a ``ProviderError``."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise ProviderError(f"{provider} returned text that is not JSON: {error}") from error
    if not isinstance(data, dict):
        raise ProviderError(f"{provider} returned JSON that is not an object")
    return data


def missing_sdk(provider: str, extra: str) -> ProviderError:
    """The error raised when a provider's optional SDK is not installed."""
    return ProviderError(
        f"the {provider} provider needs its SDK: "
        f"pip install 'steel-drawing-ontology[{extra}]' (or: uv sync --extra {extra})"
    )
