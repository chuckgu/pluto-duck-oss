"""LangGraph composition for the single-agent skeleton."""

from __future__ import annotations

from typing import AsyncIterator

from langgraph.graph import END, START, StateGraph

from pluto_duck_backend.agent.core import AgentEvent, AgentState, EventSubType, EventType
from pluto_duck_backend.agent.core.nodes import (
    build_finalize_node,
    build_planner_node,
    build_reasoning_node,
    build_schema_node,
    build_sql_node,
    build_verifier_node,
    route_after_reasoning,
)


def build_agent_graph() -> StateGraph[AgentState]:
    graph = StateGraph(AgentState)
    graph.add_node("reasoning", build_reasoning_node())
    graph.add_node("planner", build_planner_node())
    graph.add_node("schema", build_schema_node())
    graph.add_node("sql", build_sql_node())
    graph.add_node("verifier", build_verifier_node())
    graph.add_node("finalize", build_finalize_node())

    graph.add_edge(START, "reasoning")
    graph.add_conditional_edges(
        "reasoning",
        route_after_reasoning,
        {
            "planner": "planner",
            "schema": "schema",
            "sql": "sql",
            "verifier": "verifier",
            "finalize": "finalize",
        },
    )
    graph.add_edge("planner", "reasoning")
    graph.add_edge("schema", "reasoning")
    graph.add_edge("sql", "reasoning")
    graph.add_edge("verifier", "reasoning")
    graph.add_edge("finalize", END)
    return graph.compile()


async def stream_events(graph: StateGraph[AgentState], state: AgentState) -> AsyncIterator[AgentEvent]:
    async for update in graph.astream(state):
        yield AgentEvent(EventType.MESSAGE, EventSubType.CHUNK, content=str(update))


