"""DuckDB-backed query execution service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

import duckdb


@dataclass
class QueryJob:
    job_id: str
    sql: str
    submitted_at: datetime
    status: str
    result_table: Optional[str] = None
    error: Optional[str] = None
    completed_at: Optional[datetime] = None


class QueryExecutionService:
    """Execute SQL queries against the local DuckDB warehouse."""

    def __init__(self, warehouse_path: Path):
        self.warehouse_path = warehouse_path
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        with duckdb.connect(str(self.warehouse_path)) as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS query_history (
                    job_id TEXT PRIMARY KEY,
                    sql TEXT,
                    status TEXT,
                    submitted_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    result_relation TEXT,
                    error TEXT
                )
                """
            )

    def _sanitize_relation(self, job_id: str) -> str:
        sanitized = "".join(ch for ch in job_id if ch.isalnum() or ch == "_")
        if not sanitized:
            sanitized = "result"
        return f"query_result_{sanitized}"

    def submit(self, job_id: str, sql: str) -> QueryJob:
        submitted_at = datetime.now(UTC)
        with duckdb.connect(str(self.warehouse_path)) as con:
            con.execute(
                "INSERT OR REPLACE INTO query_history (job_id, sql, status, submitted_at) VALUES (?, ?, ?, ?)",
                [job_id, sql, "pending", submitted_at],
            )
        return QueryJob(job_id=job_id, sql=sql, status="pending", submitted_at=submitted_at)

    def execute(self, job_id: str) -> QueryJob:
        with duckdb.connect(str(self.warehouse_path)) as con:
            row = con.execute(
                "SELECT sql, submitted_at FROM query_history WHERE job_id = ?",
                [job_id],
            ).fetchone()
            if not row:
                raise ValueError(f"Unknown job_id {job_id}")
            sql, submitted_at = row
            submitted_at = submitted_at.replace(tzinfo=UTC) if submitted_at.tzinfo is None else submitted_at
            result_relation = self._sanitize_relation(job_id)
            try:
                con.execute(f"CREATE OR REPLACE TABLE {result_relation} AS {sql}")
                completed_at = datetime.now(UTC)
                con.execute(
                    "UPDATE query_history SET status=?, completed_at=?, result_relation=?, error=NULL WHERE job_id=?",
                    ["success", completed_at, result_relation, job_id],
                )
            except duckdb.Error as exc:
                completed_at = datetime.now(UTC)
                con.execute(
                    "UPDATE query_history SET status=?, completed_at=?, error=? WHERE job_id=?",
                    ["failed", completed_at, str(exc), job_id],
                )
                raise
        return self.fetch(job_id)  # type: ignore[return-value]

    def fetch(self, job_id: str) -> Optional[QueryJob]:
        with duckdb.connect(str(self.warehouse_path)) as con:
            row = con.execute(
                "SELECT job_id, sql, status, submitted_at, completed_at, result_relation, error FROM query_history WHERE job_id=?",
                [job_id],
            ).fetchone()
        if not row:
            return None
        submitted_at = row[3]
        if isinstance(submitted_at, datetime) and submitted_at.tzinfo is None:
            submitted_at = submitted_at.replace(tzinfo=UTC)
        completed_at = row[4]
        if isinstance(completed_at, datetime) and completed_at.tzinfo is None:
            completed_at = completed_at.replace(tzinfo=UTC)
        return QueryJob(
            job_id=row[0],
            sql=row[1],
            status=row[2],
            submitted_at=submitted_at,
            completed_at=completed_at,
            result_table=row[5],
            error=row[6],
        )


