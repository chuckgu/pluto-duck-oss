from pathlib import Path

import duckdb
import sqlite3

from pluto_duck_backend.app.services.ingestion.base import IngestionContext
from pluto_duck_backend.app.services.ingestion.connectors.csv import CSVConnector
from pluto_duck_backend.app.services.ingestion.connectors.sqlite import SQLiteConnector
from pluto_duck_backend.app.services.ingestion.duckdb_loader import DuckDBLoader
from pluto_duck_backend.app.services.ingestion.registry import ConnectorRegistry
from pluto_duck_backend.app.services.ingestion.service import IngestionJob, IngestionService


def make_tmp_warehouse(tmp_path: Path) -> Path:
    warehouse = tmp_path / "warehouse.duckdb"
    warehouse.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(warehouse))
    conn.close()
    return warehouse


def test_duckdb_loader_overwrite(tmp_path: Path) -> None:
    loader = DuckDBLoader(make_tmp_warehouse(tmp_path))
    data = [{"id": 1}, {"id": 2}]
    inserted = loader.load_dicts("test_table", data, overwrite=True)
    assert inserted == 2


def test_csv_connector_stream(tmp_path: Path) -> None:
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("id,name\n1,Alice\n2,Bob\n", encoding="utf-8")
    connector = CSVConnector({"path": str(csv_file)})
    rows = list(connector.stream_rows())
    assert rows == [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
    ]


def test_registry_creates_connector(tmp_path: Path) -> None:
    registry = ConnectorRegistry()
    registry.register(CSVConnector)
    connector = registry.create("csv", {"path": str(tmp_path / "fake.csv")})
    assert isinstance(connector, CSVConnector)


def test_ingestion_service_runs_csv(tmp_path: Path) -> None:
    registry = ConnectorRegistry()
    registry.register(CSVConnector)

    csv_file = tmp_path / "data.csv"
    csv_file.write_text("id,name\n1,Alice\n2,Bob\n", encoding="utf-8")

    warehouse = make_tmp_warehouse(tmp_path)

    service = IngestionService(registry)
    job = IngestionJob(
        connector="csv",
        target_table="people",
        warehouse_path=warehouse,
        config={"path": str(csv_file)},
        overwrite=True,
    )
    result = service.run(job)

    assert result["rows_ingested"] == 2

    con = duckdb.connect(str(warehouse))
    data = con.execute("SELECT * FROM people ORDER BY id").fetchall()
    assert data == [(1, "Alice"), (2, "Bob")]
    con.close()


def test_sqlite_connector(tmp_path: Path) -> None:
    db_path = tmp_path / "example.db"
    sqlite_conn = sqlite3.connect(str(db_path))
    sqlite_conn.execute("CREATE TABLE example (id INTEGER, name TEXT)")
    sqlite_conn.execute("INSERT INTO example VALUES (1, 'Alice')")
    sqlite_conn.commit()
    sqlite_conn.close()

    connector = SQLiteConnector({"path": str(db_path), "query": "SELECT * FROM example"})
    connector.open()
    rows = list(connector.stream_rows())
    connector.close()

    assert rows == [{"id": 1, "name": "Alice"}]

