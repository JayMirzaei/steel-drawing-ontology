"""A local OpenAI-compatible server (llama.cpp ``llama-server``, Ollama, vLLM, LM Studio).

Plain HTTP with the standard library, so this provider needs no SDK and no key. The server must
serve a vision model and support ``response_format`` with a JSON schema.

Not verified locally against a running server; the request is tested with mocked HTTP.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from steel_ontology.extract.providers.base import ProviderError, Request
from steel_ontology.extract.providers.openai import chat_messages, response_format

DEFAULT_URL = "http://localhost:8080/v1"
URL_ENV = "STEEL_ONTOLOGY_LOCAL_URL"
MODEL_ENV = "STEEL_ONTOLOGY_LOCAL_MODEL"
KEY_ENV = "STEEL_ONTOLOGY_LOCAL_API_KEY"
TIMEOUT_SECONDS = 600

Opener = Callable[..., Any]


class LocalProvider:
    """Structured extraction with a model served on this machine or network.

    ``opener`` is ``urllib.request.urlopen`` unless a test passes a stand-in.
    """

    name = "local"

    def __init__(
        self,
        model: str | None = None,
        *,
        base_url: str | None = None,
        opener: Opener = urllib.request.urlopen,
    ) -> None:
        self.model = model or os.environ.get(MODEL_ENV) or "local-model"
        self.base_url = (base_url or os.environ.get(URL_ENV) or DEFAULT_URL).rstrip("/")
        if not self.base_url.startswith(("http://", "https://")):
            raise ProviderError(f"local: {self.base_url!r} is not an http(s) URL")
        self._opener = opener

    def complete(self, request: Request) -> str:
        body = {
            "model": self.model,
            "messages": chat_messages(request),
            "response_format": response_format(request),
        }
        headers = {"Content-Type": "application/json"}
        if os.environ.get(KEY_ENV):
            headers["Authorization"] = f"Bearer {os.environ[KEY_ENV]}"
        http_request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with self._opener(http_request, timeout=TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            raise ProviderError(f"local: server answered HTTP {error.code}") from error
        except (urllib.error.URLError, TimeoutError) as error:
            raise ProviderError(f"local: could not reach {self.base_url}: {error}") from error
        except json.JSONDecodeError as error:
            raise ProviderError("local: the server's reply is not JSON") from error
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise ProviderError("local: the reply has no choices[0].message.content") from error
        if not content:
            raise ProviderError(f"local: empty answer for {request.key}")
        return content
