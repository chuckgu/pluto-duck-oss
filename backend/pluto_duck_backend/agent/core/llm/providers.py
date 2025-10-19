"""LLM provider abstractions for the agent skeleton."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, Optional

from pluto_duck_backend.app.core.config import get_settings


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


def get_llm_provider(*, scripted_responses: Optional[Iterable[str]] = None) -> BaseLLMProvider:
    """Return an LLM provider configured via `PlutoDuckSettings`."""

    settings = get_settings()
    if scripted_responses is not None:
        return MockLLMProvider(scripted_responses)
    if settings.agent.mock_mode or not settings.agent.api_key:
        return MockLLMProvider()

    # Placeholder for future real provider integration.
    return MockLLMProvider()


