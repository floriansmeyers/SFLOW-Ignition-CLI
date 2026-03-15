# ignition-cli

CLI tool for the Ignition SCADA 8.3+ REST API. Built with Typer, httpx, and Pydantic.

## Quick Start

```bash
# Install from PyPI
pip install ignition-cli

# Configure a gateway connection (--webdev-project enables tag read/write)
ignition-cli config add dev --url https://gateway:8043 --token "keyId:secretKey" --webdev-project mcp-connector

# Test the connection
ignition-cli config test

# Check gateway status
ignition-cli gateway status
```

## Commands

| Command Group | Description | Key Commands |
|---|---|---|
| `config` | Manage gateway profiles | `init`, `add`, `list`, `show`, `test`, `set-default`, `remove` |
| `gateway` | Gateway operations | `status`, `info`, `backup`, `restore`, `modules`, `logs`, `loggers`, `log-download`, `scan-projects`, `scan-config`, `entity-browse` |
| `project` | Manage Ignition projects | `list`, `show`, `create`, `delete`, `export`, `import`, `copy`, `rename`, `resources`, `diff`, `watch` |
| `tag` | Tag operations | `browse`, `read`\*, `write`\*, `export`, `import`, `providers` |
| `device` | Device connections | `list`, `show`, `restart` (supports `--module`/`--type` for non-OPC-UA) |
| `resource` | Generic resource CRUD | `list`, `show`, `create`, `update`, `delete`, `names`, `types`, `upload`, `download` |
| `perspective` | Perspective views, pages, styles | `view list/show/create/update/delete/tree`, `page list/show/update`, `style list/show/create/update/delete`, `session show/update` |
| `mode` | Deployment modes | `list`, `show`, `create`, `update`, `delete`, `assign`, `unassign` |
| `api` | Raw API access | `get`, `post`, `put`, `delete`, `discover`, `spec` |

\* Tag `read` and `write` require the included SFLOW MCP Connector or a custom WebDev endpoint. Use `--webdev-project` to configure.

## Output Formats

All list/show commands support `--format` / `-f` with: `table` (default), `json`, `yaml`, `csv`.

```bash
ignition-cli project list -f json | jq '.[].name'
ignition-cli gateway status -f yaml
```

## Authentication

- **API Token** (recommended): `--token "keyId:secretKey"` (sent as `X-Ignition-API-Token` header)
- **HTTP Basic Auth**: `--username admin --password secret`
- **Environment variables**: `IGNITION_GATEWAY_URL`, `IGNITION_API_TOKEN`

## Tag Read/Write Setup

Tag `read` and `write` are not part of the standard Ignition REST API. They require a WebDev endpoint on the gateway.

**Recommended:** Install the included SFLOW MCP Connector (`contrib/mcp-connector.zip`) on your gateway. See `contrib/README.md` for instructions.

Then configure your profile with the WebDev project name:

```bash
ignition-cli config add dev --url https://gateway:8043 --token "keyId:secretKey" --webdev-project mcp-connector
```

Or pass it per-command:

```bash
ignition-cli tag read "[default]HMI/Temperature" --webdev-project mcp-connector
ignition-cli tag write "[default]HMI/Setpoint" 75.0 --webdev-project mcp-connector
```

Without `--webdev-project`, the CLI falls back to a direct `/tags/read` endpoint (non-standard, requires a custom module).

## Tools

### Perspective View Previewer

`tools/perspective-viewer.html` — a self-contained HTML file that renders Perspective view JSON locally in a browser. No server or dependencies required.

- **Paste JSON** or **drag & drop** a `.json` file
- **Load via URL parameter**: `?file=path` for Playwright automation
- **Keyboard shortcut**: `Ctrl/Cmd+Enter` to render
- **Controls**: Dark/light background, component outlines toggle, fit-to-pane scaling
- **Renders**: Coord/flex/column/drawing/breakpoint/tab/split containers, labels, buttons, inputs, vessel/pump/valve/motor/sensor symbols, SVG shapes (path, rect, circle, ellipse, polygon), embedded view placeholders

## Documentation

Run `ignition-cli --help` for full usage information. See [docs/usage.md](docs/usage.md) for the complete reference.

### Scenarios

8 production-ready automation scripts in [docs/scenarios/](docs/scenarios/overview.md) for tasks where the CLI provides unique value:

| # | Scenario | # | Scenario |
|---|----------|---|----------|
| 1 | [Tag Snapshot & Version Control](docs/scenarios/01-tag-snapshot-version-control.md) | 5 | [Tag Template Factory](docs/scenarios/05-tag-template-factory.md) |
| 2 | [Tag Diff Across Gateways](docs/scenarios/02-tag-diff-across-gateways.md) | 6 | [Upgrade Verification](docs/scenarios/06-upgrade-verification.md) |
| 3 | [Resource Inventory Export](docs/scenarios/03-resource-inventory-export.md) | 7 | [Compliance Audit Report](docs/scenarios/07-compliance-report/README.md) |
| 4 | [Bulk Device Commissioning](docs/scenarios/04-bulk-device-commissioning.md) | 8 | [Environment Cloning](docs/scenarios/08-environment-cloning.md) |

## Development

```bash
git clone https://github.com/floriansmeyers/SFLOW-Ignition-CLI.git
cd SFLOW-Ignition-CLI
pip install -e ".[dev]"
pytest tests/
```

## License

MIT
