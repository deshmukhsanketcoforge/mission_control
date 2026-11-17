"""A scripted stand-in for the model, used by every test."""

import asyncio
import json
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

from app.llm.base import LLMError, LLMRequest, LLMResponse


@dataclass(frozen=True)
class _Scripted:
    text: str
    model: str | None
    input_tokens: int
    output_tokens: int
    delay: float


class FakeLLMClient:
    """Returns scripted replies per step and records every request.

    Replies for a step are used in order. The last one repeats, so a single
    ``respond`` call covers any number of calls to that step.

    ``max_in_flight`` is the most calls that were running at the same moment, so
    a test can prove that calls ran concurrently.
    """

    def __init__(self) -> None:
        self.calls: list[LLMRequest] = []
        self.in_flight = 0
        self.max_in_flight = 0
        self._script: dict[str, deque[_Scripted | LLMError]] = defaultdict(deque)

    def respond(
        self,
        step: str,
        reply: str | dict[str, Any] | list[Any],
        *,
        input_tokens: int = 10,
        output_tokens: int = 5,
        model: str | None = None,
        delay: float = 0.0,
    ) -> None:
        text = reply if isinstance(reply, str) else json.dumps(reply)
        self._script[step].append(_Scripted(text, model, input_tokens, output_tokens, delay))

    def clear(self, step: str) -> None:
        """Forget everything scripted for a step."""
        self._script[step].clear()

    def fail(self, step: str, message: str = "fake model failure") -> None:
        self._script[step].append(LLMError(message))

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        queue = self._script.get(request.step)
        if not queue:
            raise LookupError(f"No fake reply scripted for step {request.step!r}")
        item = queue.popleft() if len(queue) > 1 else queue[0]

        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            delay = item.delay if isinstance(item, _Scripted) else 0.0
            await asyncio.sleep(delay)  # lets other calls start, like a real network call
        finally:
            self.in_flight -= 1

        if isinstance(item, LLMError):
            raise item
        return LLMResponse(
            text=item.text,
            model=item.model or request.model or "fake-model",
            input_tokens=item.input_tokens,
            output_tokens=item.output_tokens,
        )
