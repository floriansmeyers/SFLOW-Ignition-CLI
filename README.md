# ignition-cli

CLI tool for the Ignition SCADA 8.3+ REST API. Built with Typer, httpx, and Pydantic.

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Configure a gateway connection
ignition-cli config add dev --url https://gateway:8043 --token "keyId:secretKey"

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
| `mode` | Deployment modes | `list`, `show`, `create`, `update`, `delete` |
| `api` | Raw API access | `get`, `post`, `put`, `delete`, `discover`, `spec` |

\* Tag `read` and `write` are non-standard endpoints requiring a WebDev module or custom gateway extension.

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

## Documentation

Run `ignition-cli --help` for full usage information. See [docs/usage.md](docs/usage.md) for the complete reference.

## License

MIT
