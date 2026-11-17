"""The recording client wraps any LLMClient and keeps what the trace needs."""

import asyncio

import pytest

from app.llm.base import LLMClient, LLMError, LLMRequest
from app.llm.fake import FakeLLMClient
from app.llm.recording import RecordingClient


def req(step, round=None, model="claude-haiku-5-5"):
    return LLMRequest(step=step, system="s", user="u", model=model, round=round)


def make():
    fake = FakeLLMClient()
    return fake, RecordingClient(fake)


def test_satisfies_the_client_interface():
    assert isinstance(RecordingClient(FakeLLMClient()), LLMClient)


def test_passes_the_reply_through_unchanged():
    fake, rec = make()
    fake.respond("sort", "hi", input_tokens=9, output_tokens=4)
    out = asyncio.run(rec.complete(req("sort")))
    assert (out.text, out.input_tokens, out.output_tokens) == ("hi", 9, 4)


def test_records_step_round_model_tokens_and_timing():
    fake, rec = make()
    fake.respond("draft", "x", input_tokens=100, output_tokens=20)
    asyncio.run(rec.complete(req("draft", round=2, model="claude-sonnet-5-5")))

    (r,) = rec.records
    assert (r.step, r.round, r.model) == ("draft", 2, "claude-sonnet-5-5")
    assert (r.input_tokens, r.output_tokens) == (100, 20)
    assert r.latency_ms >= 0
    assert r.status == "ok" and r.error is None


def test_a_failed_call_is_recorded_and_still_raises():
    fake, rec = make()
    fake.fail("sort", "service down")
    with pytest.raises(LLMError, match="service down"):
        asyncio.run(rec.complete(req("sort")))

    (r,) = rec.records
    assert r.status == "error"
    assert "service down" in r.error
    assert (r.input_tokens, r.output_tokens) == (0, 0)


def test_records_are_ordered_by_when_each_call_started():
    fake, rec = make()
    for step, delay in [("a", 0.03), ("b", 0.02), ("c", 0.01)]:
        fake.respond(step, "x", delay=delay)

    async def go():
        await asyncio.gather(*(rec.complete(req(s)) for s in "abc"))

    asyncio.run(go())
    assert [r.step for r in rec.records] == ["a", "b", "c"]
    assert [r.seq for r in rec.records] == [0, 1, 2]
