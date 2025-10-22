"""Entrypoint script for running the Pluto-Duck backend locally.

This script is intended for desktop bundling (e.g., Tauri sidecar). It ensures
required directories exist before launching the FastAPI app with uvicorn.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Optional

import uvicorn

from pluto_duck_backend.app.core.config import (
    DEFAULT_DATA_ROOT,
    PlutoDuckSettings,
    get_settings,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Pluto-Duck backend server")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    parser.add_argument(
        "--data-root",
        type=Path,
        default=DEFAULT_DATA_ROOT,
        help="Root directory for Pluto-Duck data (logs, dbt, duckdb)",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        help="Override log level (e.g., INFO, DEBUG)",
    )
    return parser.parse_args()


def _prepare_environment(data_root: Path, log_level: Optional[str]) -> PlutoDuckSettings:
    os.environ.setdefault("PLUTODUCK_DATA_DIR__ROOT", str(data_root))
    if log_level:
        os.environ.setdefault("PLUTODUCK_LOG_LEVEL", log_level)

    settings = get_settings()
    settings.data_dir.ensure()
    return settings


def main() -> None:
    args = _parse_args()
    settings = _prepare_environment(args.data_root.expanduser(), args.log_level)

    uvicorn.run(
        "pluto_duck_backend.app.main:app",
        host=args.host,
        port=args.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()


