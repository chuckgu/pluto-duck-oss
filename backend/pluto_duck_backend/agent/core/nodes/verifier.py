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

        run_id = str(uuid4())
        service.submit(run_id, state.working_sql)
        try:
            job = service.execute(run_id)
        except Exception as exc:  # duckdb errors or others
            record = service.fetch(run_id)
            state.verification_result = {
                "run_id": run_id,
                "error": str(exc),
                "result_table": record.result_table if record else None,
            }
            state.add_message(MessageRole.ASSISTANT, f"Query failed: {state.verification_result['error']}")
            _log("verifier_failed", conversation_id=state.conversation_id, run_id=run_id, error=str(exc))
            return state

        if job.status == QueryJobStatus.SUCCESS:
            state.verification_result = {
                "run_id": job.run_id,
                "rows_affected": job.rows_affected,
                "result_table": job.result_table,
            }
            state.add_message(
                MessageRole.ASSISTANT,
                f"Query succeeded with table {job.result_table} ({job.rows_affected} rows).",
            )
            _log(
                "verifier_succeeded",
                conversation_id=state.conversation_id,
                job_run_id=job.run_id,
                rows_affected=job.rows_affected,
            )
        else:
            state.verification_result = {
                "run_id": job.run_id,
                "error": job.error or "Unknown error",
                "result_table": job.result_table,
            }
            state.add_message(MessageRole.ASSISTANT, f"Query failed: {state.verification_result['error']}")
            _log(
                "verifier_reported_failure",
                conversation_id=state.conversation_id,
                job_run_id=job.run_id,
                error=job.error,
            )
        return state

    return verifier_node


def _log(message: str, **fields: object) -> None:
    payload = " ".join(f"{key}={value}" for key, value in fields.items()) if fields else ""
    print(f"[agent][verifier] {message} {payload}")


