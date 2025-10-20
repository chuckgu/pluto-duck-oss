"""Typer-based CLI for Pluto-Duck."""

import asyncio
import itertools
import json
import sys
import threading
import time
from pathlib import Path

import typer

from pluto_duck_backend import __version__
from pluto_duck_backend.agent.core.orchestrator import get_agent_manager, run_agent_once
from pluto_duck_backend.app.core.config import get_settings
from pluto_duck_backend.app.services.ingestion import IngestionJob, IngestionService, get_registry
from pluto_duck_backend.app.services.transformation import DbtService
from pluto_duck_backend.app.services.execution import QueryExecutionManager, QueryJobStatus


def run_async(coro):
    """Run an async coroutine from synchronous Typer commands."""

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


def run_with_spinner(coro, message: str = "Thinking"):
    """Run a coroutine while displaying a simple spinner animation."""

    stop_event = threading.Event()

    def _spin() -> None:
        frames = itertools.cycle("|/-\\")
        while not stop_event.is_set():
            sys.stdout.write(f"\r{message} {next(frames)}")
            sys.stdout.flush()
            time.sleep(0.1)
        sys.stdout.write("\r" + " " * (len(message) + 2) + "\r")
        sys.stdout.flush()

    spinner_thread = threading.Thread(target=_spin, daemon=True)
    spinner_thread.start()
    try:
        return run_async(coro)
    finally:
        stop_event.set()
        spinner_thread.join()


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
    target_table: str = typer.Option(..., "--target-table", help="Target DuckDB table"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing table"),
    config: str = typer.Option(None, "--config", help="Connector config as JSON string"),
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
def query(sql: str = typer.Argument(..., help="SQL query to execute")) -> None:
    """Execute a SQL query."""
    settings = get_settings()
    manager = QueryExecutionManager(settings.duckdb.path)
    job_id = manager.submit(sql)
    typer.echo(f"Query submitted with job ID: {job_id}")
    job = manager.fetch(job_id)
    while job.status in {QueryJobStatus.PENDING, QueryJobStatus.RUNNING}:
        typer.echo(f"Job {job_id} status: {job.status.value}...")
        time.sleep(1)
        job = manager.fetch(job_id)

    if job.status == QueryJobStatus.SUCCESS:
        typer.echo(f"Query completed. Result table: {job.result_table}")
    else:
        typer.echo(f"Query failed: {job.error}")


@app.command()
def agent(question: str = typer.Argument(..., help="Natural language question for the agent")) -> None:
    """Run the local agent once and display the final result."""

    def _run() -> None:
        typer.echo("Starting agent...")
        result = run_with_spinner(run_agent_once(question), message="Thinking")
        typer.echo(typer.style("Agent run completed", fg=typer.colors.GREEN))
        typer.echo(result)

    _run()


@app.command()
def agent_stream(question: str = typer.Argument(..., help="Natural language question")) -> None:
    """Run the agent and stream intermediate events to the console."""

    async def _stream() -> None:
        manager = get_agent_manager()
        run_id = manager.start_run(question)
        typer.echo(f"Started run {run_id}. Streaming events...")
        async for event in manager.stream_events(run_id):
            typer.echo(event)
        final = await manager.get_result(run_id)
        typer.echo(typer.style("Final result", fg=typer.colors.GREEN))
        typer.echo(final)

    run_async(_stream())


if __name__ == "__main__":
    app()

