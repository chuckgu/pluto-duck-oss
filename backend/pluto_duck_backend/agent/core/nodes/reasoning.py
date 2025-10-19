"""Reasoning node for deciding the next agent action."""

from __future__ import annotations

import json
from typing import Any, Dict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from pluto_duck_backend.agent.core import AgentState, MessageRole
from pluto_duck_backend.agent.core.llm.providers import get_llm_provider


REASONING_SYSTEM_PROMPT = (
    "You are the Pluto-Duck OSS agent controller. "
    "Given the plan, recent messages, and execution context, "
    "decide the next action to take. Respond as compact JSON: "
    '{"next": "planner|schema|sql|verifier|finalize", "reason": "..."}.'
)


def build_reasoning_node():
    """Return an async function compatible with LangGraph nodes."""

    async def reasoning_node(state: AgentState) -> AgentState:
        provider = get_llm_provider()
        prompt = _compose_prompt(state)
        response = await provider.ainvoke(prompt)
        parsed = _parse_decision(response)
        state.add_message(MessageRole.REASONING, parsed["reason"])
        state.context["reasoning_decision"] = parsed["next"]
        return state

    return reasoning_node


def route_after_reasoning(state: AgentState) -> str:
    decision = state.context.get("reasoning_decision")
    if decision:
        return decision
    if not state.plan:
        return "planner"
    if "schema_preview" not in state.context:
        return "schema"
    if not state.working_sql:
        return "sql"
    if not state.verification_result:
        return "verifier"
    return "finalize"


def _compose_prompt(state: AgentState) -> str:
    plan_summary = "\n".join(f"- {step.description} ({step.status})" for step in state.plan) or "(no plan yet)"
    recent_messages = "\n".join(f"[{msg.role.value}] {msg.content}" for msg in state.messages[-5:])
    verification = state.verification_result or {}
    return (
        f"{REASONING_SYSTEM_PROMPT}\n"
        f"Current plan:\n{plan_summary}\n"
        f"Recent messages:\n{recent_messages}\n"
        f"Working SQL: {state.working_sql or 'N/A'}\n"
        f"Verification: {verification}\n"
    )


def _parse_decision(response: str) -> Dict[str, str]:
    try:
        payload = json.loads(response)
        next_action = payload.get("next", "planner")
        reason = payload.get("reason", "No rationale provided")
    except json.JSONDecodeError:
        next_action = "planner"
        reason = response.strip() or "No rationale provided"
    normalized = next_action.strip().lower()
    aliases = {
        "final": "finalize",
        "finish": "finalize",
        "complete": "finalize",
        "verification": "verifier",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in {"planner", "schema", "sql", "verifier", "finalize"}:
        normalized = "planner"
    return {"next": normalized, "reason": reason}


