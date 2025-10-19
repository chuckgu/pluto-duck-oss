"""Integration tests for the single-agent LangGraph skeleton."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from pluto_duck_backend.agent.core import AgentState, MessageRole
from pluto_duck_backend.agent.core.graph import build_agent_graph
from pluto_duck_backend.agent.core.llm.providers import MockLLMProvider


@pytest.mark.asyncio
async def test_agent_graph_completes(monkeypatch) -> None:
    scripted = [
        '{"next": "planner", "reason": "create plan"}',
        '{"steps": [{"description": "Generate demo SQL"}]}',
        '{"next": "sql", "reason": "generate sql"}',
        'SELECT 1 AS value;',
        '{"next": "verifier", "reason": "run query"}',
        '{"next": "finalize", "reason": "finish"}',
    ]
    provider = MockLLMProvider(scripted)

    patch = lambda: provider
    monkeypatch.setattr("pluto_duck_backend.agent.core.llm.providers.get_llm_provider", patch)
    monkeypatch.setattr("pluto_duck_backend.agent.core.nodes.reasoning.get_llm_provider", patch)
    monkeypatch.setattr("pluto_duck_backend.agent.core.nodes.planner.get_llm_provider", patch)
    monkeypatch.setattr("pluto_duck_backend.agent.core.nodes.sql.get_llm_provider", patch)

    graph = build_agent_graph()
    state = AgentState(conversation_id=str(uuid4()), user_query="List customers")
    state.add_message(MessageRole.USER, state.user_query)

    result = await graph.ainvoke(state)
    assert result["context"].get("finished") is True
    assert result["working_sql"]
    assert result["verification_result"] is not None
    assert "job_id" in result["verification_result"]


