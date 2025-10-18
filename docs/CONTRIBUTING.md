# Contributing to Pluto-Duck OSS

Thanks for your interest in improving Pluto-Duck! This document describes how to set up a
development environment and the expectations for pull requests.

## Getting Started

1. Clone the repository and create a virtual environment.
2. Install dependencies with development extras:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -e .[dev]
   ```

3. Copy `.env.example` to `.env` (if present) and adjust settings as needed.

## Coding Standards

- Format & lint using [Ruff](https://docs.astral.sh/ruff/) and static type check with mypy:

  ```bash
  ruff check backend packages
  mypy backend packages
  ```

- Write tests with pytest and place them under `backend/tests/` or `packages/*/tests` as
  appropriate.

- Run the full suite before submitting a PR:

  ```bash
  pytest
  ```

## Workflow

- Feature branches should target `main` via pull requests.
- Ensure your PR description references relevant issues or plans (`plans/implementation-plan.md`).
- Add or update documentation when behavior changes.
- Squash commits if necessary before merge to keep history clean.

## Communication

- Use GitHub Issues for bug reports or feature requests.
- Join discussions in the community channels (see README) to coordinate larger efforts.

We welcome contributions of all sizes—bug fixes, documentation, connectors, and more. Thank you!

