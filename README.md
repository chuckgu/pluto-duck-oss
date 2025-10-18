# Pluto-Duck OSS

Local-first analytics studio powered by DuckDB, dbt, and an AI-assisted query agent.

## Vision

Build a personal data IDE that keeps your data and compute on your machine while offering
ergonomic ingestion, modeling, and natural-language querying capabilities.

## Project Layout

- `backend/pluto_duck_backend`: FastAPI service, ingestion/transformation engines, and AI agent.
- `packages/pluto_duck_cli`: Typer-based CLI entrypoint (`pluto-duck`).
- `frontend/pluto_duck_frontend`: Minimal chat/front-end client (placeholder).
- `dbt_projects/core`: Reference dbt project used by the transformation service.
- `legacy/`: Snapshot of prior closed-source implementation for reference only (ignored by git).

## Getting Started

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .[dev]

# Run linters/tests
ruff check backend packages
mypy backend packages
pytest backend

# Run API locally
pluto-duck run
```

## Roadmap Highlights

- Phase 1: Extract clean OSS backend, focus on ingestion, dbt integration, public API, CLI.
- Phase 2: Ship minimal chat frontend for end-to-end local experience.
- Phase 3: Prepare for optional managed/cloud offering with premium features.

See `.cursor/plans/pluto-duck-re-architecture-plan-9662a618.plan.md` and
`.cursor/plans/backend-spec.plan.md` for detailed design notes.

