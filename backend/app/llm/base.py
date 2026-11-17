"""The one interface every model call goes through.

Pipeline code depends on ``LLMClient`` only. Production uses the Anthropic
client; tests use ``FakeLLMClient``, so no test needs a network or an API key.
"""

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


class LLMError(Exception):
    """A model call failed (network, API error, refusal, empty reply)."""


@dataclass(frozen=True)
class LLMRequest:
    step: str  # pipeline step name, for example "sort" or "draft"
    system: str
    user: str
    schema: dict[str, Any] | None = None  # JSON schema for a structured reply
    model: str | None = None  # None means the client's default model
    max_tokens: int = 2048
    effort: str | None = None  # low | medium | high; None means the model default
    round: int | None = None  # draft/review round, for the trace


@dataclass(frozen=True)
class LLMResponse:
    text: str  # raw reply text. For a schema request this is JSON, not yet validated.
    model: str
    input_tokens: int
    output_tokens: int


@runtime_checkable
class LLMClient(Protocol):
    async def complete(self, request: LLMRequest) -> LLMResponse: ...
