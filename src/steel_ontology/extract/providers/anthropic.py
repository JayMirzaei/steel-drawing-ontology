"""Claude through the official ``anthropic`` SDK (optional extra ``anthropic``).

Page images go in as base64 image blocks, the answer is constrained with structured outputs
(``output_config.format``), and the response is streamed so a long sheet does not hit an HTTP
timeout. Credentials are resolved by the SDK (``ANTHROPIC_API_KEY`` or a login profile).

The API's server-side refusal fallback is off unless asked for (``refusal_fallback=True``,
``--refusal-fallback`` or ``STEEL_ONTOLOGY_ANTHROPIC_FALLBACKS=1``): when it is on, a model other
than the one chosen may answer, and ``last_model`` then names the model that actually did.

Not verified locally: no API key was available when this was written. The request shape is
tested against a mocked client only.
"""

from __future__ import annotations

import base64
import os
from typing import Any

from steel_ontology.extract.providers.base import ProviderError, Request, missing_sdk

DEFAULT_MODEL = "claude-opus-5-5"
MODEL_ENV = "STEEL_ONTOLOGY_ANTHROPIC_MODEL"
FALLBACK_ENV = "STEEL_ONTOLOGY_ANTHROPIC_FALLBACKS"
FALLBACK_BETA = "server-side-fallback-2026-07-01"
MAX_TOKENS = 64000
NO_CREDENTIALS = "anthropic: no credentials found (set ANTHROPIC_API_KEY)"


class AnthropicProvider:
    """Structured extraction with a Claude model.

    ``effort`` is set explicitly because reading a dense sheet is intelligence-sensitive and the
    default differs between models. ``refusal_fallback`` opts into the API's server-side
    fallback: if a safety classifier declines the request, the API re-runs it on the fallback
    model it recommends instead of returning a refusal. It is off by default, because the answer
    would then come from a model the user did not choose; ``None`` reads
    ``STEEL_ONTOLOGY_ANTHROPIC_FALLBACKS`` (``1`` turns it on). ``last_model`` is the model that
    produced the latest answer, as the API reports it.
    """

    name = "anthropic"

    def __init__(
        self,
        model: str | None = None,
        *,
        client: Any = None,
        effort: str = "high",
        refusal_fallback: bool | None = None,
    ) -> None:
        try:
            import anthropic
        except ImportError as error:
            raise missing_sdk("anthropic", "anthropic") from error
        self._sdk = anthropic
        self._client = client if client is not None else anthropic.Anthropic()
        self.model = model or os.environ.get(MODEL_ENV) or DEFAULT_MODEL
        self.effort = effort
        if refusal_fallback is None:
            refusal_fallback = os.environ.get(FALLBACK_ENV, "").strip() == "1"
        self.refusal_fallback = refusal_fallback
        self.last_model: str | None = None

    def complete(self, request: Request) -> str:
        content: list[dict[str, Any]] = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": base64.standard_b64encode(image).decode("ascii"),
                },
            }
            for image in request.images
        ]
        content.append({"type": "text", "text": request.prompt})
        arguments: dict[str, Any] = {
            "model": self.model,
            "max_tokens": MAX_TOKENS,
            # The system text (reading rules and field catalogue) is the same for every page, so
            # it is marked for prompt caching: later pages read it from the cache.
            "system": [
                {"type": "text", "text": request.system, "cache_control": {"type": "ephemeral"}}
            ],
            "messages": [{"role": "user", "content": content}],
            "thinking": {"type": "adaptive"},
            "output_config": {
                "effort": self.effort,
                "format": {"type": "json_schema", "schema": request.schema},
            },
        }
        if self.refusal_fallback:
            arguments["betas"] = [FALLBACK_BETA]
            arguments["fallbacks"] = "default"
        message = self._send(arguments)
        self.last_model = getattr(message, "model", None) or self.model
        if message.stop_reason == "refusal":
            raise ProviderError(f"anthropic: the model declined the request ({request.key})")
        if message.stop_reason == "max_tokens":
            raise ProviderError(
                f"anthropic: the answer for {request.key} was cut off at {MAX_TOKENS} tokens"
            )
        # After a mid-answer fallback the answer is split at a ``fallback`` block: the partial
        # text and its continuation together are the answer.
        text = "".join(block.text for block in message.content if block.type == "text")
        if text:
            return text
        raise ProviderError(f"anthropic: no text block in the answer for {request.key}")

    def _send(self, arguments: dict[str, Any]) -> Any:
        sdk = self._sdk
        try:
            with self._client.beta.messages.stream(**arguments) as stream:
                return stream.get_final_message()
        except TypeError as error:
            # The SDK raises TypeError before sending when it finds no credentials at all.
            if "authentication" not in str(error).lower():
                raise
            raise ProviderError(NO_CREDENTIALS) from error
        except sdk.AuthenticationError as error:
            raise ProviderError(
                "anthropic: no valid credentials (set ANTHROPIC_API_KEY)"
            ) from error
        except sdk.RateLimitError as error:
            raise ProviderError("anthropic: rate limited after the SDK's retries") from error
        except sdk.APIStatusError as error:
            raise ProviderError(f"anthropic: API error {error.status_code}: {error}") from error
        except sdk.APIConnectionError as error:
            raise ProviderError(f"anthropic: could not reach the API: {error}") from error
