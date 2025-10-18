# Pluto-Duck OSS Architecture Overview

This document summarizes the target architecture. For full detail, refer to
`.cursor/plans/backend-spec.plan.md` and `.cursor/plans/pluto-duck-re-architecture-plan-9662a618.plan.md`.

## Layers

1. **CLI & API**
   - `packages/pluto_duck_cli`: Typer-based CLI.
   - `backend/pluto_duck_backend/app/api`: FastAPI server exposing public endpoints.
2. **Services**
   - Ingestion (`app/services/ingestion`): pluggable connectors stream data into DuckDB.
   - Transformation (`app/services/transformation`): thin wrapper around dbt CLI.
   - Execution (`app/services/execution`): DuckDB query execution and metadata capture.
3. **Agent**
   - `backend/pluto_duck_backend/agent`: LangGraph-compatible workflow for NL query planning, SQL generation, verification, and result assembly.
4. **Infrastructure**
   - Local DuckDB warehouse, artifacts directory, configuration store.

## Data Layout

- Default root: `~/.pluto-duck/`
  - `data/warehouse.duckdb`
  - `artifacts/dbt/`
  - `artifacts/queries/`
  - `configs/`

## Packaging

- Python package published as `pluto-duck` with extras for connectors and dbt.
- Docker image to follow (`docker run -p 8000:8000 pluto-duck:oss`).
- CLI entrypoint: `pluto-duck`.

## Testing Strategy

- Unit tests for connectors, config parsing, agent nodes.
- Integration tests with DuckDB fixtures and dbt sample project.
- CLI smoke tests via pytest subprocess.

