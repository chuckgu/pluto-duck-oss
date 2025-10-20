"""Verifier node executes SQL candidates and records results."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from pluto_duck_backend.agent.core import AgentState, MessageRole
from pluto_duck_backend.app.core.config import get_settings
from pluto_duck_backend.app.services.execution import QueryExecutionService, QueryJobStatus


def build_verifier_node():
    settings = get_settings()
    warehouse_path = Path(settings.duckdb.path)
    warehouse_path.parent.mkdir(parents=True, exist_ok=True)
    service = QueryExecutionService(warehouse_path)

    async def verifier_node(state: AgentState) -> AgentState:
        if not state.working_sql:
            state.add_message(MessageRole.ASSISTANT, "No SQL to verify.")
            return state

        job_id = str(uuid4())
        service.submit(job_id, state.working_sql)
        try:
            job = service.execute(job_id)
        except Exception as exc:  # duckdb errors or others
            record = service.fetch(job_id)
            state.verification_result = {
                "job_id": job_id,
                "error": str(exc),
                "result_table": record.result_table if record else None,
            }
            state.add_message(MessageRole.ASSISTANT, f"Query failed: {state.verification_result['error']}")
            return state

        if job.status == QueryJobStatus.SUCCESS:
            state.verification_result = {
                "job_id": job.job_id,
                "rows_affected": job.rows_affected,
                "result_table": job.result_table,
            }
            state.add_message(
                MessageRole.ASSISTANT,
                f"Query succeeded with table {job.result_table} ({job.rows_affected} rows).",
            )
        else:
            state.verification_result = {
                "job_id": job.job_id,
                "error": job.error or "Unknown error",
                "result_table": job.result_table,
            }
            state.add_message(MessageRole.ASSISTANT, f"Query failed: {state.verification_result['error']}")
        return state

    return verifier_node


