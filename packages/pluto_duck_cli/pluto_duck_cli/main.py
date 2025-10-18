"""Typer-based CLI for Pluto-Duck."""

import typer

from pluto_duck_backend.app.core.config import get_settings
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


@app.command()
def dbt_run(select: str = typer.Option(None, help="Space-separated dbt selection")) -> None:
    """Run dbt models."""
    settings = get_settings()
    service = DbtService(
        settings.dbt.project_path,
        settings.dbt.profiles_path,
        settings.data_dir.artifacts / "dbt",
        settings.duckdb.path,
    )
    args = select.split(" ") if select else None
    typer.echo(service.run(select=args))


@app.command()
def dbt_test(select: str = typer.Option(None, help="Space-separated dbt selection")) -> None:
    """Run dbt tests."""
    settings = get_settings()
    service = DbtService(
        settings.dbt.project_path,
        settings.dbt.profiles_path,
        settings.data_dir.artifacts / "dbt",
        settings.duckdb.path,
    )
    args = select.split(" ") if select else None
    typer.echo(service.test(select=args))


if __name__ == "__main__":
    app()

