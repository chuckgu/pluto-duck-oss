"""LLM provider abstractions for the agent skeleton."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, Optional


def _is_gpt5_model(model: str) -> bool:
    return model.startswith("gpt-5")

from pluto_duck_backend.app.core.config import get_settings

try:  # Optional dependency for real provider
    from openai import AsyncOpenAI
except ImportError:  # pragma: no cover - handled at runtime
    AsyncOpenAI = None  # type: ignore


class BaseLLMProvider(ABC):
    """Abstract interface for orchestrating LLM calls."""

    @abstractmethod
    async def ainvoke(self, prompt: str, *, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Asynchronously execute a prompt and return the model response."""


class MockLLMProvider(BaseLLMProvider):
    """Deterministic provider used for tests and offline development."""

    def __init__(self, scripted_responses: Optional[Iterable[str]] = None) -> None:
        self._responses = list(scripted_responses or [])

    async def ainvoke(self, prompt: str, *, metadata: Optional[Dict[str, Any]] = None) -> str:
        if self._responses:
            return self._responses.pop(0)
        return '{"next": "planner", "reason": "default mock"}'


class OpenAILLMProvider(BaseLLMProvider):
    """OpenAI GPT-based provider using the Responses API."""

    def __init__(self, api_key: str, model: str, api_base: Optional[str] = None) -> None:
        if AsyncOpenAI is None:  # pragma: no cover - requires optional dependency
            raise RuntimeError("openai package is not installed. Install `openai>=1.0` to use the OpenAI provider.")
        if api_base is not None:
            api_base = str(api_base)
        self._client = AsyncOpenAI(api_key=api_key, base_url=api_base)
        self._model = model

    async def ainvoke(self, prompt: str, *, metadata: Optional[Dict[str, Any]] = None) -> str:
        config = get_settings().agent
        request_kwargs: Dict[str, Any] = {
            "model": self._model,
            "input": prompt,
        }

        if _is_gpt5_model(self._model):
            request_kwargs["reasoning"] = {"effort": config.reasoning_effort}
            request_kwargs["text"] = {"verbosity": config.text_verbosity}
            if config.max_output_tokens is not None:
                request_kwargs["max_output_tokens"] = config.max_output_tokens

        response = await self._client.responses.create(**request_kwargs)
        if hasattr(response, "output_text"):
            return response.output_text  # type: ignore[return-value]
        # Fallback: join content pieces if output_text missing
        if response.output:
            parts = []
            for item in response.output:
                if getattr(item, "content", None):
                    for content in item.content:
                        if getattr(content, "text", None):
                            parts.append(content.text)
            if parts:
                return "\n".join(parts)
        return ""


def get_llm_provider(*, scripted_responses: Optional[Iterable[str]] = None) -> BaseLLMProvider:
    """Return an LLM provider configured via `PlutoDuckSettings`."""

    if scripted_responses is not None:
        return MockLLMProvider(scripted_responses)

    settings = get_settings()
    if settings.agent.mock_mode or not settings.agent.api_key:
        return MockLLMProvider()

    provider_name = (settings.agent.provider or "openai").lower()
    if provider_name == "openai":
        return OpenAILLMProvider(
            api_key=settings.agent.api_key,
            model=settings.agent.model,
            api_base=settings.agent.api_base,
        )

    raise RuntimeError(f"Unsupported agent provider: {settings.agent.provider}")


