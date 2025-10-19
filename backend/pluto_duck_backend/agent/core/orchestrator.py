"""Agent orchestrator managing LangGraph runs and event streaming."""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, is_dataclass
from typing import Any, AsyncIterator, Dict, Iterable, List, Optional
from uuid import uuid4

from pluto_duck_backend.agent.core import (
    AgentEvent,
    AgentState,
    EventSubType,
    EventType,
    MessageRole,
    PlanStep,
)
from pluto_duck_backend.agent.core.graph import build_agent_graph


def _serialize(value: Any) -> Any:
    if isinstance(value, AgentState):
        return value.to_dict()
    if isinstance(value, PlanStep):
        return asdict(value)
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if is_dataclass(value):
        return asdict(value)
    return value


def _extract_reasoning_message(update: Dict[str, Any]) -> Optional[str]:
    messages = update.get("messages", [])
    for msg in reversed(messages):
        role = getattr(msg, "role", None)
        if role == MessageRole.REASONING:
            return getattr(msg, "content", None)
    return None


def _serialize_plan(update: Dict[str, Any]) -> List[Dict[str, Any]]:
    plan = update.get("plan", [])
    return [_serialize(step) for step in plan]


class AgentRun:
    def __init__(self, conversation_id: str, question: str) -> None:
        self.conversation_id = conversation_id
        self.question = question
        self.queue: asyncio.Queue[Optional[Dict[str, Any]]] = asyncio.Queue()
        self.done = asyncio.Event()
        self.result: Optional[Dict[str, Any]] = None
        self.flags: Dict[str, Any] = {"reasoning_started": False}


class AgentRunManager:
    def __init__(self) -> None:
        self._runs: Dict[str, AgentRun] = {}

    def start_run(self, question: str) -> str:
        conversation_id = str(uuid4())
        run = AgentRun(conversation_id, question)
        self._runs[conversation_id] = run
        asyncio.create_task(self._execute_run(run))
        return conversation_id

    async def _execute_run(self, run: AgentRun) -> None:
        graph = build_agent_graph()
        state = AgentState(conversation_id=run.conversation_id, user_query=run.question)
        state.add_message(MessageRole.USER, run.question)

        final_state: Dict[str, Any] = {}
        try:
            async for chunk in graph.astream(state, stream_mode=["updates", "values"]):
                if isinstance(chunk, tuple) and len(chunk) == 2:
                    mode, payload = chunk
                else:
                    mode, payload = "updates", chunk
                if mode == "updates" and isinstance(payload, dict):
                    for node_name, update in payload.items():
                        events = self._events_from_update(node_name, update, run)
                        for event in events:
                            await run.queue.put(event.to_dict())
                elif mode == "values":
                    if isinstance(payload, dict):
                        final_state = _serialize(payload)
        except Exception as exc:  # pragma: no cover
            event = AgentEvent(
                type=EventType.RUN,
                subtype=EventSubType.ERROR,
                content={"error": str(exc)},
            )
            await run.queue.put(event.to_dict())
            final_state = {"error": str(exc)}
        finally:
            run.result = final_state
            await run.queue.put(
                AgentEvent(
                    type=EventType.RUN,
                    subtype=EventSubType.END,
                    content=_serialize(final_state),
                ).to_dict()
            )
            await run.queue.put(None)
            run.done.set()

    def _events_from_update(self, node_name: str, update: Dict[str, Any], run: AgentRun) -> List[AgentEvent]:
        events: List[AgentEvent] = []
        if node_name == "reasoning":
            decision = update.get("context", {}).get("reasoning_decision")
            reason = _extract_reasoning_message(update) or ""
            if not run.flags["reasoning_started"]:
                events.append(
                    AgentEvent(
                        type=EventType.REASONING,
                        subtype=EventSubType.START,
                        content={"decision": decision, "reason": reason},
                    )
                )
                run.flags["reasoning_started"] = True
            events.append(
                AgentEvent(
                    type=EventType.REASONING,
                    subtype=EventSubType.CHUNK,
                    content={"decision": decision, "reason": reason},
                )
            )
        elif node_name == "planner":
            plan = _serialize_plan(update)
            events.append(
                AgentEvent(
                    type=EventType.TOOL,
                    subtype=EventSubType.END,
                    content={"tool": "planner", "plan": plan},
                )
            )
        elif node_name == "schema":
            preview = update.get("context", {}).get("schema_preview", [])
            events.append(
                AgentEvent(
                    type=EventType.TOOL,
                    subtype=EventSubType.CHUNK,
                    content={"tool": "schema", "preview": preview},
                )
            )
        elif node_name == "sql":
            sql_text = update.get("working_sql") or ""
            events.append(
                AgentEvent(
                    type=EventType.TOOL,
                    subtype=EventSubType.CHUNK,
                    content={"tool": "sql", "sql": sql_text},
                )
            )
        elif node_name == "verifier":
            result = update.get("verification_result", {})
            events.append(
                AgentEvent(
                    type=EventType.TOOL,
                    subtype=EventSubType.END,
                    content={"tool": "verifier", "result": _serialize(result)},
                )
            )
        elif node_name == "finalize":
            info = update.get("context", {})
            events.append(
                AgentEvent(
                    type=EventType.MESSAGE,
                    subtype=EventSubType.FINAL,
                    content=_serialize(info),
                )
            )
        return events

    async def stream_events(self, conversation_id: str) -> AsyncIterator[Dict[str, Any]]:
        run = self._runs.get(conversation_id)
        if run is None:
            raise KeyError(conversation_id)
        while True:
            item = await run.queue.get()
            if item is None:
                break
            yield item

    async def get_result(self, conversation_id: str) -> Dict[str, Any]:
        run = self._runs.get(conversation_id)
        if run is None:
            raise KeyError(conversation_id)
        await run.done.wait()
        return run.result or {}


_AGENT_MANAGER: Optional[AgentRunManager] = None


def get_agent_manager() -> AgentRunManager:
    global _AGENT_MANAGER
    if _AGENT_MANAGER is None:
        _AGENT_MANAGER = AgentRunManager()
    return _AGENT_MANAGER


async def run_agent_once(question: str) -> Dict[str, Any]:
    graph = build_agent_graph()
    state = AgentState(conversation_id=str(uuid4()), user_query=question)
    state.add_message(MessageRole.USER, question)
    final_state: Dict[str, Any] = {}
    async for chunk in graph.astream(state, stream_mode=["updates", "values"]):
        if isinstance(chunk, tuple) and len(chunk) == 2:
            mode, payload = chunk
        else:
            mode, payload = "updates", chunk
        if mode == "values" and isinstance(payload, dict):
            final_state = _serialize(payload)
    return final_state


