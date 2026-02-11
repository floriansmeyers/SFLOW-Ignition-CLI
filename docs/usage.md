# ignition-cli Usage Guide

Complete reference for the `ignition-cli` command-line tool for Ignition SCADA 8.3+ gateway management.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Installation](#2-installation)
3. [Quick Start](#3-quick-start)
4. [Configuration](#4-configuration)
5. [Authentication](#5-authentication)
6. [Output Formats](#6-output-formats)
7. [Command Reference](#7-command-reference)
   - [Common Options](#common-options)
   - [config](#config) (7 commands)
   - [gateway](#gateway) (11 commands)
   - [project](#project) (11 commands)
   - [tag](#tag) (6 commands)
   - [device](#device) (3 commands)
   - [resource](#resource) (9 commands)
   - [mode](#mode) (7 commands)
   - [api](#api) (6 commands)
8. [Common Workflows](#8-common-workflows)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Overview

`ignition-cli` is a command-line tool for managing Inductive Automation's Ignition SCADA 8.3+ gateways through their REST API. It provides structured access to gateway configuration, projects, tags, device connections, and generic resources without needing to interact with the gateway web UI.

### Target Audience

- **SCADA integrators** managing multiple Ignition gateways across sites
- **DevOps engineers** automating gateway provisioning, backups, and CI/CD pipelines
- **Developers** working with Ignition projects and needing scriptable tag/resource management

### Capabilities

- Manage multiple gateway connections through named profiles
- View gateway status, version info, modules, and logs
- Trigger project and config scans without gateway restart
- Create, export, import, delete, and diff Ignition projects
- Browse, read, write, export, and import tags
- List and inspect OPC-UA device connections
- Generic CRUD operations on any gateway resource type
- Upload and download binary datafiles (fonts, themes, icons, drivers)
- Manage deployment modes (dev/staging/prod)
- Raw API access to arbitrary gateway endpoints
- Discover available API endpoints from the gateway's OpenAPI spec
- Output in table, JSON, YAML, or CSV format

### Requirements

- Python 3.10 or later (3.10, 3.11, 3.12, 3.13)
- An Ignition SCADA 8.3+ gateway with the REST API enabled

---

## 2. Installation

### From PyPI

```bash
pip install ignition-cli
```

### With file-watching support

The `project watch` command requires the optional `watchfiles` dependency:

```bash
pip install "ignition-cli[watch]"
```

### From source

```bash
git clone https://github.com/SFLOW-Ignition-CLI/ignition-cli.git
cd ignition-cli
pip install -e ".[dev]"
```

### Verify installation

```bash
ignition-cli --version
# ignition-cli 0.1.0
```

---

## 3. Quick Start

### Step 1: Create your first gateway profile

```bash
ignition-cli config init
```

The interactive wizard prompts for:

| Prompt | Example |
|---|---|
| Profile name | `default` |
| Gateway URL | `https://gateway:8043` |
| API Token | `myKeyId:mySecretKey` |
| Verify SSL? | `Yes` |

### Step 2: Test the connection

```bash
ignition-cli config test
```

Expected output:

```
Testing connection to https://gateway:8043...
Connected! Gateway: MyGateway v8.3.2
```

### Step 3: Run your first commands

```bash
# List projects on the gateway
ignition-cli project list

# Check gateway status
ignition-cli gateway status

# Browse the tag tree
ignition-cli tag browse
```

### Step 4: Try different output formats

```bash
# JSON output
ignition-cli project list --format json

# Pipe to jq
ignition-cli project list -f json | jq '.[].name'

# CSV for spreadsheets
ignition-cli project list -f csv > projects.csv
```

---

## 4. Configuration

### Config File Location

The configuration file is stored using platform-standard directories (via `platformdirs`):

| Platform | Path |
|---|---|
| Linux | `~/.config/ignition-cli/config.toml` |
| macOS | `~/Library/Application Support/ignition-cli/config.toml` |
| Windows | `%LOCALAPPDATA%\SFLOW\ignition-cli\config.toml` |

The app name is `ignition-cli` and the author is `SFLOW`.

### TOML Format

```toml
default_profile = "production"

[profiles.production]
url = "https://prod-gateway:8043"
token = "keyId:secretKey"

[profiles.development]
url = "https://dev-gateway:8088"
token = "devKeyId:devSecret"
verify_ssl = false
timeout = 60.0
```

### Profile Fields

| Field | Type | Default | Description |
|---|---|---|---|
| `url` | string | *(required)* | Gateway base URL (must start with `http://` or `https://`) |
| `token` | string | `null` | API token in `keyId:secretKey` format |
| `username` | string | `null` | HTTP basic auth username |
| `password` | string | `null` | HTTP basic auth password |
| `verify_ssl` | boolean | `true` | Verify SSL/TLS certificates (prints warning when disabled) |
| `timeout` | float | `30.0` | HTTP request timeout in seconds (range: 0–600) |

Fields at their default values (`verify_ssl = true`, `timeout = 30.0`) are omitted from the config file to keep it clean.

### Global Settings

| Field | Type | Default | Description |
|---|---|---|---|
| `default_profile` | string | *(first added)* | Name of the default gateway profile |
| `default_format` | string | `"table"` | Default output format |

### Environment Variables

| Variable | Overrides | Example |
|---|---|---|
| `IGNITION_GATEWAY_URL` | Profile URL | `https://gateway:8043` |
| `IGNITION_API_TOKEN` | Profile token | `keyId:secretKey` |
| `IGNITION_GATEWAY_PROFILE` | Default profile selection | `production` |

### Resolution Precedence

Gateway connection parameters are resolved in this order (highest priority first):

1. **CLI flags** (`--url`, `--token`, `--gateway`)
2. **Environment variables** (`IGNITION_GATEWAY_URL`, `IGNITION_API_TOKEN`, `IGNITION_GATEWAY_PROFILE`)
3. **Config file** (default profile or named profile)

For example, if you have a `production` profile in your config but pass `--url https://other:8043`, the CLI flag wins.

---

## 5. Authentication

### API Token (recommended)

The preferred method. Tokens use the format `keyId:secretKey` and are sent as the `X-Ignition-API-Token` HTTP header on every request.

Set up via config:

```bash
ignition-cli config add prod --url https://gateway:8043 --token "myKeyId:mySecretKey"
```

Or via environment variable:

```bash
export IGNITION_API_TOKEN="myKeyId:mySecretKey"
```

### HTTP Basic Auth

Fall back to basic authentication when API tokens are not available:

```bash
ignition-cli config add prod --url https://gateway:8043 --username admin --password secret
```

### Resolution Logic

Authentication is resolved from the gateway profile in this order:

1. If `token` is set, use API token auth (`X-Ignition-API-Token` header)
2. If `username` **and** `password` are set, use HTTP basic auth
3. Otherwise, no authentication is sent

A profile is considered to have auth configured if either condition 1 or 2 is met.

### SSL Verification

By default, SSL certificates are verified. To disable (e.g., for self-signed certificates in development):

```bash
# When adding a profile
ignition-cli config add dev --url https://dev:8043 --token "key:secret" --no-verify-ssl

# Or set verify_ssl = false in config.toml
```

---

## 6. Output Formats

Most commands accept `--format` / `-f` to control output rendering. Four formats are available:

### Table (default)

Rich-formatted tables for terminal display. Key-value data is shown as a two-column table.

```bash
ignition-cli project list
# ┌──────────┬────────────────┬─────────┬─────────┬─────────────────────┐
# │ Name     │ Title          │ Enabled │ State   │ Last Modified       │
# ├──────────┼────────────────┼─────────┼─────────┼─────────────────────┤
# │ MyApp    │ My Application │ True    │ Running │ 2025-01-15 10:30:00 │
# │ TestProj │ Test Project   │ True    │ Running │ 2025-01-14 08:00:00 │
# └──────────┴────────────────┴─────────┴─────────┴─────────────────────┘
```

### JSON

Structured JSON output, ideal for piping to `jq` or scripting.

```bash
ignition-cli project list -f json
```

```json
[
  {
    "name": "MyApp",
    "title": "My Application",
    "enabled": true,
    "state": "Running"
  }
]
```

### YAML

YAML output for configuration file workflows.

```bash
ignition-cli gateway status -f yaml
```

```yaml
name: MyGateway
version: 8.3.2
edition: standard
state: RUNNING
```

### CSV

Comma-separated values for spreadsheet import. Only available for tabular (list) data; falls back to JSON for key-value data.

```bash
ignition-cli project list -f csv > projects.csv
```

### Piping Tips

```bash
# Extract project names with jq
ignition-cli project list -f json | jq -r '.[].name'

# Count modules
ignition-cli gateway modules -f json | jq 'length'

# Save to CSV for Excel
ignition-cli device list -f csv > devices.csv

# Pretty-print YAML
ignition-cli gateway info -f yaml | less
```

---

## 7. Command Reference

### Common Options

These options are available on every command that communicates with a gateway:

| Option | Short | Description |
|---|---|---|
| `--gateway` | `-g` | Gateway profile name to use |
| `--url` | | Gateway URL override (takes precedence over profile) |
| `--token` | | API token override (takes precedence over profile) |
| `--format` | `-f` | Output format: `table`, `json`, `yaml`, `csv` |

Global options on the root `ignition-cli` command:

| Option | Short | Description |
|---|---|---|
| `--version` | `-V` | Show version and exit |
| `--help` | | Show help and exit |

---

### config

Manage gateway profiles and CLI configuration.

```
ignition-cli config <command>
```

#### config init

Interactive setup wizard to create your first gateway profile.

```bash
ignition-cli config init
```

Prompts for profile name, gateway URL, API token, and SSL verification preference. The created profile is automatically set as the default.

**Example:**

```bash
$ ignition-cli config init
Ignition CLI Setup Wizard

Profile name [default]:
Gateway URL (e.g. https://gateway:8043): https://prod:8043
API Token (keyId:secretKey) [None]: abc123:secret456
Verify SSL certificates? [y/N]: y

Profile 'default' saved and set as default.
Config file: /home/user/.config/ignition-cli/config.toml
```

---

#### config add

Add a gateway profile non-interactively.

```bash
ignition-cli config add <name> --url <url> [options]
```

**Arguments:**

| Argument | Description |
|---|---|
| `name` | Profile name |

**Options:**

| Option | Short | Required | Description |
|---|---|---|---|
| `--url` | `-u` | Yes | Gateway URL |
| `--token` | `-t` | No | API token (`keyId:secretKey`) |
| `--username` | | No | Basic auth username |
| `--password` | | No | Basic auth password |
| `--no-verify-ssl` | | No | Disable SSL certificate verification |
| `--default` | | No | Set this profile as the default |

**Examples:**

```bash
# Token auth
ignition-cli config add production --url https://prod:8043 --token "keyId:secret"

# Basic auth with default
ignition-cli config add dev --url https://dev:8088 --username admin --password pass --default

# No SSL verification
ignition-cli config add local --url https://localhost:8043 --token "key:secret" --no-verify-ssl
```

---

#### config list

List all configured profiles.

```bash
ignition-cli config list [--format <fmt>]
```

**Options:**

| Option | Short | Description |
|---|---|---|
| `--format` | `-f` | Output format (default: `table`) |

**Example:**

```bash
$ ignition-cli config list
┌────────────┬──────────────────────────┬───────┬─────────┐
│ Name       │ URL                      │ Auth  │ Default │
├────────────┼──────────────────────────┼───────┼─────────┤
│ production │ https://prod:8043        │ token │ *       │
│ dev        │ https://dev:8088         │ basic │         │
└────────────┴──────────────────────────┴───────┴─────────┘
```

---

#### config show

Show details for a specific profile. Token and password values are masked in the output.

```bash
ignition-cli config show <name> [--format <fmt>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `name` | Profile name |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--format` | `-f` | Output format (default: `table`) |

**Example:**

```bash
$ ignition-cli config show production
┌────────────┬──────────────────────────┐
│ Key        │ Value                    │
├────────────┼──────────────────────────┤
│ name       │ production               │
│ url        │ https://prod:8043        │
│ token      │ ***                      │
│ verify_ssl │ True                     │
│ timeout    │ 30.0                     │
└────────────┴──────────────────────────┘
```

---

#### config set-default

Set the default gateway profile.

```bash
ignition-cli config set-default <name>
```

**Arguments:**

| Argument | Description |
|---|---|
| `name` | Profile name to set as default |

**Example:**

```bash
ignition-cli config set-default production
# Default profile set to 'production'.
```

---

#### config test

Test connectivity to a gateway. Uses the default profile if no name is provided.

```bash
ignition-cli config test [name]
```

**Arguments:**

| Argument | Description |
|---|---|
| `name` | Profile name (optional; uses default profile if omitted) |

**Example:**

```bash
$ ignition-cli config test production
Testing connection to https://prod:8043...
Connected! Gateway: ProductionGW v8.3.2
```

---

#### config remove

Remove a gateway profile. Prompts for confirmation unless `--force` is used. If the removed profile was the default, the next available profile becomes the new default.

```bash
ignition-cli config remove <name> [--force]
```

**Arguments:**

| Argument | Description |
|---|---|
| `name` | Profile name to remove |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--force` | `-f` | Skip confirmation prompt |

**Example:**

```bash
$ ignition-cli config remove dev
Remove profile 'dev'? [y/N]: y
Profile 'dev' removed.
```

---

### gateway

Gateway status, backups, modules, and logs.

```
ignition-cli gateway <command>
```

#### gateway status

Show gateway status and system info as a key-value table.

```bash
ignition-cli gateway status [--gateway <profile>] [--url <url>] [--token <token>] [--format <fmt>]
```

**Options:**

| Option | Short | Description |
|---|---|---|
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |
| `--format` | `-f` | Output format (default: `table`) |

**Example:**

```bash
ignition-cli gateway status
ignition-cli gateway status -g production -f json
```

---

#### gateway info

Show gateway version, edition, and OS details as a key-value table.

```bash
ignition-cli gateway info [--gateway <profile>] [--url <url>] [--token <token>] [--format <fmt>]
```

**Options:**

| Option | Short | Description |
|---|---|---|
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |
| `--format` | `-f` | Output format (default: `table`) |

**Example:**

```bash
ignition-cli gateway info
ignition-cli gateway info -f yaml
```

---

#### gateway backup

Download a gateway backup archive (`.gwbk` file).

```bash
ignition-cli gateway backup [--output <path>] [--gateway <profile>] [--url <url>] [--token <token>]
```

**Options:**

| Option | Short | Description |
|---|---|---|
| `--output` | `-o` | Output file path (default: `gateway-backup.gwbk`) |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |

**Example:**

```bash
# Default filename
ignition-cli gateway backup

# Custom filename
ignition-cli gateway backup -o backups/prod-2025-01-15.gwbk
```

---

#### gateway restore

Restore a gateway from a backup file. Prompts for confirmation unless `--force` is used. Uses streaming upload to handle large backup files without loading them entirely into memory.

```bash
ignition-cli gateway restore <file> [--force] [--gateway <profile>] [--url <url>] [--token <token>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `file` | Path to the `.gwbk` backup file |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--force` | | Skip confirmation prompt |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |

**Example:**

```bash
ignition-cli gateway restore backups/prod-2025-01-15.gwbk
# Restore backup to gateway 'default'? This will overwrite the current configuration [y/N]: y
# Backup restore initiated.

ignition-cli gateway restore backups/prod-2025-01-15.gwbk --force
```

---

#### gateway modules

List installed gateway modules. Use `--quarantined` to see quarantined modules instead.

```bash
ignition-cli gateway modules [--quarantined] [--gateway <profile>] [--url <url>] [--token <token>] [--format <fmt>]
```

**Options:**

| Option | Short | Description |
|---|---|---|
| `--quarantined` | `-q` | Show quarantined modules instead of healthy ones |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |
| `--format` | `-f` | Output format (default: `table`) |

**Example:**

```bash
# Healthy modules
ignition-cli gateway modules

# Quarantined modules
ignition-cli gateway modules --quarantined

# JSON output
ignition-cli gateway modules -f json
```

---

#### gateway logs

View gateway log entries.

```bash
ignition-cli gateway logs [--lines <n>] [--level <level>] [--gateway <profile>] [--url <url>] [--token <token>] [--format <fmt>]
```

**Options:**

| Option | Short | Description |
|---|---|---|
| `--lines` | `-n` | Number of log lines to retrieve (default: `50`) |
| `--level` | `-l` | Minimum log level filter (e.g. `WARN`, `ERROR`) |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |
| `--format` | `-f` | Output format (default: `table`) |

**Example:**

```bash
# Last 50 log entries (default)
ignition-cli gateway logs

# Last 100 entries, errors only
ignition-cli gateway logs -n 100 --level ERROR

# JSON output for processing
ignition-cli gateway logs -f json | jq '.[] | select(.level == "ERROR")'
```

---

#### gateway log-download

Download the gateway log file as a zip archive.

```bash
ignition-cli gateway log-download [--output <path>] [--gateway <profile>] [--url <url>] [--token <token>]
```

**Options:**

| Option | Short | Description |
|---|---|---|
| `--output` | `-o` | Output file path (default: `gateway-logs.zip`) |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |

**Example:**

```bash
ignition-cli gateway log-download
ignition-cli gateway log-download -o logs/gateway-2025-01-15.zip
```

---

#### gateway loggers

List configured loggers and their levels.

```bash
ignition-cli gateway loggers [--gateway <profile>] [--url <url>] [--token <token>] [--format <fmt>]
```

**Options:**

| Option | Short | Description |
|---|---|---|
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |
| `--format` | `-f` | Output format (default: `table`) |

**Example:**

```bash
ignition-cli gateway loggers
ignition-cli gateway loggers -f json
```

---

#### gateway entity-browse

Browse the gateway entity tree (configuration, health, metrics).

```bash
ignition-cli gateway entity-browse [--path <path>] [--depth <n>] [--gateway <profile>] [--url <url>] [--token <token>] [--format <fmt>]
```

**Options:**

| Option | Short | Description |
|---|---|---|
| `--path` | `-p` | Entity path to browse (optional; browses root if omitted) |
| `--depth` | `-d` | Browse depth (default: `1`) |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |
| `--format` | `-f` | Output format (default: `table`) |

**Example:**

```bash
# Browse root
ignition-cli gateway entity-browse

# Browse a specific path with depth
ignition-cli gateway entity-browse --path /config/databases --depth 2
```

---

#### gateway scan-projects

Trigger the gateway to scan for project changes. This causes the gateway to pick up project file modifications without a restart.

```bash
ignition-cli gateway scan-projects [--gateway <profile>] [--url <url>] [--token <token>]
```

**Options:**

| Option | Short | Description |
|---|---|---|
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |

**Example:**

```bash
ignition-cli gateway scan-projects
# Project scan triggered.
```

---

#### gateway scan-config

Trigger the gateway to scan for configuration changes. This causes the gateway to pick up resource/config file modifications without a restart.

```bash
ignition-cli gateway scan-config [--gateway <profile>] [--url <url>] [--token <token>]
```

**Options:**

| Option | Short | Description |
|---|---|---|
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |

**Example:**

```bash
ignition-cli gateway scan-config
# Config scan triggered.
```

---

### project

Manage Ignition projects.

```
ignition-cli project <command>
```

#### project list

List all projects on the gateway.

```bash
ignition-cli project list [--filter <text>] [--gateway <profile>] [--url <url>] [--token <token>] [--format <fmt>]
```

**Options:**

| Option | Short | Description |
|---|---|---|
| `--filter` | | Filter projects by name (case-insensitive substring match) |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |
| `--format` | `-f` | Output format (default: `table`) |

**Example:**

```bash
ignition-cli project list
ignition-cli project list --filter "HMI"
ignition-cli project list -f json
```

---

#### project show

Show details for a specific project.

```bash
ignition-cli project show <name> [--gateway <profile>] [--url <url>] [--token <token>] [--format <fmt>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `name` | Project name |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |
| `--format` | `-f` | Output format (default: `table`) |

**Example:**

```bash
ignition-cli project show MyApp
ignition-cli project show MyApp -f json
```

---

#### project create

Create a new project on the gateway.

```bash
ignition-cli project create <name> [--title <title>] [--description <desc>] [--gateway <profile>] [--url <url>] [--token <token>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `name` | Project name |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--title` | `-t` | Project title |
| `--description` | `-d` | Project description |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |

**Example:**

```bash
ignition-cli project create NewProject --title "New Project" --description "A test project"
# Project 'NewProject' created.
```

---

#### project delete

Delete a project from the gateway. Prompts for confirmation unless `--force` is used.

```bash
ignition-cli project delete <name> [--force] [--gateway <profile>] [--url <url>] [--token <token>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `name` | Project name |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--force` | | Skip confirmation prompt |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |

**Example:**

```bash
ignition-cli project delete OldProject
# Delete project 'OldProject'? This cannot be undone [y/N]: y
# Project 'OldProject' deleted.

ignition-cli project delete OldProject --force
```

---

#### project export

Export a project as a `.zip` file.

```bash
ignition-cli project export <name> [--output <path>] [--gateway <profile>] [--url <url>] [--token <token>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `name` | Project name |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--output` | `-o` | Output file path (default: `<name>.zip`) |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |

**Example:**

```bash
ignition-cli project export MyApp
# Project 'MyApp' exported to MyApp.zip (145,832 bytes)

ignition-cli project export MyApp -o backups/MyApp-v2.zip
```

---

#### project import

Import a project from a `.zip` file. When `--overwrite` is used, prompts for confirmation unless `--force` is also provided. Uses streaming upload to handle large project files without loading them entirely into memory.

```bash
ignition-cli project import <file> [--name <name>] [--overwrite] [--force] [--gateway <profile>] [--url <url>] [--token <token>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `file` | Path to the project `.zip` file |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--name` | `-n` | Project name (defaults to the filename stem) |
| `--overwrite` | | Overwrite if project already exists |
| `--force` | | Skip confirmation when using `--overwrite` |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |

**Example:**

```bash
ignition-cli project import MyApp.zip
# Project 'MyApp' imported from MyApp.zip.

ignition-cli project import MyApp.zip --name MyApp-Restored --overwrite --force
```

---

#### project copy

Copy a project to a new name on the same gateway.

```bash
ignition-cli project copy <name> --name <new_name> [--gateway <profile>] [--url <url>] [--token <token>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `name` | Source project name |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--name` | `-n` | New project name (required) |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |

**Example:**

```bash
ignition-cli project copy MyApp --name MyApp-Backup
# Project 'MyApp' copied to 'MyApp-Backup'.
```

---

#### project rename

Rename a project on the gateway.

```bash
ignition-cli project rename <name> --name <new_name> [--gateway <profile>] [--url <url>] [--token <token>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `name` | Current project name |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--name` | `-n` | New project name (required) |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |

**Example:**

```bash
ignition-cli project rename OldProject --name NewProject
# Project 'OldProject' renamed to 'NewProject'.
```

---

#### project resources

List resources within a project.

```bash
ignition-cli project resources <name> [--gateway <profile>] [--url <url>] [--token <token>] [--format <fmt>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `name` | Project name |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |
| `--format` | `-f` | Output format (default: `table`) |

**Example:**

```bash
$ ignition-cli project resources MyApp
┌──────────────────┬────────────────┬─────────┬─────────┐
│ Name             │ Type           │ Path    │ Scope   │
├──────────────────┼────────────────┼─────────┼─────────┤
│ MainWindow       │ view           │ /views  │ session │
│ LoginScript      │ script         │ /       │ gateway │
└──────────────────┴────────────────┴─────────┴─────────┘
```

---

#### project diff

Diff a project between two gateways. Compares the project's configuration on the source gateway (your default or `--gateway` profile) with the same project on a target gateway.

```bash
ignition-cli project diff <name> --target <profile> [--gateway <profile>] [--url <url>] [--token <token>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `name` | Project name |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--target` | `-t` | Target gateway profile for comparison (required) |
| `--gateway` | `-g` | Source gateway profile |
| `--url` | | Source gateway URL override |
| `--token` | | Source API token override |

**Example:**

```bash
ignition-cli project diff MyApp --target staging
```

---

#### project watch

Watch a local directory and sync file changes to a project on the gateway. Requires the `watchfiles` package (`pip install "ignition-cli[watch]"`).

```bash
ignition-cli project watch <name> <path> [--gateway <profile>] [--url <url>] [--token <token>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `name` | Project name on the gateway |
| `path` | Local directory to watch |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |

Press `Ctrl+C` to stop watching.

**Example:**

```bash
ignition-cli project watch MyApp ./my-app-src
# Watching ./my-app-src for changes to project 'MyApp'...
# Press Ctrl+C to stop.
```

---

### tag

Browse, read, write, and manage tags.

```
ignition-cli tag <command>
```

#### tag browse

Browse the tag tree. Displays tags as a Rich tree in table mode, or structured data in other formats.

> **Note:** Tag browsing uses the tag export endpoint to retrieve tag structure, as browsing is not part of the standard Ignition REST API.

```bash
ignition-cli tag browse [path] [--recursive] [--provider <name>] [--gateway <profile>] [--url <url>] [--token <token>] [--format <fmt>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `path` | Tag path to browse (optional; browses root if omitted) |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--recursive` | `-r` | Browse recursively into folders |
| `--provider` | `-p` | Tag provider name (default: `default`) |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |
| `--format` | `-f` | Output format (default: `table`) |

**Example:**

```bash
# Browse root
ignition-cli tag browse

# Browse a folder recursively
ignition-cli tag browse "Pumps/Station1" --recursive

# JSON output
ignition-cli tag browse -f json

# Different provider
ignition-cli tag browse --provider "MyProvider"
```

---

#### tag read

Read one or more tag values. Accepts multiple tag paths as arguments.

> **Note:** Tag reading is not part of the standard Ignition REST API. This requires a gateway with a WebDev endpoint or custom module providing this capability.

```bash
ignition-cli tag read <paths>... [--provider <name>] [--gateway <profile>] [--url <url>] [--token <token>] [--format <fmt>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `paths` | One or more tag paths to read |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--provider` | `-p` | Tag provider name (default: `default`) |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |
| `--format` | `-f` | Output format (default: `table`) |

**Example:**

```bash
# Read a single tag
ignition-cli tag read "Pumps/Station1/Flow"

# Read multiple tags
ignition-cli tag read "Pumps/Station1/Flow" "Pumps/Station1/Pressure" "Pumps/Station1/Temp"

# JSON output
ignition-cli tag read "Pumps/Station1/Flow" -f json
```

Output columns: Path, Value, Quality, Timestamp.

---

#### tag write

Write a value to a tag. The value is automatically parsed as JSON (for numeric and boolean types) or used as a string.

> **Note:** Tag writing is not part of the standard Ignition REST API. This requires a gateway with a WebDev endpoint or custom module providing this capability.

```bash
ignition-cli tag write <path> <value> [--provider <name>] [--gateway <profile>] [--url <url>] [--token <token>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `path` | Tag path to write to |
| `value` | Value to write (parsed as JSON if valid, otherwise string) |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--provider` | `-p` | Tag provider name (default: `default`) |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |

**Example:**

```bash
# Write a numeric value
ignition-cli tag write "Setpoints/TargetTemp" 72.5

# Write a boolean
ignition-cli tag write "Controls/PumpEnable" true

# Write a string
ignition-cli tag write "Labels/Status" "Running"
```

---

#### tag export

Export tag configuration as JSON. Exports the full tag tree or a subtree.

```bash
ignition-cli tag export [path] [--output <file>] [--provider <name>] [--gateway <profile>] [--url <url>] [--token <token>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `path` | Tag path to export (optional; exports root if omitted) |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--output` | `-o` | Save to file instead of printing to stdout |
| `--provider` | `-p` | Tag provider name (default: `default`) |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |

**Example:**

```bash
# Export all tags to stdout
ignition-cli tag export

# Export a subtree to file
ignition-cli tag export "Pumps/Station1" -o station1-tags.json

# Different provider
ignition-cli tag export --provider "HistoricalProvider" -o historical.json
```

---

#### tag import

Import tag configuration from a file (JSON, XML, or CSV).

```bash
ignition-cli tag import <file> [--collision-policy <policy>] [--path <path>] [--provider <name>] [--gateway <profile>] [--url <url>] [--token <token>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `file` | Path to the tag file to import (JSON, XML, or CSV) |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--collision-policy` | `-c` | Collision policy: `Abort`, `Overwrite`, `Rename`, `Ignore`, `MergeOverwrite` (default: `MergeOverwrite`) |
| `--path` | | Target path for import |
| `--provider` | `-p` | Tag provider name (default: `default`) |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |

The file type is auto-detected from the file extension (`.json`, `.xml`, `.csv`).

**Example:**

```bash
# Import with default MergeOverwrite policy
ignition-cli tag import tags-backup.json

# Import with Overwrite policy
ignition-cli tag import tags-backup.json --collision-policy Overwrite

# Import to a specific path
ignition-cli tag import station1-tags.json --path "Pumps/Station1"

# Import XML tags to a specific provider
ignition-cli tag import tags.xml --provider "MyProvider"
```

---

#### tag providers

List available tag providers on the gateway.

```bash
ignition-cli tag providers [--gateway <profile>] [--url <url>] [--token <token>] [--format <fmt>]
```

**Options:**

| Option | Short | Description |
|---|---|---|
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |
| `--format` | `-f` | Output format (default: `table`) |

**Example:**

```bash
$ ignition-cli tag providers
┌─────────┬────────────────┬─────────┐
│ Name    │ Type           │ State   │
├─────────┼────────────────┼─────────┤
│ default │ tag-provider   │ Running │
└─────────┴────────────────┴─────────┘
```

---

### device

Manage device connections. Devices default to the `com.inductiveautomation.opcua` module but support `--module` and `--type` flags for other device types (Modbus, Allen-Bradley, etc.).

```
ignition-cli device <command>
```

#### device list

List device connections.

```bash
ignition-cli device list [--status <filter>] [--module <mod>] [--type <type>] [--gateway <profile>] [--url <url>] [--token <token>] [--format <fmt>]
```

**Options:**

| Option | Short | Description |
|---|---|---|
| `--status` | | Filter by device status (case-insensitive substring match) |
| `--module` | | Device module (default: `com.inductiveautomation.opcua`) |
| `--type` | | Device type (default: `device`) |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |
| `--format` | `-f` | Output format (default: `table`) |

**Example:**

```bash
ignition-cli device list
ignition-cli device list --status "connected"
ignition-cli device list --module com.inductiveautomation.modbus -f json
```

---

#### device show

Show details for a specific device connection.

```bash
ignition-cli device show <name> [--module <mod>] [--type <type>] [--gateway <profile>] [--url <url>] [--token <token>] [--format <fmt>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `name` | Device name |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--module` | | Device module (default: `com.inductiveautomation.opcua`) |
| `--type` | | Device type (default: `device`) |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |
| `--format` | `-f` | Output format (default: `table`) |

**Example:**

```bash
ignition-cli device show "PLC-Station1"
ignition-cli device show "PLC-Station1" -f json
```

---

#### device restart

Restart a device connection by toggling its enabled state (disable, wait, re-enable). Fetches the current resource, sets `enabled: false`, waits for the specified delay, then sets `enabled: true`.

```bash
ignition-cli device restart <name> [--delay <seconds>] [--module <mod>] [--type <type>] [--gateway <profile>] [--url <url>] [--token <token>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `name` | Device name |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--delay` | | Seconds between disable and enable (default: `2.0`) |
| `--module` | | Device module (default: `com.inductiveautomation.opcua`) |
| `--type` | | Device type (default: `device`) |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |

**Example:**

```bash
ignition-cli device restart "PLC-Station1"
# Disabled 'PLC-Station1'...
# Device 'PLC-Station1' restarted (toggled enabled state).

# Longer delay for slower devices
ignition-cli device restart "PLC-Station1" --delay 5
```

---

### resource

Generic CRUD for gateway resources. Resource types use the `module/type` format.

```
ignition-cli resource <command>
```

Common resource type examples:
- `ignition/database-connection`
- `com.inductiveautomation.opcua/device`
- `ignition/tag-provider`

#### resource list

List resources of a given type.

```bash
ignition-cli resource list <resource_type> [--gateway <profile>] [--url <url>] [--token <token>] [--format <fmt>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `resource_type` | Resource type in `module/type` format |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |
| `--format` | `-f` | Output format (default: `table`) |

**Example:**

```bash
ignition-cli resource list ignition/database-connection
ignition-cli resource list ignition/tag-provider -f json
```

---

#### resource show

Show configuration for a specific resource. Omit `name` for singleton resources (gateway-level settings with exactly one instance per type).

```bash
ignition-cli resource show <resource_type> [name] [--collection <mode>] [--default-if-undefined] [--gateway <profile>] [--url <url>] [--token <token>] [--format <fmt>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `resource_type` | Resource type in `module/type` format |
| `name` | Resource name (optional — omit for singleton resources) |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--collection` | | Deployment mode/collection to query |
| `--default-if-undefined` | | Return default config when singleton is undefined |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |
| `--format` | `-f` | Output format (default: `table`) |

**Example:**

```bash
# Named resource
ignition-cli resource show ignition/database-connection "MySQL_Production"

# Singleton resource (no name)
ignition-cli resource show com.inductiveautomation.opcua/server-config

# Singleton with collection and defaults
ignition-cli resource show com.inductiveautomation.opcua/server-config \
  --collection staging --default-if-undefined
```

---

#### resource create

Create a new resource. Configuration can be provided as an inline JSON string or loaded from a file using the `@` prefix.

```bash
ignition-cli resource create <resource_type> --name <name> [--config <json>] [--collection <mode>] [--gateway <profile>] [--url <url>] [--token <token>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `resource_type` | Resource type in `module/type` format |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--name` | `-n` | Resource name (required) |
| `--config` | `-c` | JSON config string or `@file` path |
| `--collection` | | Target deployment mode/collection |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |

**Example:**

```bash
# Inline JSON config
ignition-cli resource create ignition/database-connection \
  --name "MySQL_Prod" \
  --config '{"driver": "MySQL", "connectUrl": "jdbc:mysql://db:3306/prod"}'

# Config from file
ignition-cli resource create ignition/database-connection \
  --name "MySQL_Prod" \
  --config @db-config.json

# Minimal (name-only)
ignition-cli resource create ignition/tag-provider --name "MyProvider"

# Create with deployment mode collection
ignition-cli resource create ignition/database-connection \
  --name "MySQL_Staging" \
  --collection staging \
  --config '{"driver": "MySQL", "connectUrl": "jdbc:mysql://staging-db:3306/app"}'
```

---

#### resource update

Update an existing resource configuration. The resource signature (required by the API) is automatically fetched from the resource metadata. Omit `name` for singleton resources.

```bash
ignition-cli resource update <resource_type> [name] --config <json> [--collection <mode>] [--gateway <profile>] [--url <url>] [--token <token>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `resource_type` | Resource type in `module/type` format |
| `name` | Resource name (optional — omit for singleton resources) |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--config` | `-c` | JSON config string or `@file` path (required) |
| `--collection` | | Target deployment mode/collection |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |

**Example:**

```bash
ignition-cli resource update ignition/database-connection "MySQL_Prod" \
  --config '{"maxConnections": 20}'

ignition-cli resource update ignition/database-connection "MySQL_Prod" \
  --config @updated-config.json

# Update within a specific deployment mode
ignition-cli resource update ignition/database-connection "MySQL_Prod" \
  --config '{"maxConnections": 50}' --collection staging

# Update a singleton resource (no name)
ignition-cli resource update com.inductiveautomation.opcua/server-config \
  --config '{"enabled": false}'
```

---

#### resource delete

Delete a resource. Uses the Ignition `DELETE /resources/{module}/{type}/{name}/{signature}` endpoint. The resource signature is required; if `--signature` is omitted, the CLI automatically fetches it from the resource metadata.

Prompts for confirmation unless `--force` is used.

```bash
ignition-cli resource delete <resource_type> <name> [--force] [--signature <sig>] [--gateway <profile>] [--url <url>] [--token <token>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `resource_type` | Resource type in `module/type` format |
| `name` | Resource name |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--force` | | Skip confirmation prompt |
| `--signature` | `-s` | Resource signature (auto-fetched if omitted) |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |

**Example:**

```bash
# Auto-fetch signature
ignition-cli resource delete ignition/database-connection "OldDB" --force

# Explicit signature (skips the lookup request)
ignition-cli resource delete ignition/database-connection "OldDB" --force --signature abc123
```

---

#### resource names

List resource names for a given type. Returns just the names without full configuration details.

```bash
ignition-cli resource names <resource_type> [--gateway <profile>] [--url <url>] [--token <token>] [--format <fmt>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `resource_type` | Resource type in `module/type` format |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |
| `--format` | `-f` | Output format (default: `table`) |

**Example:**

```bash
ignition-cli resource names ignition/database-connection
ignition-cli resource names ignition/tag-provider -f json
```

---

#### resource upload

Upload a binary datafile to a resource. Used for fonts, theme CSS, icons, database drivers, and other binary resources.

The resource signature is required for uploads. If `--signature` is omitted, the CLI automatically fetches it from the resource metadata.

```bash
ignition-cli resource upload <resource_type> <name> <file_path> [--signature <sig>] [--filename <name>] [--gateway <profile>] [--url <url>] [--token <token>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `resource_type` | Resource type in `module/type` format |
| `name` | Resource name |
| `file_path` | Path to the local file to upload |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--signature` | `-s` | Resource signature (auto-fetched if omitted) |
| `--filename` | | Remote filename (defaults to local file basename) |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |

**Example:**

```bash
# Upload a CSS file (signature auto-fetched)
ignition-cli resource upload com.inductiveautomation.perspective/themes custom ./style.css

# Upload with explicit signature and custom remote filename
ignition-cli resource upload com.inductiveautomation.perspective/fonts MyFont ./font.woff2 \
  --signature "abc123def" --filename "MyFont-Regular.woff2"
```

---

#### resource download

Download a binary datafile from a resource to the local filesystem.

```bash
ignition-cli resource download <resource_type> <name> <filename> [--output <path>] [--gateway <profile>] [--url <url>] [--token <token>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `resource_type` | Resource type in `module/type` format |
| `name` | Resource name |
| `filename` | Remote filename to download |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--output` | `-o` | Output file path (defaults to the remote filename) |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |

**Example:**

```bash
# Download a theme CSS file
ignition-cli resource download com.inductiveautomation.perspective/themes dark variables.css

# Download to a specific path
ignition-cli resource download com.inductiveautomation.perspective/fonts Roboto Roboto-Regular.woff2 \
  --output ./fonts/Roboto-Regular.woff2
```

---

#### resource types

List available resource types discovered from the gateway's OpenAPI spec. Parses the `/openapi.json` endpoint to find resource paths.

```bash
ignition-cli resource types [--gateway <profile>] [--url <url>] [--token <token>]
```

**Options:**

| Option | Short | Description |
|---|---|---|
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |

**Example:**

```bash
$ ignition-cli resource types
┌────────────────────────────────────────────────────┐
│ Module/Type                                        │
├────────────────────────────────────────────────────┤
│ com.inductiveautomation.opcua/device               │
│ ignition/database-connection                       │
│ ignition/tag-provider                              │
└────────────────────────────────────────────────────┘
```

---

### mode

Manage gateway deployment modes. Deployment modes (introduced in Ignition 8.3) allow a single gateway to hold configuration for multiple environments (dev, staging, production).

```
ignition-cli mode <command>
```

#### mode list

List all deployment modes on the gateway.

```bash
ignition-cli mode list [--gateway <profile>] [--url <url>] [--token <token>] [--format <fmt>]
```

**Options:**

| Option | Short | Description |
|---|---|---|
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |
| `--format` | `-f` | Output format (default: `table`) |

**Example:**

```bash
$ ignition-cli mode list
                  Deployment Modes
┏━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Name    ┃ Title       ┃ Description         ┃ Resources ┃
┡━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ dev     │ Development │ Dev environment     │ 5         │
│ staging │ Staging     │ Pre-prod            │ 3         │
│ prod    │ Production  │ Live environment    │ 10        │
└─────────┴─────────────┴─────────────────────┴───────────┘

ignition-cli mode list -f json
```

---

#### mode show

Show details of a specific deployment mode.

```bash
ignition-cli mode show <name> [--gateway <profile>] [--url <url>] [--token <token>] [--format <fmt>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `name` | Mode name |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |
| `--format` | `-f` | Output format (default: `table`) |

**Example:**

```bash
$ ignition-cli mode show dev
             Mode: dev
┌───────────────┬─────────────────┐
│ name          │ dev             │
│ title         │ Development     │
│ description   │ Dev environment │
│ resourceCount │ 5               │
└───────────────┴─────────────────┘
```

---

#### mode create

Create a new deployment mode.

```bash
ignition-cli mode create <name> [--title <title>] [--description <desc>] [--gateway <profile>] [--url <url>] [--token <token>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `name` | Mode name |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--title` | `-t` | Short title for the mode |
| `--description` | `-d` | Mode description |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |

**Example:**

```bash
ignition-cli mode create dev --title "Development" --description "Dev environment"
# Deployment mode 'dev' created.
```

---

#### mode update

Update or rename an existing deployment mode.

```bash
ignition-cli mode update <name> [--name <new_name>] [--title <title>] [--description <desc>] [--gateway <profile>] [--url <url>] [--token <token>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `name` | Current mode name |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--name` | `-n` | Rename the mode |
| `--title` | `-t` | New title |
| `--description` | `-d` | New description |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |

**Example:**

```bash
# Update description
ignition-cli mode update dev --description "Updated dev environment"

# Rename a mode
ignition-cli mode update staging --name pre-prod --title "Pre-Production"
```

---

#### mode delete

Delete a deployment mode. Prompts for confirmation unless `--force` is used.

```bash
ignition-cli mode delete <name> [--force] [--gateway <profile>] [--url <url>] [--token <token>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `name` | Mode name to delete |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--force` | | Skip confirmation prompt |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |

**Example:**

```bash
ignition-cli mode delete test-mode --force
# Deployment mode 'test-mode' deleted.
```

---

#### mode assign

Assign a resource to a deployment mode. Fetches the existing resource configuration and creates a mode-specific config override. Omit `resource_name` for singleton resources.

```bash
ignition-cli mode assign <name> <resource_type> [resource_name] [--gateway <profile>] [--url <url>] [--token <token>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `name` | Mode name |
| `resource_type` | Resource type in `module/type` format |
| `resource_name` | Resource name (optional — omit for singleton resources) |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |

**Example:**

```bash
# Assign a database connection to the staging mode
ignition-cli mode assign staging ignition/database-connection Automotive
# Resource 'Automotive' (ignition/database-connection) assigned to mode 'staging'.

# Assign a singleton resource (no name)
ignition-cli mode assign staging com.inductiveautomation.opcua/server-config

# Verify the assignment
ignition-cli mode list  # staging should show increased resource count
```

---

#### mode unassign

Remove a resource from a deployment mode. Fetches the resource signature and deletes the mode-specific config override. Omit `resource_name` for singleton resources.

```bash
ignition-cli mode unassign <name> <resource_type> [resource_name] [--gateway <profile>] [--url <url>] [--token <token>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `name` | Mode name |
| `resource_type` | Resource type in `module/type` format |
| `resource_name` | Resource name (optional — omit for singleton resources) |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |

**Example:**

```bash
# Remove a database connection from the staging mode
ignition-cli mode unassign staging ignition/database-connection Automotive
# Resource 'Automotive' (ignition/database-connection) removed from mode 'staging'.

# Remove a singleton resource from a mode (no name)
ignition-cli mode unassign staging com.inductiveautomation.opcua/server-config
```

---

### api

Raw API access and endpoint discovery. Use these commands to call arbitrary gateway API endpoints or explore the available API surface.

```
ignition-cli api <command>
```

#### api get

Send a GET request to a gateway API endpoint. The path is relative to the API base (`/data/api/v1`).

```bash
ignition-cli api get <path> [--gateway <profile>] [--url <url>] [--token <token>] [--format <fmt>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `path` | API path (e.g. `/status`, `/gateway-info`) |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |
| `--format` | `-f` | Output format (default: `json`) |

**Example:**

```bash
ignition-cli api get /gateway-info
ignition-cli api get /projects/list -f table
```

---

#### api post

Send a POST request to a gateway API endpoint.

```bash
ignition-cli api post <path> [--data <json>] [--gateway <profile>] [--url <url>] [--token <token>] [--format <fmt>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `path` | API path |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--data` | `-d` | JSON request body |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |
| `--format` | `-f` | Output format (default: `json`) |

**Example:**

```bash
ignition-cli api post /projects -d '{"name": "NewProject"}'
ignition-cli api post /tags/read -d '["Pumps/Flow", "Pumps/Pressure"]'
```

---

#### api put

Send a PUT request to a gateway API endpoint.

```bash
ignition-cli api put <path> [--data <json>] [--gateway <profile>] [--url <url>] [--token <token>] [--format <fmt>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `path` | API path |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--data` | `-d` | JSON request body |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |
| `--format` | `-f` | Output format (default: `json`) |

**Example:**

```bash
ignition-cli api put /resources/ignition/database-connection \
  -d '{"name": "MySQL_Prod", "maxConnections": 25}'
```

---

#### api delete

Send a DELETE request to a gateway API endpoint. Prints "Deleted." for 204 No Content responses.

```bash
ignition-cli api delete <path> [--gateway <profile>] [--url <url>] [--token <token>] [--format <fmt>]
```

**Arguments:**

| Argument | Description |
|---|---|
| `path` | API path |

**Options:**

| Option | Short | Description |
|---|---|---|
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |
| `--format` | `-f` | Output format (default: `json`) |

**Example:**

```bash
ignition-cli api delete /projects/OldProject
```

---

#### api discover

Browse available API endpoints from the gateway's OpenAPI spec. Fetches `/openapi.json` and displays a table of methods, paths, and summaries.

```bash
ignition-cli api discover [--filter <text>] [--method <method>] [--gateway <profile>] [--url <url>] [--token <token>]
```

**Options:**

| Option | Short | Description |
|---|---|---|
| `--filter` | | Filter endpoints by path (case-insensitive substring match) |
| `--method` | `-m` | Filter by HTTP method (e.g. `GET`, `POST`) |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |

**Example:**

```bash
# Show all endpoints
ignition-cli api discover

# Filter by path
ignition-cli api discover --filter "project"

# Only GET endpoints
ignition-cli api discover --method GET

# Combine filters
ignition-cli api discover --filter "tag" --method POST
```

---

#### api spec

Download the full OpenAPI specification from the gateway.

```bash
ignition-cli api spec [--output <file>] [--gateway <profile>] [--url <url>] [--token <token>]
```

**Options:**

| Option | Short | Description |
|---|---|---|
| `--output` | `-o` | Save spec to file (prints to stdout if omitted) |
| `--gateway` | `-g` | Gateway profile |
| `--url` | | Gateway URL override |
| `--token` | | API token override |

**Example:**

```bash
# Print to stdout
ignition-cli api spec

# Save to file
ignition-cli api spec -o openapi-spec.json
```

---

## 8. Common Workflows

### Multi-Gateway Project Diff

Compare a project across development and production gateways:

```bash
# Ensure both profiles are configured
ignition-cli config add dev --url https://dev:8088 --token "devKey:devSecret"
ignition-cli config add prod --url https://prod:8043 --token "prodKey:prodSecret"

# Compare
ignition-cli project diff MyApp --gateway dev --target prod
```

### Automated Gateway Backup (CI/CD)

A cron job or CI pipeline step to back up a gateway daily:

```bash
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/backups/ignition"
DATE=$(date +%Y-%m-%d)
GATEWAY="production"

mkdir -p "$BACKUP_DIR"

export IGNITION_GATEWAY_PROFILE="$GATEWAY"
ignition-cli gateway backup -o "$BACKUP_DIR/gateway-$DATE.gwbk"

echo "Backup complete: $BACKUP_DIR/gateway-$DATE.gwbk"
```

### Tag Monitoring Script

Periodically read tag values and log them:

```bash
#!/bin/bash
while true; do
  ignition-cli tag read \
    "Pumps/Station1/Flow" \
    "Pumps/Station1/Pressure" \
    "Pumps/Station1/Temp" \
    -f json | jq -c '{
      timestamp: now | todate,
      flow: .[0].value,
      pressure: .[1].value,
      temp: .[2].value
    }' >> tag-log.jsonl
  sleep 10
done
```

### Project Export/Import for Migration

Export from one gateway and import to another:

```bash
# Export from dev
ignition-cli project export MyApp -o MyApp-export.zip --gateway dev

# Import to staging (--force skips confirmation on overwrite)
ignition-cli project import MyApp-export.zip --overwrite --force --gateway staging
```

### Project Watch for Development

Sync local file changes to a gateway project during development:

```bash
pip install "ignition-cli[watch]"
ignition-cli project watch MyApp ./src/MyApp --gateway dev
```

### API Discovery and Exploration

Discover what endpoints are available and test them:

```bash
# See all available endpoints
ignition-cli api discover

# Find tag-related endpoints
ignition-cli api discover --filter "tag"

# Save the full OpenAPI spec for offline reference
ignition-cli api spec -o gateway-api.json

# Test an endpoint directly
ignition-cli api get /gateway-info
```

### Deployment Mode Management

Set up deployment modes for multi-environment configuration on a single gateway:

```bash
# Create modes
ignition-cli mode create dev --title "Development" --description "Dev environment"
ignition-cli mode create staging --title "Staging" --description "Pre-production"
ignition-cli mode create prod --title "Production" --description "Live environment"

# Assign resources to modes
ignition-cli mode assign staging ignition/database-connection Automotive

# Verify the assignment
ignition-cli mode list  # staging should show Resources: 1

# Or create a resource directly into a mode
ignition-cli resource create ignition/database-connection \
  --name "TestDB" --collection staging \
  --config '{"driver":"MySQL ConnectorJ"}'

# Remove a resource from a mode
ignition-cli mode unassign staging ignition/database-connection Automotive

# List modes
ignition-cli mode list

# Update a mode
ignition-cli mode update staging --description "QA and staging"

# Clean up
ignition-cli mode delete dev --force
```

### Theme and Binary Resource Management

Download, modify, and re-upload binary resources like Perspective themes:

```bash
# See what files a theme contains
ignition-cli resource show com.inductiveautomation.perspective/themes custom -f json

# Download a CSS file for editing
ignition-cli resource download com.inductiveautomation.perspective/themes custom index.css \
  --output ./theme-work/index.css

# Edit the file locally, then upload it back
ignition-cli resource upload com.inductiveautomation.perspective/themes custom ./theme-work/index.css \
  --filename index.css

# Trigger a scan so the gateway picks up changes
ignition-cli gateway scan-config
```

### Bulk Resource Inventory

Export an inventory of all resource types and their instances:

```bash
#!/bin/bash
for rtype in $(ignition-cli resource types 2>/dev/null | tail -n +4 | head -n -1 | awk '{print $2}'); do
  echo "=== $rtype ==="
  ignition-cli resource names "$rtype" 2>/dev/null
  echo
done
```

---

## 9. Troubleshooting

### Exit Codes

| Code | Name | Description |
|---|---|---|
| 0 | Success | Command completed successfully |
| 1 | General Error | Generic error (invalid input, unexpected failures) |
| 2 | Connection Error | Cannot connect to the gateway (network, DNS, timeout) |
| 3 | Authentication Error | Authentication failed (HTTP 401 or 403) |
| 4 | Not Found | Requested resource not found (HTTP 404) |
| 5 | Conflict | Resource conflict (HTTP 409, e.g. duplicate name) |
| 6 | Configuration Error | Missing or invalid configuration (no URL, bad profile) |

### Common Errors

#### Connection refused / Cannot connect

```
Error: Cannot connect to gateway at https://gateway:8043: ...
```

**Causes:**
- Gateway is not running or not reachable on the network
- Wrong URL or port in the profile
- Firewall blocking the connection

**Solutions:**
- Verify the gateway is running and the URL is correct
- Check `ignition-cli config show <profile>` for the configured URL
- Test network connectivity: `curl -k https://gateway:8043`

#### Authentication failed

```
Error: Authentication failed: ...
```

**Causes:**
- Invalid or expired API token
- Wrong username/password for basic auth
- API token lacks required permissions

**Solutions:**
- Regenerate the API token in the Ignition gateway web UI
- Verify credentials with `ignition-cli config show <profile>`
- Ensure the token has the necessary permissions for the endpoint

#### SSL certificate errors

```
Error: Cannot connect to gateway at https://gateway:8043: [SSL: CERTIFICATE_VERIFY_FAILED] ...
```

**Causes:**
- Self-signed certificate on the gateway
- Expired or invalid certificate
- Missing CA certificate in the trust store

**Solutions:**
- For development/testing, disable SSL verification:
  ```bash
  ignition-cli config add dev --url https://dev:8043 --token "key:secret" --no-verify-ssl
  ```
- For production, install the CA certificate in your system trust store

#### Request timeout

```
Error: Request to https://gateway:8043 timed out: ...
```

**Causes:**
- Gateway is overloaded or slow to respond
- Network latency
- Large backup/export taking too long

**Solutions:**
- Increase the timeout in your profile:
  ```toml
  [profiles.production]
  url = "https://prod:8043"
  token = "key:secret"
  timeout = 120.0
  ```
- For backup/export operations, consider increasing significantly (e.g. 300 seconds)

#### watchfiles not installed

```
ModuleNotFoundError: No module named 'watchfiles'
```

**Cause:** The `project watch` command requires the optional `watchfiles` dependency.

**Solution:**

```bash
pip install "ignition-cli[watch]"
```

#### Invalid resource type format

```
Invalid resource type 'database-connection'. Use module/type format (e.g. ignition/database-connection).
```

**Cause:** Resource types must include the module prefix separated by `/`.

**Solution:** Always use the `module/type` format:

```bash
# Wrong
ignition-cli resource list database-connection

# Correct
ignition-cli resource list ignition/database-connection
```

Use `ignition-cli resource types` to discover available resource types.

#### Tag read/write not available

Tag `read` and `write` commands are not part of the standard Ignition REST API. They require a custom WebDev endpoint or third-party module on the gateway.

If you get 404 errors on tag read/write:
- Ensure the gateway has a WebDev module with endpoints for tag operations
- Verify the endpoint paths match what the CLI expects (`/tags/read`, `/tags/write`)

### Debugging Tips

#### Check resolved configuration

Use `config show` to see what the CLI will use:

```bash
ignition-cli config show production
```

#### Test connectivity first

Always start with `config test` to verify the connection:

```bash
ignition-cli config test production
```

#### Use JSON output for scripting

When debugging, JSON output is easier to inspect:

```bash
ignition-cli gateway status -f json | python -m json.tool
```

#### Override profile settings temporarily

Use CLI flags to override without modifying the config:

```bash
ignition-cli gateway status --url https://other:8043 --token "tempKey:tempSecret"
```

#### Inspect environment variables

Check if environment variables are interfering:

```bash
echo $IGNITION_GATEWAY_URL
echo $IGNITION_API_TOKEN
echo $IGNITION_GATEWAY_PROFILE
```

#### Use raw API commands for debugging

When a high-level command fails, try the raw API equivalent:

```bash
# Instead of: ignition-cli project list
ignition-cli api get /projects/list

# See what endpoints exist
ignition-cli api discover --filter "project"
```
