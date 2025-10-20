# Phase 2 Frontend MVP Plan

## 1. Context & Goals
- Deliver Phase 2 scope from `implementation-plan.md`: ship a frontend MVP that consumes the LangGraph agent’s SSE stream, guides configuration, and mirrors CLI/backend workflows.
- Maintain local-first development, reuse FastAPI services, and keep the frontend loosely coupled so it can evolve independently of backend release cadence.
- Target `pluto_duck_frontend/` (currently empty) as the home for the new app.

## 2. Guiding Principles
- **Streaming-first UX**: prioritize real-time surfaces for reasoning, tool snapshots, and final answers.
- **Parity with CLI/API**: all workflows (ingest, dbt, query) should be reproducible end-to-end via the UI.
- **Extensibility**: modular state management, theming, and integration layers to support future personas and provider swaps.
- **Type safety & testing**: TypeScript throughout, shared schema packages where practical, and automated regression coverage.

## 3. Tech Stack Decisions
- **Frontend framework**: Vite + React + TypeScript for fast iteration; consider Next.js only if SSR is required in later phases.
- **Styling**: Tailwind CSS with design tokens to enable theming; fallback option is Chakra UI if prefabs are needed quickly.
- **State management**: Zustand or Redux Toolkit Query for streaming data; final choice gated on complexity of SSE handling.
- **SSE consumption**: Evaluate integrating Vercel AI SDK hooks (`useChat`, `streamText`) for event handling and reconnection logic. Adapter layer will map Pluto-Duck event schema to SDK message format [AI SDK Docs](https://ai-sdk.dev/docs/introduction).
- **Backend bridge**: FastAPI remains the authoritative API surface. Reference the Vercel `next-fastapi` example for proxying SSE and REST calls when hosting UI alongside API [Next.js + FastAPI 예제](https://github.com/vercel/ai/tree/main/examples/next-fastapi).
- **Testing**: Vitest + React Testing Library for unit/component tests; Playwright for end-to-end flows including SSE.

## 4. Milestones & Deliverables

### Milestone F — Frontend Scaffold (Week 7)
- Initialize Vite React app in `pluto_duck_frontend/` with ESLint, Prettier, testing stack, and CI lint/test jobs.
- Establish folder structure (`app/`, `components/`, `hooks/`, `lib/`, `styles/`).
- Implement global layout, navigation shell, theming/tokens.
- Add API client module wrapping REST endpoints (`/api/v1/query`, `/agent/run`, etc.).
- Spike on SSE hook: compare native `EventSource`, custom hook, and AI SDK integration. Document decision.

### Milestone G — Agent Chat UI (Week 8)
- Build chat interface with message list, input form, run history, and status indicators.
- Render event-specific cards (planner plan list, schema preview, SQL candidate, verifier result). Ensure compatibility with existing JSON event schema.
- Implement SSE subscription with reconnection, cancellation, and error handling; surface network state in UI.
- Add unit tests for components and hook coverage for SSE logic.
- Provide Storybook (optional) or mock data playground to iterate on event rendering.

### Milestone H — Onboarding & Settings (Week 9)
- Design onboarding wizard for DuckDB path, dbt project path, connector setup.
- Integrate with FastAPI settings endpoints (extend if needed) to validate and persist configuration.
- Mirror CLI configuration semantics, reusing shared schema models via generated TypeScript types.
- Ensure accessibility basics: keyboard navigation, ARIA labels, focus management.

### Milestone I — E2E & Release Prep (Week 10)
- Implement end-to-end test covering ingest → dbt run → agent query using Playwright against local backend.
- Harden error handling, toasts, logging, and telemetry toggles.
- Document local setup, `.env` expectations, and run instructions in README and docs.
- Prepare build scripts (e.g., `pnpm build`, container integration) and ensure CI passes.

## 5. Integration Tasks
- Define TypeScript types mirroring `AgentEvent` schema; consider generating from backend Pydantic models via `datamodel-codegen` or manual sync.
- Provide mock SSE server or recorded event fixtures for offline UI development.
- Create shared utilities for formatting SQL, plan steps, and result tables.
- Align authentication/session story between frontend and FastAPI (initially local-only, but keep extension points for tokens).

## 6. Risks & Mitigations
- **Schema drift** between backend events and UI expectations → add contract tests and versioning in `backend/tests/api/test_agent_api.py` to detect changes early.
- **SSE stability** under flaky networks → leverage AI SDK reconnect helpers or implement exponential backoff in custom hook.
- **Configuration divergence** across CLI/API/UI → centralize settings loading through existing backend services; validate after onboarding wizard completes.
- **Scope creep** into advanced visualizations → lock MVP feature list; track stretch goals separately.

## 7. Success Criteria
- Agent chat UI displays reasoning/tool/final events in real time using LangGraph SSE.
- Users can configure data sources and dbt project entirely via the frontend and execute a query end-to-end.
- Automated tests (unit, component, Playwright) run in CI and pass with backend Phase 1 services.
- Docs updated so a new contributor can set up frontend + backend locally within 30 minutes.

## 8. Follow-up & Stretch Goals
- Evaluate design system abstraction or component library adoption once MVP usage is validated.
- Consider WebSocket or gRPC streaming if SSE proves limiting.
- Explore multi-run timeline view and persistent chat histories in Phase 3.
- Add opt-in telemetry dashboards once privacy posture is defined.

