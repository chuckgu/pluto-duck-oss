from pathlib import Path

import pytest

from pluto_duck_backend.app.services.transformation.service import DbtInvocationError, DbtService


def test_dbt_service_run_fails_without_dbt(tmp_path: Path) -> None:
    service = DbtService(tmp_path, tmp_path, tmp_path / "artifacts", tmp_path / "warehouse.duckdb")
    with pytest.raises(DbtInvocationError):
        service.run()

