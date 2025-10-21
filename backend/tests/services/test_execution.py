from pathlib import Path
from uuid import uuid4

from pluto_duck_backend.app.services.execution import QueryExecutionService


def test_query_execution_success(tmp_path: Path) -> None:
    warehouse = tmp_path / "warehouse.duckdb"
    service = QueryExecutionService(warehouse)

    run_id = str(uuid4())
    service.submit(run_id, "select 1 as value")
    job = service.execute(run_id)

    assert job.status == "success"
    fetched = service.fetch(run_id)
    assert fetched is not None
    assert fetched.result_table is not None

