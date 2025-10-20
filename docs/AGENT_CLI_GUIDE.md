# CLI Agent Quickstart (GPT-5 Provider)

Follow these steps to try the LangGraph-based agent from the terminal using a real OpenAI GPT-5 model.

## 1. Prerequisites
- Python 3.10+ with the project dependencies installed (`pip install -e .[dev]`).
- OpenAI account with access to the GPT-5 model family.
- A valid API key; store it securely (do not commit it to source control).

## 2. Configure the environment
Activate the project virtualenv and export the agent settings:

```bash
source .venv/bin/activate
export PLUTODUCK_AGENT__PROVIDER=openai
export PLUTODUCK_AGENT__MODEL=gpt-5.0-mini
export PLUTODUCK_AGENT__API_KEY="sk-your-openai-key"
```

You can also place these values in the repository `.env` file:

```
PLUTODUCK_AGENT__PROVIDER=openai
PLUTODUCK_AGENT__MODEL=gpt-5.0-mini
PLUTODUCK_AGENT__API_KEY=sk-your-openai-key
```

## 3. Run the agent once
Execute a natural-language question; the agent will plan, generate SQL, and verify the result before printing the final payload:

```bash
pluto-duck agent "List the top 5 customers by total orders"
```

## 4. Stream structured events
For live updates (reasoning, plan, SQL, verifier output), use the streaming command:

```bash
pluto-duck agent-stream "Show daily revenue for the last 7 days"
```

Each event is printed as JSON and mirrors the payload from the `/api/v1/agent/{run_id}/events` SSE endpoint (see `docs/ARCHITECTURE.md` for schema details).

## 5. Troubleshooting
- Ensure the DuckDB warehouse path in `~/.pluto-duck/data/warehouse.duckdb` exists; the first CLI run will create it automatically.
- If the agent reports authentication failures, re-check `PLUTODUCK_AGENT__API_KEY`.
- For debugging or offline development, you can fall back to the mock provider by setting `PLUTODUCK_AGENT__MOCK_MODE=true`.
