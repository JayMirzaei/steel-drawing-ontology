"""Model providers with mocked SDK clients and mocked HTTP. No network, no keys.

These tests pin the request each provider sends and how it reports failures. They cannot show
that a real API accepts the request: that needs a key.
"""

from __future__ import annotations

import base64
import io
import json
import sys
import urllib.error
from types import SimpleNamespace
from typing import Any

import anthropic
import httpx2
import openai
import pytest
from google.genai import errors as genai_errors

from steel_ontology.extract.providers import (
    PROVIDERS,
    AnthropicProvider,
    GeminiProvider,
    LocalProvider,
    OpenAIProvider,
    Provider,
    ProviderError,
    RecordedProvider,
    Request,
    get_provider,
)
from steel_ontology.extract.providers.base import parse_json

PNG = b"\x89PNG fake image bytes"
SCHEMA = {"type": "object", "additionalProperties": False, "required": [], "properties": {}}
REQUEST = Request("page-001", "system text", "user text", SCHEMA, "sheet_extraction", (PNG,))
ANSWER = '{"objects": []}'


def _http_error(sdk: Any, cls_name: str, status: int) -> Exception:
    request = httpx2.Request("POST", "https://api.invalid/v1")
    response = httpx2.Response(status, request=request)
    return getattr(sdk, cls_name)("nope", response=response, body=None)


# ---- Anthropic ------------------------------------------------------------------------------


class _Stream:
    def __init__(self, message: Any) -> None:
        self.message = message

    def __enter__(self) -> _Stream:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def get_final_message(self) -> Any:
        return self.message


class _AnthropicClient:
    """Stands in for ``anthropic.Anthropic``: records the call, returns or raises."""

    def __init__(
        self,
        stop_reason: str = "end_turn",
        error: Exception | None = None,
        model: str = "claude-opus-5-5",
        content: list[Any] | None = None,
    ) -> None:
        self.calls: list[dict[str, Any]] = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream))
        self._stop_reason = stop_reason
        self._error = error
        self._model = model
        self._content = content or [
            SimpleNamespace(type="thinking"),
            SimpleNamespace(type="text", text=ANSWER),
        ]

    def _stream(self, **arguments: Any) -> _Stream:
        self.calls.append(arguments)
        if self._error:
            raise self._error
        message = SimpleNamespace(
            stop_reason=self._stop_reason, content=self._content, model=self._model
        )
        return _Stream(message)


def test_anthropic_request_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STEEL_ONTOLOGY_ANTHROPIC_FALLBACKS", raising=False)
    client = _AnthropicClient()
    provider = AnthropicProvider(client=client)
    assert isinstance(provider, Provider)
    assert provider.model == "claude-opus-5-5"
    assert provider.complete(REQUEST) == ANSWER
    (call,) = client.calls
    assert call["model"] == "claude-opus-5-5"
    # The shared system text is marked for prompt caching.
    assert call["system"] == [
        {"type": "text", "text": "system text", "cache_control": {"type": "ephemeral"}}
    ]
    assert call["thinking"] == {"type": "adaptive"}
    assert call["output_config"] == {
        "effort": "high",
        "format": {"type": "json_schema", "schema": SCHEMA},
    }
    # The refusal fallback is off unless asked for: the user chose this model.
    assert "fallbacks" not in call and "betas" not in call
    assert provider.last_model == "claude-opus-5-5"
    image, text = call["messages"][0]["content"]
    assert image["source"]["media_type"] == "image/png"
    assert base64.standard_b64decode(image["source"]["data"]) == PNG
    assert text == {"type": "text", "text": "user text"}
    assert "temperature" not in call and "tool_choice" not in call


def test_anthropic_options(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STEEL_ONTOLOGY_ANTHROPIC_MODEL", "claude-sonnet-5-5")
    client = _AnthropicClient()
    provider = AnthropicProvider(client=client, refusal_fallback=True, effort="low")
    provider.complete(REQUEST)
    assert provider.model == "claude-sonnet-5-5"
    call = client.calls[0]
    assert (call["betas"], call["fallbacks"]) == (["server-side-fallback-2026-07-01"], "default")
    assert call["output_config"]["effort"] == "low"
    assert AnthropicProvider("claude-haiku-5-5", client=client).model == "claude-haiku-5-5"


@pytest.mark.parametrize(("value", "expected"), [("1", True), ("0", False), ("", False)])
def test_anthropic_fallback_can_be_turned_on_by_environment(
    monkeypatch: pytest.MonkeyPatch, value: str, expected: bool
) -> None:
    monkeypatch.setenv("STEEL_ONTOLOGY_ANTHROPIC_FALLBACKS", value)
    assert AnthropicProvider(client=_AnthropicClient()).refusal_fallback is expected
    assert AnthropicProvider(
        client=_AnthropicClient(), refusal_fallback=False
    ).refusal_fallback is (False)
    provider = get_provider("anthropic", refusal_fallback=True)
    assert provider.refusal_fallback is True


def test_anthropic_records_the_model_that_actually_answered() -> None:
    fallback = SimpleNamespace(
        type="fallback",
        from_=SimpleNamespace(model="claude-opus-5-5"),
        to=SimpleNamespace(model="claude-opus-4-8"),
    )
    content = [
        SimpleNamespace(type="text", text='{"objects": '),
        fallback,
        SimpleNamespace(type="text", text="[]}"),
    ]
    client = _AnthropicClient(model="claude-opus-4-8", content=content)
    provider = AnthropicProvider(client=client, refusal_fallback=True)
    assert provider.complete(REQUEST) == ANSWER  # the partial and its continuation, joined
    assert (provider.model, provider.last_model) == ("claude-opus-5-5", "claude-opus-4-8")


def test_anthropic_without_any_credentials_is_a_provider_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    """The SDK raises TypeError before sending when it finds no credentials at all."""
    for name in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_PROFILE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))  # no login profile on disk either
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    with pytest.raises(ProviderError, match="no credentials found"):
        AnthropicProvider().complete(REQUEST)


