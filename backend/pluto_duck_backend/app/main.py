"""FastAPI application factory for the Pluto-Duck backend."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pluto_duck_backend import __version__
from pluto_duck_backend.app.api.router import api_router
from pluto_duck_backend.app.core.config import get_settings


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""

    # Ensure settings and filesystem layout are prepared during startup
    settings = get_settings()

    app = FastAPI(
        title="Pluto-Duck API",
        version=__version__,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Local-first; tighten once auth is added
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )

    @app.get("/health", tags=["health"], summary="Health check")
    def health() -> dict[str, str]:
        """Return a simple status payload for readiness checks."""

        return {
            "status": "ok",
            "version": __version__,
            "provider": settings.agent.provider,
        }

    app.include_router(api_router)

    return app


# ASGI entrypoint for uvicorn / hypercorn
app = create_app()


