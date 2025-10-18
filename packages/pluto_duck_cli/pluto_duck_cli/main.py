"""Typer-based CLI for Pluto-Duck."""

import typer


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


if __name__ == "__main__":
    app()

