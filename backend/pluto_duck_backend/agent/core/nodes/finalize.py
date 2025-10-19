"""Finalization node for producing the final response."""

from __future__ import annotations

from pluto_duck_backend.agent.core import AgentState, MessageRole


def build_finalize_node():
    async def finalize_node(state: AgentState) -> AgentState:
        summary = state.verification_result or {}
        result_str = "Success" if "error" not in summary else f"Error: {summary['error']}"
        state.add_message(MessageRole.ASSISTANT, f"Final result: {result_str}")
        state.context["finished"] = True
        return state

    return finalize_node


