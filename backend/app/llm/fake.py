"""A scripted stand-in for the model, used by every test."""

import json
from collections import defaultdict, deque
from typing import Any

from app.llm.base import LLMError, LLMRequest, LLMResponse


class FakeLLMClient:
    """Returns scripted replies per step and records every request.

    Replies for a step are used in order. The last one repeats, so a single
    ``respond`` call covers any number of calls to that step.
    """

    def __init__(self) -> None:
        self.calls: list[LLMRequest] = []
        self._script: dict[str, deque[LLMResponse | LLMError]] = defaultdict(deque)

    def respond(
        self,
        step: str,
        reply: str | dict[str, Any] | list[Any],
        *,
        input_tokens: int = 10,
        output_tokens: int = 5,
        model: str = "fake-model",
    ) -> None:
        text = reply if isinstance(reply, str) else json.dumps(reply)
        self._script[step].append(LLMResponse(text, model, input_tokens, output_tokens))

    def fail(self, step: str, message: str = "fake model failure") -> None:
        self._script[step].append(LLMError(message))

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        queue = self._script.get(request.step)
        if not queue:
            raise LookupError(f"No fake reply scripted for step {request.step!r}")
        item = queue.popleft() if len(queue) > 1 else queue[0]
        if isinstance(item, LLMError):
            raise item
        return item
