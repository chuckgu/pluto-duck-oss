"""Finalization node for producing the final response."""

from __future__ import annotations

from pluto_duck_backend.agent.core import AgentState, MessageRole


def build_finalize_node():
    async def finalize_node(state: AgentState) -> AgentState:
        # Use the final_message from reasoning if available
        final_message = state.context.get("final_message")
        
        if final_message:
            # Reasoning already prepared the final message
            result_str = final_message
        else:
            # Fallback: construct from verification result
            summary = state.verification_result or {}
            if "error" in summary:
                result_str = f"Error: {summary['error']}"
            elif state.working_sql:
                result_str = f"Query executed successfully. SQL: {state.working_sql}"
            else:
                result_str = "Task completed."
        
        # Don't add to state.messages - orchestrator will save to DB
        # Just store in context for orchestrator to use
        state.context["finished"] = True
        state.context["final_answer"] = result_str
        _log("finalized", conversation_id=state.conversation_id, has_message=bool(final_message))
        return state

    return finalize_node


def _log(message: str, **fields: object) -> None:
    payload = " ".join(f"{key}={value}" for key, value in fields.items()) if fields else ""
    print(f"[agent][finalize] {message} {payload}")
