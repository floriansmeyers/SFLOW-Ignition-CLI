# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

SFLOW Ignition CLI — a Python CLI tool for the Ignition SCADA 8.3+ REST API. Built with Typer, httpx, and Pydantic. Manages gateways, projects, tags, devices, resources, deployment modes, and binary datafiles.

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
├── client/
│   ├── auth.py         # APITokenAuth, BasicAuth, resolve_auth
│   ├── errors.py       # Exception hierarchy, error_handler decorator
│   └── gateway.py      # GatewayClient (HTTP, pagination, streaming, OpenAPI)
├── commands/
│   ├── _common.py      # Shared helpers (make_client, extract_items, validate_resource_type, type aliases)
│   ├── api.py          # Raw API access + discover/spec
│   ├── config_cmd.py   # Profile management (init, add, test, etc.)
│   ├── device.py       # Device list/show/restart (configurable module/type)
│   ├── gateway.py      # Status, info, backup, restore, modules, logs, entity-browse
│   ├── modes.py        # Deployment mode CRUD
│   ├── perspective.py  # Perspective views, pages, styles, session props (export/import cycle)
│   ├── project.py      # Project CRUD, export/import, copy/rename, diff, watch
│   ├── resource.py     # Generic resource CRUD, upload/download datafiles
│   └── tag.py          # Tag browse, read, write, export, import, providers
├── config/
│   ├── constants.py    # API base path, defaults
│   ├── manager.py      # ConfigManager (TOML read/write, profile resolution)
│   └── models.py       # GatewayProfile, CLIConfig Pydantic models
├── models/             # Pydantic models (gateway, project, tag, device, resource, mode, perspective, common)
├── output/
│   ├── formatter.py    # output() dispatcher (JSON, YAML, CSV, table)
│   └── tables.py       # Rich table builders
└── utils/
    ├── diff.py         # Project diff utility
    └── file_watcher.py # File watch + sync
tests/
├── conftest.py         # Shared fixtures (config, gateway mocks)
├── unit/               # Unit tests (errors, formatter, config, client, models, helpers)
├── integration/        # Integration tests (all command groups with respx mocks)
└── e2e/                # End-to-end tests (requires live gateway, @pytest.mark.e2e)
tools/
└── perspective-viewer.html  # Local HTML renderer for previewing Perspective view JSON
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

## Post-Implementation Checklist

After every implementation task, always:

1. **Run the test suite** — `pytest tests/` must pass with zero failures
2. **Update documentation** — keep these files in sync with the code:
   - `CLAUDE.md` — project structure, commands, conventions
   - `README.md` — quick start, command list
   - `docs/usage.md` — full command reference with options, arguments, and examples

## Ignition 8.3 API Notes

- API base path: `/data/api/v1/`
- Auth header: `X-Ignition-API-Token: keyId:secretKey`
- OpenAPI spec at gateway root: `GET /openapi.json`
- Gateway info endpoint: `GET /gateway-info` (NOT `/status/info`)
- Deployment modes endpoint is `/mode` (singular), not `/modes`
- `GET /mode` returns `{ "items": [...] }` — no `GET /mode/{name}` exists
- `PUT /mode/{name}` requires `name` in the request body
- Mode model fields: `name`, `title`, `description`, `resourceCount`
- Resource delete: `DELETE /resources/{module}/{type}/{name}/{signature}` (NOT POST)
- Binary datafiles: `PUT/GET/DELETE /resources/datafile/{module}/{type}/{name}/{filename}`
- Datafile upload requires `?signature=` query param (from the resource's `signature` field)
- Resource file lists are returned in the `data` field (not `files`)
- Scan endpoints: `POST /scan/projects`, `POST /scan/config` (fire-and-forget, no body)
- Entity browse: `GET /entity/browse?path=X&depth=N`
- Tag read/write endpoints are non-standard (require WebDev module or custom extension)
- Tag export: `GET /tags/export?provider=X&type=json` — `type` param is **required** (json, xml)
- Tag import: `POST /tags/import?provider=X&type=json&collisionPolicy=MergeOverwrite` — `type` and `collisionPolicy` are **required**
- Resource create/update: `POST/PUT /resources/{module}/{type}` expects a **JSON array** of objects, not a single object
- Resource update (`PUT`) requires `signature` field in request body
- Mode-scoped resources: `POST /resources/{module}/{type}` with `"collection": "mode_name"` in the body to assign a resource to a mode
- Mode-scoped resource lookup: `GET /resources/find/{module}/{type}/{name}?collection=mode_name` — returns the mode-specific signature (different from the base resource signature)
- Mode-scoped resource delete: `DELETE /resources/{module}/{type}/{name}/{signature}?collection=mode_name&confirm=true` — must use the mode-specific signature and `confirm=true` when references exist
- Singleton resources: `GET /resources/singleton/{module}/{type}` — no name required; accepts `?collection=X` and `?defaultIfUndefined=true`
- Singleton resources share the same `POST/PUT /resources/{module}/{type}` create/update endpoints as named resources
- `resource show`, `resource update`, `mode assign`, `mode unassign` accept optional name — omit for singletons
- Perspective views, pages, styles, and session-props are **project-scoped** — NOT exposed via the gateway resource API
- Perspective resources are only accessible via the project export/import cycle (export zip → modify files → import with `overwrite=true`)
- Project zip structure for Perspective: `com.inductiveautomation.perspective/views/{path}/view.json`, `style-classes/{name}/style.json`, `page-config/config.json`, `session-props/props.json`
- Each Perspective resource has a `resource.json` with metadata (`scope`, `version`, `restricted`, `overridable`, `files`, `attributes`)
