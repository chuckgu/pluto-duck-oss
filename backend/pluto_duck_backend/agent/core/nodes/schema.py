"""Schema exploration node."""

from __future__ import annotations

from typing import List

import duckdb

from pluto_duck_backend.agent.core import AgentState, MessageRole
from pluto_duck_backend.agent.core.prompts import try_load_prompt
from pluto_duck_backend.app.core.config import get_settings

DEFAULT_SCHEMA_PROMPT = "Summarize available tables for the user."


def build_schema_node():
    settings = get_settings()
    prompt = try_load_prompt("schema_prompt") or DEFAULT_SCHEMA_PROMPT

    async def schema_node(state: AgentState) -> AgentState:
        with duckdb.connect(str(settings.duckdb.path)) as con:
            rows = con.execute("SHOW TABLES").fetchall()
        tables = [row[0] for row in rows]
        state.context["schema_preview"] = tables
        summary = f"Schema preview: {', '.join(tables)}" if tables else "No tables found."
        state.add_message(MessageRole.ASSISTANT, summary)
        return state

    return schema_node


