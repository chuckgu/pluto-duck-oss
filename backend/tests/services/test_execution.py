from pathlib import Path
from uuid import uuid4

from pluto_duck_backend.app.services.execution import QueryExecutionService


def test_query_execution_success(tmp_path: Path) -> None:
    warehouse = tmp_path / "warehouse.duckdb"
    service = QueryExecutionService(warehouse)

    job_id = str(uuid4())
    service.submit(job_id, "select 1 as value")
    job = service.execute(job_id)

    assert job.status == "success"
    fetched = service.fetch(job_id)
    assert fetched is not None
    assert fetched.result_table is not None

