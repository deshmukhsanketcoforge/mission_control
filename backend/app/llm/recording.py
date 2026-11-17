"""Wraps any LLMClient and keeps one record per call, for the trace."""

import time
from dataclasses import dataclass

from app.llm.base import LLMClient, LLMError, LLMRequest, LLMResponse


@dataclass(frozen=True)
class CallRecord:
    seq: int
    step: str
    round: int | None
    model: str | None
    input_tokens: int
    output_tokens: int
    latency_ms: int
    status: str  # "ok" or "error"
    error: str | None = None


class RecordingClient:
    def __init__(self, inner: LLMClient) -> None:
        self._inner = inner
        self._slots: list[CallRecord | None] = []

    @property
    def records(self) -> list[CallRecord]:
        """Records in the order the calls started, not the order they finished."""
        return [r for r in self._slots if r is not None]

    async def complete(self, request: LLMRequest) -> LLMResponse:
        seq = len(self._slots)
        self._slots.append(None)
        started = time.perf_counter()
        try:
            response = await self._inner.complete(request)
        except LLMError as err:
            self._slots[seq] = CallRecord(
                seq, request.step, request.round, request.model, 0, 0,
                _ms(started), "error", str(err),
            )
            raise
        self._slots[seq] = CallRecord(
            seq, request.step, request.round, response.model,
            response.input_tokens, response.output_tokens, _ms(started), "ok",
        )
        return response


def _ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)
