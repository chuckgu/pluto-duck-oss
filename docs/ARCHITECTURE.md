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

## Agent Event Stream

The agent orchestrator uses LangGraph to emit structured events over Server-Sent Events (SSE) and the CLI stream command. Each event contains `type`, `subtype`, `content`, and `timestamp` fields:

- `reasoning.start` / `reasoning.chunk`: LLM controller updates. `content` includes the latest decision (planner/schema/sql/verifier/finalize) and an optional reasoning message.
- `tool.chunk` / `tool.end`: Tool execution snapshots.
  - `planner`: emits the current plan as an array of `{description, status, metadata}`.
  - `schema`: shares the `schema_preview` table list.
  - `sql`: includes the generated SQL statement.
  - `verifier`: provides query verification result metadata (`job_id`, `result_table`, `rows_affected`, `error`).
- `message.final`: Finalization payload with context flags (e.g., `finished: true`).
- `run.chunk` / `run.end` / `run.error`: Generic updates for nodes without specialized handlers and overall completion/error states.

Consumers (CLI, frontend) should parse the `content` object based on `type`/`subtype`. The `/api/v1/agent/{run_id}/events` endpoint streams these events; `pluto-duck agent-stream` prints them for debugging.

Agent responses are also available via `/api/v1/agent/{run_id}/events` as SSE streams. Each event carries structured JSON describing reasoning updates, tool outputs, and final summaries (see `docs/ARCHITECTURE.md`).

For hands-on CLI usage with a real GPT-5 provider, follow `docs/AGENT_CLI_GUIDE.md`.

