"""Typer-based CLI for Pluto-Duck."""

import json

import typer

from pluto_duck_backend.app.core.config import get_settings
from pluto_duck_backend.app.services.execution.manager import get_execution_manager
from pluto_duck_backend.app.services.ingestion import IngestionJob, IngestionService, get_registry
from pluto_duck_backend.app.services.transformation import DbtService


app = typer.Typer(help="Local-first Pluto-Duck CLI")


@app.command()
def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the Pluto-Duck API server (stub)."""

    typer.echo(
        "Pluto-Duck backend is not implemented yet. "
        "This command will start the FastAPI server once available."
    )


@app.command()
def version() -> None:
    """Display the current Pluto-Duck package version."""

    from pluto_duck_backend import __version__

    typer.echo(__version__)


def _dbt_service() -> DbtService:
    settings = get_settings()
    return DbtService(
        settings.dbt.project_path,
        settings.dbt.profiles_path,
        settings.data_dir.artifacts / "dbt",
        settings.duckdb.path,
    )


@app.command()
def dbt_run(select: str = typer.Option(None, help="Space-separated dbt selection")) -> None:
    """Run dbt models."""

    selection = select.split(" ") if select else None
    typer.echo(_dbt_service().run(select=selection))


@app.command()
def dbt_test(select: str = typer.Option(None, help="Space-separated dbt selection")) -> None:
    """Run dbt tests."""

    selection = select.split(" ") if select else None
    typer.echo(_dbt_service().test(select=selection))


@app.command()
def ingest(
    connector: str = typer.Argument(..., help="Connector name"),
    target_table: str = typer.Option(..., "--target", help="Target DuckDB table"),
    overwrite: bool = typer.Option(False, help="Overwrite existing table"),
    config: str = typer.Option(None, help="Connector config as JSON string"),
) -> None:
    """Run an ingestion job using a registered connector."""

    settings = get_settings()
    registry = get_registry()
    service = IngestionService(registry)
    job = IngestionJob(
        connector=connector,
        target_table=target_table,
        warehouse_path=settings.duckdb.path,
        overwrite=overwrite,
        config=json.loads(config) if config else {},
    )
    typer.echo(service.run(job))


@app.command()
def query(sql: str = typer.Argument(..., help="SQL to execute")) -> None:
    """Execute SQL via the background query manager."""

    manager = get_execution_manager()
    job_id = manager.submit_sql(sql)
    job = manager.wait_for(job_id)
    if not job:
        typer.echo("Query job not found")
        raise typer.Exit(code=1)
    typer.echo(
        {
            "job_id": job.job_id,
            "status": job.status,
            "result_table": job.result_table,
            "error": job.error,
        }
    )


if __name__ == "__main__":
    app()

