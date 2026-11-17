"""The real model client, built on the Anthropic SDK.

Everything the SDK can raise is turned into ``LLMError``, so pipeline code only
has one kind of failure to handle.
"""

from typing import Any

import anthropic

from app.llm.base import LLMError, LLMRequest, LLMResponse
from app.llm.models import FAST_MODEL


class AnthropicClient:
    def __init__(self, sdk: Any | None = None, default_model: str = FAST_MODEL) -> None:
        # The SDK client is built on first use, so creating this object needs no
        # API key. Tests pass in a stub instead.
        self._sdk = sdk
        self._default_model = default_model

    @property
    def sdk(self) -> Any:
        if self._sdk is None:
            self._sdk = anthropic.AsyncAnthropic()
        return self._sdk

    async def complete(self, request: LLMRequest) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": request.model or self._default_model,
            "max_tokens": request.max_tokens,
            "system": request.system,
            "messages": [{"role": "user", "content": request.user}],
        }
        output_config: dict[str, Any] = {}
        if request.schema is not None:
            output_config["format"] = {"type": "json_schema", "schema": request.schema}
        if request.effort is not None:
            output_config["effort"] = request.effort
        if output_config:
            kwargs["output_config"] = output_config

        try:
            message = await self.sdk.messages.create(**kwargs)
        except anthropic.APIError as err:
            raise LLMError(f"{type(err).__name__}: {err}") from err

        # Check the stop reason before reading the content.
        if message.stop_reason == "refusal":
            raise LLMError("The model refused the request.")
        if message.stop_reason == "max_tokens":
            raise LLMError("The reply was cut off at max_tokens.")

        text = "".join(b.text for b in message.content if b.type == "text")
        if not text:
            raise LLMError("The model reply had no text.")

        return LLMResponse(
            text=text,
            model=message.model,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
        )
