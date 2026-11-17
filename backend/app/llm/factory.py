import os
from collections.abc import Mapping

from app.llm.anthropic_client import AnthropicClient
from app.llm.base import LLMClient
from app.llm.demo import DemoLLMClient


def build_llm_client(env: Mapping[str, str] | None = None) -> LLMClient:
    """The real model when an API key is set, otherwise the offline demo client."""
    env = os.environ if env is None else env
    for var in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        if (env.get(var) or "").strip():
            return AnthropicClient()
    return DemoLLMClient()
