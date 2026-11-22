"""OpenAI models through the official ``openai`` SDK (optional extra ``openai``).

Uses Chat Completions with image inputs as data URLs and a strict ``json_schema`` response
format. Credentials come from ``OPENAI_API_KEY``.

Not verified locally: no API key was available when this was written. The default model id is
a guess that the reader should check; override it with ``--model`` or the environment variable.
"""

from __future__ import annotations

import base64
import os
from typing import Any

from steel_ontology.extract.providers.base import ProviderError, Request, missing_sdk

DEFAULT_MODEL = "gpt-5"
MODEL_ENV = "STEEL_ONTOLOGY_OPENAI_MODEL"


def chat_messages(request: Request) -> list[dict[str, Any]]:
    """The request as OpenAI-style chat messages (also used by the local provider)."""
    content: list[dict[str, Any]] = [{"type": "text", "text": request.prompt}]
    for image in request.images:
        encoded = base64.standard_b64encode(image).decode("ascii")
        content.append(
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}}
        )
    return [
        {"role": "system", "content": request.system},
        {"role": "user", "content": content},
    ]


def response_format(request: Request) -> dict[str, Any]:
    """The strict structured-output setting (also used by the local provider)."""
    return {
        "type": "json_schema",
        "json_schema": {"name": request.schema_name, "strict": True, "schema": request.schema},
    }


class OpenAIProvider:
    """Structured extraction with an OpenAI vision model."""

    name = "openai"

    def __init__(self, model: str | None = None, *, client: Any = None) -> None:
        try:
            import openai
        except ImportError as error:
            raise missing_sdk("openai", "openai") from error
        self._sdk = openai
        self.model = model or os.environ.get(MODEL_ENV) or DEFAULT_MODEL
        try:
            self._client = client if client is not None else openai.OpenAI()
        except openai.OpenAIError as error:
            raise ProviderError(f"openai: {error}") from error

    def complete(self, request: Request) -> str:
        sdk = self._sdk
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=chat_messages(request),
                response_format=response_format(request),
            )
        except sdk.AuthenticationError as error:
            raise ProviderError("openai: no valid credentials (set OPENAI_API_KEY)") from error
        except sdk.RateLimitError as error:
            raise ProviderError("openai: rate limited after the SDK's retries") from error
        except sdk.APIStatusError as error:
            raise ProviderError(f"openai: API error {error.status_code}: {error}") from error
        except sdk.APIConnectionError as error:
            raise ProviderError(f"openai: could not reach the API: {error}") from error
        choice = response.choices[0]
        if getattr(choice.message, "refusal", None):
            raise ProviderError(f"openai: the model declined the request ({request.key})")
        if choice.finish_reason == "length":
            raise ProviderError(f"openai: the answer for {request.key} was cut off")
        if not choice.message.content:
            raise ProviderError(f"openai: empty answer for {request.key}")
        return choice.message.content