def test_anthropic_does_not_hide_other_type_errors() -> None:
    client = _AnthropicClient(error=TypeError("stream() got an unexpected keyword argument"))
    with pytest.raises(TypeError, match="unexpected keyword"):
        AnthropicProvider(client=client).complete(REQUEST)


@pytest.mark.parametrize(
    ("client", "message"),
    [
        (_AnthropicClient(stop_reason="refusal"), "declined"),
        (_AnthropicClient(stop_reason="max_tokens"), "cut off"),
        (_AnthropicClient(error=_http_error(anthropic, "AuthenticationError", 401)), "credentials"),
        (_AnthropicClient(error=_http_error(anthropic, "RateLimitError", 429)), "rate limited"),
        (_AnthropicClient(error=_http_error(anthropic, "InternalServerError", 500)), "error 500"),
        (
            _AnthropicClient(
                error=anthropic.APIConnectionError(request=httpx2.Request("POST", "https://x"))
            ),
            "could not reach",
        ),
    ],
)
def test_anthropic_failures_become_provider_errors(client: _AnthropicClient, message: str) -> None:
    with pytest.raises(ProviderError, match=message):
        AnthropicProvider(client=client).complete(REQUEST)


# ---- OpenAI ---------------------------------------------------------------------------------


class _OpenAIClient:
    def __init__(self, message: Any = None, finish: str = "stop", error: Exception | None = None):
        self.calls: list[dict[str, Any]] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))
        self._message = message or SimpleNamespace(content=ANSWER, refusal=None)
        self._finish = finish
        self._error = error

    def _create(self, **arguments: Any) -> Any:
        self.calls.append(arguments)
        if self._error:
            raise self._error
        choice = SimpleNamespace(message=self._message, finish_reason=self._finish)
        return SimpleNamespace(choices=[choice])


def test_openai_request_shape() -> None:
    client = _OpenAIClient()
    provider = OpenAIProvider("some-model", client=client)
    assert provider.complete(REQUEST) == ANSWER
    (call,) = client.calls
    assert call["model"] == "some-model"
    assert call["response_format"] == {
        "type": "json_schema",
        "json_schema": {"name": "sheet_extraction", "strict": True, "schema": SCHEMA},
    }
    system, user = call["messages"]
    assert system == {"role": "system", "content": "system text"}
    text, image = user["content"]
    assert text == {"type": "text", "text": "user text"}
    encoded = base64.standard_b64encode(PNG).decode()
    assert image["image_url"]["url"] == f"data:image/png;base64,{encoded}"


@pytest.mark.parametrize(
    ("client", "message"),
    [
        (_OpenAIClient(message=SimpleNamespace(content=None, refusal="no")), "declined"),
        (_OpenAIClient(finish="length"), "cut off"),
        (_OpenAIClient(message=SimpleNamespace(content="", refusal=None)), "empty answer"),
        (_OpenAIClient(error=_http_error(openai, "AuthenticationError", 401)), "credentials"),
        (_OpenAIClient(error=_http_error(openai, "RateLimitError", 429)), "rate limited"),
        (_OpenAIClient(error=_http_error(openai, "InternalServerError", 503)), "error 503"),
    ],
)
def test_openai_failures_become_provider_errors(client: _OpenAIClient, message: str) -> None:
    with pytest.raises(ProviderError, match=message):
        OpenAIProvider(client=client).complete(REQUEST)


def test_openai_without_a_key_is_a_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ProviderError, match="api_key"):
        OpenAIProvider()


# ---- Gemini ---------------------------------------------------------------------------------


