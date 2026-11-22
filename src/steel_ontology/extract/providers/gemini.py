"""Gemini through the ``google-genai`` SDK (optional extra ``gemini``).

Page images go in as inline PNG parts; the answer is constrained with a JSON response schema.
Credentials come from ``GEMINI_API_KEY`` (or ``GOOGLE_API_KEY``).

Not verified locally: no API key was available when this was written.
"""

from __future__ import annotations

import os
from typing import Any

from steel_ontology.extract.providers.base import ProviderError, Request, missing_sdk

DEFAULT_MODEL = "gemini-2.5-flash"
MODEL_ENV = "STEEL_ONTOLOGY_GEMINI_MODEL"


class GeminiProvider:
    """Structured extraction with a Gemini model."""

    name = "gemini"

    def __init__(self, model: str | None = None, *, client: Any = None) -> None:
        try:
            from google import genai
            from google.genai import errors, types
        except ImportError as error:
            raise missing_sdk("gemini", "gemini") from error
        self._types = types
        self._errors = errors
        self.model = model or os.environ.get(MODEL_ENV) or DEFAULT_MODEL
        try:
            self._client = client if client is not None else genai.Client()
        except ValueError as error:
            raise ProviderError(f"gemini: {error} (set GEMINI_API_KEY)") from error

    def complete(self, request: Request) -> str:
        types = self._types
        parts = [
            types.Part.from_bytes(data=image, mime_type="image/png") for image in request.images
        ]
        config = types.GenerateContentConfig(
            system_instruction=request.system,
            response_mime_type="application/json",
            response_json_schema=request.schema,
        )
        try:
            response = self._client.models.generate_content(
                model=self.model, contents=[*parts, request.prompt], config=config
            )
        except self._errors.APIError as error:
            raise ProviderError(f"gemini: API error {error.code}: {error.message}") from error
        if not response.text:
            raise ProviderError(f"gemini: empty answer for {request.key}")
        return response.text
