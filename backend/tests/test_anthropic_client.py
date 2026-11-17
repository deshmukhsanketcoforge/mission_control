"""The real client is tested against a stub SDK object: no network, no API key."""

import asyncio
from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from app.llm.anthropic_client import AnthropicClient
from app.llm.base import LLMClient, LLMError, LLMRequest
from app.llm.models import FAST_MODEL

SCHEMA = {
    "type": "object",
    "properties": {"a": {"type": "string"}},
    "required": ["a"],
    "additionalProperties": False,
}


def message(text="hello", stop_reason="end_turn", model="claude-haiku-5-5", blocks=None):
    content = blocks if blocks is not None else [SimpleNamespace(type="text", text=text)]
    return SimpleNamespace(
        content=content,
        stop_reason=stop_reason,
        model=model,
        usage=SimpleNamespace(input_tokens=21, output_tokens=7),
    )


class StubSDK:
    """Looks like AsyncAnthropic: ``await sdk.messages.create(**kwargs)``."""

    def __init__(self, result=None, error=None):
        self.kwargs = None
        self._result, self._error = result, error
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kwargs):
        self.kwargs = kwargs
        if self._error:
            raise self._error
        return self._result


def request(**kw):
    return LLMRequest(step="sort", system="SYS", user="USER", **kw)


def call(sdk, **kw):
    return asyncio.run(AnthropicClient(sdk).complete(request(**kw)))


def test_satisfies_the_client_interface():
    assert isinstance(AnthropicClient(StubSDK(message())), LLMClient)


def test_sends_system_user_and_model():
    sdk = StubSDK(message())
    call(sdk, model="claude-sonnet-5-5", max_tokens=300)
    assert sdk.kwargs["model"] == "claude-sonnet-5-5"
    assert sdk.kwargs["max_tokens"] == 300
    assert sdk.kwargs["system"] == "SYS"
    assert sdk.kwargs["messages"] == [{"role": "user", "content": "USER"}]


def test_default_model_is_used_when_the_request_names_none():
    sdk = StubSDK(message())
    call(sdk)
    assert sdk.kwargs["model"] == FAST_MODEL


def test_schema_request_asks_for_structured_json():
    sdk = StubSDK(message('{"a": "x"}'))
    call(sdk, schema=SCHEMA)
    assert sdk.kwargs["output_config"]["format"] == {"type": "json_schema", "schema": SCHEMA}


def test_plain_request_sends_no_output_format():
    sdk = StubSDK(message())
    call(sdk)
    assert "format" not in sdk.kwargs.get("output_config", {})


def test_effort_is_sent_when_requested():
    sdk = StubSDK(message())
    call(sdk, effort="low")
    assert sdk.kwargs["output_config"]["effort"] == "low"


def test_no_sampling_parameters_are_sent():
    """Newer models reject temperature, top_p and top_k."""
    sdk = StubSDK(message())
    call(sdk, schema=SCHEMA)
    assert not {"temperature", "top_p", "top_k"} & sdk.kwargs.keys()


def test_no_forced_tool_choice_is_sent():
    sdk = StubSDK(message())
    call(sdk, schema=SCHEMA)
    assert "tool_choice" not in sdk.kwargs


def test_returns_text_model_and_tokens():
    out = call(StubSDK(message("hi", model="claude-haiku-5-5")))
    assert out.text == "hi"
    assert out.model == "claude-haiku-5-5"
    assert (out.input_tokens, out.output_tokens) == (21, 7)


def test_non_text_blocks_are_skipped_and_text_blocks_joined():
    blocks = [
        SimpleNamespace(type="thinking", thinking=""),
        SimpleNamespace(type="text", text="part one "),
        SimpleNamespace(type="text", text="part two"),
    ]
    assert call(StubSDK(message(blocks=blocks))).text == "part one part two"


def test_reply_without_text_is_an_error():
    sdk = StubSDK(message(blocks=[SimpleNamespace(type="thinking", thinking="")]))
    with pytest.raises(LLMError, match="no text"):
        call(sdk)


def test_refusal_is_an_error():
    with pytest.raises(LLMError, match="refus"):
        call(StubSDK(message(stop_reason="refusal")))


def test_truncated_reply_is_an_error():
    with pytest.raises(LLMError, match="max_tokens"):
        call(StubSDK(message(stop_reason="max_tokens")))


def test_sdk_errors_become_llm_errors():
    err = anthropic.APIConnectionError(request=httpx2.Request("POST", "https://example.test"))
    with pytest.raises(LLMError, match="APIConnectionError"):
        call(StubSDK(error=err))


def test_building_the_client_needs_no_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    AnthropicClient()  # must not raise or touch the network
