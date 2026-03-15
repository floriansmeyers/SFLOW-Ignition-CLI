# MCP Connector for Ignition

Pre-built Ignition project that provides WebDev endpoints for tag read/write and other operations.

## Prerequisites

- Ignition 8.3+ with **WebDev module** installed
- API key configured (Gateway > Security > API Keys)

## Installation

### Option A: Via CLI

```bash
ignition-cli project import contrib/mcp-connector.zip
ignition-cli gateway scan-projects
```

### Option B: Via Gateway Web UI

1. Open Gateway webpage (http://localhost:8088)
2. Go to **Config > Projects**
3. Click **Import** and select `mcp-connector.zip`

The `mcp-connector` project will be created automatically.

Then configure your CLI profile to use it:

```bash
ignition-cli config add dev --url https://gateway:8043 --token "keyId:secretKey" --webdev-project mcp-connector
```

## Endpoints

All endpoints are available at `/system/webdev/mcp-connector/...`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `alarms/status` | GET | Active alarm status (post-filtered by priority) |
| `alarms/journal` | GET | Historical alarm events (bracket access for eventTime) |
| `alarms/acknowledge` | POST | Acknowledge unacknowledged alarms |
| `tags/browse` | GET | Browse tag tree |
| `tags/read` | GET | Read tag values |
| `tags/write` | POST | Write tag values |
| `tags/history` | GET | Query tag history |
| `tags/configure` | POST | Create/configure tags |
| `db/query` | POST | Execute named queries |
| `db/execute` | POST | Raw SQL SELECT execution |
| `db/schema` | POST | Database schema inspection (TABLE_SCHEMA = DATABASE()) |
| `audit/log` | GET | Query audit log (auto-discovers profile) |
| `script/execute` | POST | Generic system.* function executor |
| `system/performance` | GET | JVM/CPU/thread metrics |
| `project/resource-read` | POST | Read project files from gateway filesystem |
| `project/resource-write` | POST | Write project files to gateway filesystem |
| `project/resource-patch` | POST | Surgical JSON patch on project files |
| `gateway/settings` | POST | Read/modify gateway settings (timezone) |
| `translation/manage` | POST | Read/modify gateway translation terms |

Note: `system/sessions` is included in the ZIP but Perspective sessions now use the native REST API (`/data/perspective/api/v1/sessions/`) as of v2.6.0.

## Endpoint Examples

### script/execute

Execute any `system.*` function by name.

```json
POST /system/webdev/mcp-connector/script/execute
{
    "function": "system.tag.readBlocking",
    "args": [["[default]Path/To/Tag"]],
    "kwargs": {}
}
```

### db/schema

Inspect database schema. Uses `TABLE_SCHEMA = DATABASE()` to avoid cross-schema leakage on MySQL.

```json
POST /system/webdev/mcp-connector/db/schema
{"database": "MyDB", "action": "list_tables"}

POST /system/webdev/mcp-connector/db/schema
{"database": "MyDB", "action": "describe", "table": "users"}
```

### translation/manage

Read or modify gateway translation terms.

```json
POST /system/webdev/mcp-connector/translation/manage
{"action": "get", "terms": ["button.save", "label.name"], "locale": "es"}

POST /system/webdev/mcp-connector/translation/manage
{"action": "set", "entries": [{"term": "button.save", "translation": "Guardar"}], "locale": "es"}
```

## v2.6.0 Jython Script Fixes

- **alarms/status**: Priority filter post-filters results (minPriority kwarg unreliable in Gateway scope)
- **alarms/journal**: Uses `event["eventTime"]` bracket access (`getEventTime()` is None on PyAlarmEvent)
- **alarms/acknowledge**: Fixed state matching (`"unacknowledged"` not `"unacked"`)
- **db/schema**: Added `TABLE_SCHEMA = DATABASE()` to prevent cross-schema leakage
- **audit/log**: Auto-discovers audit profile name via Java API instead of hardcoding "default"
- **project/resource-read**: Normalizes directory listing paths to forward slashes

## Rebuilding

Scripts are extracted from `server.py` at build time (no duplication):

```bash
python build_connector.py
```

This regenerates `mcp-connector.zip`. Re-import to update.