class _GeminiClient:
    def __init__(self, text: str | None = ANSWER, error: Exception | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.models = SimpleNamespace(generate_content=self._generate)
        self._text = text
        self._error = error

    def _generate(self, **arguments: Any) -> Any:
        self.calls.append(arguments)
        if self._error:
            raise self._error
        return SimpleNamespace(text=self._text)


def test_gemini_request_shape() -> None:
    client = _GeminiClient()
    provider = GeminiProvider(client=client)
    assert provider.complete(REQUEST) == ANSWER
    (call,) = client.calls
    assert call["model"] == "gemini-2.5-flash"
    image, text = call["contents"]
    assert (image.inline_data.data, image.inline_data.mime_type) == (PNG, "image/png")
    assert text == "user text"
    config = call["config"]
    assert config.system_instruction == "system text"
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema == SCHEMA


def test_gemini_failures_become_provider_errors() -> None:
    with pytest.raises(ProviderError, match="empty answer"):
        GeminiProvider(client=_GeminiClient(text=None)).complete(REQUEST)
    error = genai_errors.APIError(429, {"error": {"message": "quota", "status": "EXHAUSTED"}})
    with pytest.raises(ProviderError, match="API error 429: quota"):
        GeminiProvider(client=_GeminiClient(error=error)).complete(REQUEST)


# ---- local OpenAI-compatible server ---------------------------------------------------------


class _Reply(io.BytesIO):
    def __enter__(self) -> _Reply:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


def test_local_posts_a_chat_completion(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STEEL_ONTOLOGY_LOCAL_API_KEY", "secret")
    seen: dict[str, Any] = {}

    def opener(http_request: Any, timeout: float) -> _Reply:
        seen.update(
            url=http_request.full_url,
            method=http_request.get_method(),
            headers=dict(http_request.header_items()),
            body=json.loads(http_request.data),
            timeout=timeout,
        )
        reply = {"choices": [{"message": {"content": ANSWER}}]}
        return _Reply(json.dumps(reply).encode())

    provider = LocalProvider("llava", base_url="http://localhost:11434/v1/", opener=opener)
    assert provider.complete(REQUEST) == ANSWER
    assert (seen["url"], seen["method"]) == ("http://localhost:11434/v1/chat/completions", "POST")
    assert seen["headers"]["Authorization"] == "Bearer secret"
    assert seen["body"]["model"] == "llava"
    assert seen["body"]["response_format"]["json_schema"]["schema"] == SCHEMA
    assert seen["body"]["messages"][1]["content"][1]["type"] == "image_url"
    assert seen["timeout"] == 600


def _raising(error: Exception):
    def opener(http_request: Any, timeout: float) -> _Reply:
        raise error

    return opener


@pytest.mark.parametrize(
    ("opener", "message"),
    [
        (_raising(urllib.error.URLError("refused")), "could not reach http://localhost:8080/v1"),
        (_raising(urllib.error.HTTPError("u", 500, "x", {}, None)), "HTTP 500"),
        (lambda request, timeout: _Reply(b"<html>"), "not JSON"),
        (lambda request, timeout: _Reply(b'{"choices": []}'), "no choices"),
        (lambda request, timeout: _Reply(b'{"choices": [{"message": {"content": ""}}]}'), "empty"),
    ],
)
def test_local_failures_become_provider_errors(opener: Any, message: str) -> None:
    with pytest.raises(ProviderError, match=message):
        LocalProvider(opener=opener).complete(REQUEST)


def test_local_refuses_a_non_http_url() -> None:
    with pytest.raises(ProviderError, match="not an http"):
        LocalProvider(base_url="file:///etc/passwd")


# ---- recorded and the registry --------------------------------------------------------------


def test_recorded_replays_by_request_key(tmp_path) -> None:
    (tmp_path / "page-001.json").write_text(ANSWER, encoding="utf-8")
    provider = RecordedProvider(tmp_path)
    assert provider.complete(REQUEST) == ANSWER
    with pytest.raises(ProviderError, match="no stored answer for 'page-009'"):
        provider.complete(Request("page-009", "", "", SCHEMA, "x"))
    with pytest.raises(ProviderError, match="is not a folder"):
        RecordedProvider(tmp_path / "missing")


def test_registry(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert PROVIDERS == ("anthropic", "openai", "gemini", "local", "recorded")
    assert get_provider("recorded", recorded=tmp_path).name == "recorded"
    assert get_provider("local", model="m").model == "m"
    monkeypatch.setenv("STEEL_ONTOLOGY_PROVIDER", "local")
    assert get_provider().name == "local"
    monkeypatch.delenv("STEEL_ONTOLOGY_PROVIDER")
    for arguments, message in (
        ({}, "no provider chosen"),
        ({"name": "recorded"}, "needs the folder"),
        ({"name": "llamacorp"}, "unknown provider"),
    ):
        with pytest.raises(ProviderError, match=message):
            get_provider(**arguments)


@pytest.mark.parametrize(
    ("module", "cls", "extra"),
    [
        ("anthropic", AnthropicProvider, "anthropic"),
        ("openai", OpenAIProvider, "openai"),
        ("google.genai", GeminiProvider, "gemini"),
    ],
)
def test_a_missing_sdk_names_the_extra_to_install(
    monkeypatch: pytest.MonkeyPatch, module: str, cls: type, extra: str
) -> None:
    monkeypatch.setitem(sys.modules, module, None)
    if module == "google.genai":
        monkeypatch.setitem(sys.modules, "google", None)
    with pytest.raises(ProviderError, match=rf"steel-drawing-ontology\[{extra}\]"):
        cls()


def test_parse_json_refuses_non_objects() -> None:
    assert parse_json('{"a": 1}', "x") == {"a": 1}
    for text in ("[1]", "nope"):
        with pytest.raises(ProviderError):
            parse_json(text, "x")
