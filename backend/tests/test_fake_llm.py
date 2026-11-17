"""The fake client stands in for the real model in every test."""

import asyncio

import pytest

from app.llm.base import LLMClient, LLMError, LLMRequest
from app.llm.fake import FakeLLMClient


def req(step="sort", **kw):
    return LLMRequest(step=step, system="sys", user="user", **kw)


def test_fake_satisfies_the_client_interface():
    assert isinstance(FakeLLMClient(), LLMClient)


def test_returns_scripted_text_and_token_counts():
    fake = FakeLLMClient()
    fake.respond("sort", "hello", input_tokens=12, output_tokens=3)

    out = asyncio.run(fake.complete(req()))

    assert out.text == "hello"
    assert (out.input_tokens, out.output_tokens) == (12, 3)


def test_dict_is_returned_as_json_text():
    fake = FakeLLMClient()
    fake.respond("sort", {"a": 1})
    out = asyncio.run(fake.complete(req()))
    assert out.text == '{"a": 1}'


def test_records_every_request():
    fake = FakeLLMClient()
    fake.respond("sort", "x")
    asyncio.run(fake.complete(req(step="sort")))
    assert [c.step for c in fake.calls] == ["sort"]
    assert fake.calls[0].user == "user"


def test_responses_are_used_in_order_and_the_last_one_repeats():
    fake = FakeLLMClient()
    fake.respond("draft", "one")
    fake.respond("draft", "two")
    texts = [asyncio.run(fake.complete(req("draft"))).text for _ in range(3)]
    assert texts == ["one", "two", "two"]


def test_scripted_failure_raises_llm_error():
    fake = FakeLLMClient()
    fake.fail("sort", "service down")
    with pytest.raises(LLMError, match="service down"):
        asyncio.run(fake.complete(req()))


def test_unscripted_step_fails_loudly():
    with pytest.raises(LookupError, match="sort"):
        asyncio.run(FakeLLMClient().complete(req()))


def test_needs_no_network_or_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    fake = FakeLLMClient()
    fake.respond("sort", "ok")
    assert asyncio.run(fake.complete(req())).text == "ok"
