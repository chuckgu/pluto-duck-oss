"""Planner node for creating or updating structured plans."""

from __future__ import annotations

import json
from typing import List

from pluto_duck_backend.agent.core import AgentState, MessageRole, PlanStep
from pluto_duck_backend.agent.core.llm.providers import get_llm_provider
from pluto_duck_backend.agent.core.prompts import load_prompt, try_load_prompt

_DEFAULT_PROMPT = (
    "Construct a concise JSON plan with a list of steps to satisfy the user request."
)


def build_planner_node():
    prompt_template = try_load_prompt("planner_prompt") or _DEFAULT_PROMPT

    async def planner_node(state: AgentState) -> AgentState:
        provider = get_llm_provider()
        prompt = f"{prompt_template}\nUser: {state.user_query}"
        response = await provider.ainvoke(prompt)
        steps = _parse_steps(response)
        state.update_plan(steps)
        state.add_message(MessageRole.ASSISTANT, "Plan updated:")
        for step in steps:
            state.add_message(MessageRole.ASSISTANT, f"- {step.description}")
        _log("planner_steps", conversation_id=state.conversation_id, step_count=len(steps))
        return state

    return planner_node


def _parse_steps(text: str) -> List[PlanStep]:
    try:
        payload = json.loads(text)
        items = payload.get("steps", []) if isinstance(payload, dict) else payload
        steps = []
        for item in items:
            if isinstance(item, dict):
                desc = item.get("description") or item.get("step") or "Unnamed step"
                status = item.get("status", "pending")
                metadata = {k: v for k, v in item.items() if k not in {"description", "step", "status"}}
            else:
                desc = str(item)
                status = "pending"
                metadata = {}
            steps.append(PlanStep(description=desc, status=status, metadata=metadata))
        if steps:
            return steps
    except json.JSONDecodeError:
        pass
    lines = [line.strip("- ") for line in text.splitlines() if line.strip()]
    return [PlanStep(description=line) for line in lines[:3]] or [PlanStep(description="Run sample query")]


def _log(message: str, **fields: object) -> None:
    payload = " ".join(f"{key}={value}" for key, value in fields.items()) if fields else ""
    print(f"[agent][planner] {message} {payload}")


