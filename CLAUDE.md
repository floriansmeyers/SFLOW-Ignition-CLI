# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

SFLOW Ignition CLI — a Python CLI tool for the Ignition SCADA 8.3+ REST API. Built with Typer, httpx, and Pydantic. Manages gateways, projects, tags, devices, and resources.

## Tech Stack

- **Language:** Python 3.10+
- **CLI framework:** Typer (with Rich markup)
- **HTTP client:** httpx
- **Data models:** Pydantic v2
- **Config format:** TOML (tomli-w)
- **Build system:** Hatchling

## Project Structure

```
src/ignition_cli/
├── app.py              # Root Typer app, command group registration
├── client/             # HTTP client (auth, gateway API, errors)
├── commands/           # CLI commands (config, gateway, project, tag, device, resource, api)
├── config/             # Config manager, models, constants
├── models/             # Pydantic models (gateway, project, tag, device, resource)
├── output/             # Table formatting and output helpers
└── utils/              # Diff, file watching utilities
tests/
├── unit/               # Unit tests (config, client, output)
├── integration/        # Integration tests (all command groups)
└── e2e/                # End-to-end tests (requires live gateway)
```

## Common Commands

```bash
# Install in development mode
pip install -e ".[dev]"

# Run the CLI
ignition-cli --help

# Run tests
pytest
pytest tests/unit/               # Unit tests only
pytest tests/integration/        # Integration tests only
pytest -m "not e2e"              # Skip e2e tests

# Linting and type checking
ruff check src/ tests/
mypy
```

## Conventions

- All modules use `from __future__ import annotations`
- Commands are organized as Typer sub-apps registered in `app.py`
- Test fixtures live in `tests/conftest.py`
- e2e tests are marked with `@pytest.mark.e2e`

## Allowed Tools

- WebSearch
- WebFetch
- Bash(pip install *)
- Bash(pip *)
- Bash(python *)
- Bash(pytest *)
- Bash(ruff *)
- Bash(mypy *)
- Bash(ignition-cli *)
- Bash(git *)
- Bash(gh *)
- Bash(ls *)
- Bash(cat *)
- Bash(which *)
- Bash(echo *)
