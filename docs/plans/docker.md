# Plan: Zero-Touch Gateway Deployment + Provisioning

## Status: NOT STARTED

Implementation was not begun — this file preserves the full plan for future reference.

---

## Context

The CLI can manage running Ignition gateways but can't bootstrap one from scratch. The goal is a single command that creates a VPS on DigitalOcean or Hetzner, installs Docker, starts Ignition, and provisions it with templates — fully zero-touch.

**Three features:**
1. **`deploy` command group** — Create/destroy VPS instances with Ignition via cloud APIs
2. **`docker` command group** — Generate docker-compose.yml, manage local containers
3. **`gateway provision` command** — Configure a running gateway from a template directory

**Auth strategy:** Use Basic Auth (admin credentials set via Docker env vars) for initial provisioning. If it fails (Ignition 8.3 may reject Basic Auth), fall back to printing instructions for the user to create an API token via the web UI. No new dependencies — we use httpx (already installed) for both cloud APIs.

---

## New Files

```
src/ignition_cli/
├── deploy/
│   ├── __init__.py              # package marker
│   ├── providers.py             # DigitalOcean + Hetzner API clients (httpx-based)
│   ├── cloud_init.py            # Generate cloud-init user-data script
│   └── state.py                 # Deployment state persistence (~/.config/ignition-cli/deployments.json)
├── docker/
│   ├── __init__.py              # package marker
│   └── compose.py               # ComposeOptions model + generate_compose()
├── provision/
│   ├── __init__.py              # package marker
│   ├── template.py              # ProvisionTemplate model + parse_template_dir()
│   └── engine.py                # ProvisionEngine orchestrator
├── commands/
│   ├── deploy.py                # deploy create/list/destroy/status commands
│   └── docker.py                # docker init/up/down/status/logs commands
tests/
├── unit/
│   ├── test_cloud_init.py       # cloud-init script generation
│   ├── test_docker_compose.py   # compose file generation
│   ├── test_provision_template.py
│   └── test_provision_engine.py
├── integration/
│   ├── test_deploy_commands.py  # deploy commands with mocked cloud APIs
│   ├── test_docker_commands.py  # docker commands with mocked subprocess
│   └── test_provision_command.py
```

## Modified Files

- `src/ignition_cli/app.py` — register `deploy` and `docker` sub-apps
- `src/ignition_cli/commands/gateway.py` — add `provision` command
- `src/ignition_cli/client/errors.py` — add `DockerNotFoundError`, `CloudProviderError`
- `src/ignition_cli/config/constants.py` — add `DEPLOYMENTS_FILE` path
- `CLAUDE.md`, `README.md`, `docs/usage.md` — document new commands

---

## Feature 1: `deploy` Command Group

### `deploy create` — Full zero-touch deployment

```
ignition-cli deploy create \
  --provider digitalocean \
  --api-key $DO_TOKEN \
  --region nyc1 \
  --size s-2vcpu-4gb \
  --name my-gateway \
  --admin-password SecurePass123 \
  --ssh-key "~/.ssh/id_ed25519.pub" \
  --template-dir ./templates
```

**Options:**
- `--provider` (required): `digitalocean` or `hetzner`
- `--api-key` (required): Cloud provider API token (or env `DIGITALOCEAN_TOKEN` / `HETZNER_TOKEN`)
- `--region`: Data center region (default: `nyc1` / `nbg1`)
- `--size`: Instance type (default: `s-2vcpu-4gb` / `cx22`)
- `--name`: Deployment name (default: `ignition-gateway`)
- `--image-tag`: Ignition Docker image tag (default: `8.3`)
- `--admin-user` / `--admin-password`: Gateway admin credentials
- `--ssh-key`: Path to public SSH key (optional, for VPS access)
- `--template-dir`: Template directory for provisioning (optional, skip provisioning if omitted)
- `--edition`: full/edge/maker (default: `full`)
- `--memory`: Max JVM memory in MB (default: `1024`)

**Flow:**

1. Validate inputs
2. Read SSH public key if provided
3. Generate cloud-init user-data script (installs Docker, creates compose file, starts Ignition)
4. Call cloud API to create VPS with user-data
5. Poll cloud API until VPS has a public IP (5s interval, 120s timeout)
6. Poll `http://<ip>:8088/StatusPing` until Ignition responds (10s interval, 300s timeout)
7. If `--template-dir` provided:
   a. Create a temporary GatewayProfile with URL + admin credentials (Basic Auth)
   b. Run the provision engine
   c. If auth fails (401), print manual instructions
8. Save deployment state to `deployments.json`
9. Print summary: URL, IP, admin credentials, SSH command

### `deploy list` — List deployments

Shows all tracked deployments from `deployments.json` with name, provider, IP, status, created date.

### `deploy destroy` — Tear down a deployment

```
ignition-cli deploy destroy --provider digitalocean --api-key $DO_TOKEN --name my-gateway
```

Calls cloud API to delete the VPS. Removes from `deployments.json`. Confirmation prompt (unless `--force`).

### `deploy status` — Check deployment health

Polls the VPS IP and checks if Ignition is responding.

### `deploy/providers.py` — Cloud API Clients

Both use httpx directly (no SDK dependencies):

```python
class CloudProvider(ABC):
    def create_server(self, name, region, size, image, ssh_keys, user_data) -> str:  # returns server_id
    def get_server(self, server_id) -> ServerInfo:  # ip, status
    def delete_server(self, server_id) -> None:
    def list_regions(self) -> list[Region]:
    def list_sizes(self) -> list[Size]:

class DigitalOceanProvider(CloudProvider):
    base_url = "https://api.digitalocean.com/v2"
    # POST /droplets (create)
    # GET /droplets/{id} (status/IP)
    # DELETE /droplets/{id} (destroy)

class HetznerProvider(CloudProvider):
    base_url = "https://api.hetzner.cloud/v1"
    # POST /servers (create)
    # GET /servers/{id} (status/IP)
    # DELETE /servers/{id} (destroy)
```

Defaults:
- **DigitalOcean**: image=`ubuntu-24-04-x64`, size=`s-2vcpu-4gb`, region=`nyc1`
- **Hetzner**: image=`ubuntu-24.04`, type=`cx22`, location=`nbg1`

### `deploy/cloud_init.py` — User-Data Script Generation

Generates a cloud-init bash script that:

```bash
#!/bin/bash
# Install Docker
curl -fsSL https://get.docker.com | sh

# Create compose directory
mkdir -p /opt/ignition
cat > /opt/ignition/docker-compose.yml << 'COMPOSE'
<generated docker-compose.yml content>
COMPOSE

# Start Ignition
cd /opt/ignition && docker compose up -d
```

The compose content is generated by the same `generate_compose()` function from `docker/compose.py`.

### `deploy/state.py` — Deployment State

```python
@dataclass
class Deployment:
    name: str
    provider: str           # "digitalocean" or "hetzner"
    server_id: str
    ip: str
    region: str
    size: str
    admin_user: str
    created_at: str         # ISO format
    gateway_url: str        # http://<ip>:8088
    api_key_env: str        # env var name where API key is stored (not the key itself)
```

Stored in `~/.config/ignition-cli/deployments.json`. Read/write via `DeploymentStore` class.

---

## Feature 2: `docker` Command Group (local containers)

### `docker init` — Generate docker-compose.yml

Options: `--image`, `--http-port`, `--https-port`, `--gan-port`, `--admin-user`, `--admin-password`, `--edition`, `--timezone`, `--memory`, `--modules`, `--env-file`, `--output-dir`

Generates:
```yaml
services:
  ignition:
    image: inductiveautomation/ignition:8.3
    container_name: ignition
    ports:
      - "8088:8088"
      - "8043:8043"
      - "8060:8060"
    environment:
      ACCEPT_IGNITION_EULA: "Y"
      GATEWAY_ADMIN_USERNAME: admin
      GATEWAY_ADMIN_PASSWORD: password
      IGNITION_EDITION: full
      TZ: UTC
      GATEWAY_MAX_MEMORY: "1024"
    volumes:
      - ignition-data:/usr/local/bin/ignition/data
    restart: unless-stopped
volumes:
  ignition-data:
```

Implementation in `docker/compose.py`: `ComposeOptions` Pydantic model + `generate_compose(options) -> str`.

### `docker up` / `docker down` / `docker status` / `docker logs`

Thin wrappers around `docker compose` subprocess calls. `docker up` includes health polling.
`check_docker()` validates Docker is installed before running.

---

## Feature 3: `gateway provision` Command

Added to existing `commands/gateway.py`:

```
ignition-cli gateway provision <template-dir> [-g GATEWAY] [--url URL] [--token TOKEN]
    [--dry-run] [--skip-verify] [--tag-provider default] [--collision-policy MergeOverwrite]
```

### Template Directory Structure

```
templates/
├── modes.json                              # [{"name":"dev","title":"Development"}, ...]
├── resources/
│   ├── ignition/database-connection/*.json
│   └── com.inductiveautomation.opcua/device/*.json
├── projects/*.zip
└── tags/*.json
```

### `provision/template.py` — Template Parser

- `parse_template_dir(path) -> ProvisionTemplate`
- Walks directory, parses JSON files, extracts module/type from path structure

### `provision/engine.py` — Provisioning Orchestrator

`ProvisionEngine.run() -> ProvisionResult` executes steps using GatewayClient directly:

1. **Verify connectivity** — `GET /gateway-info`
2. **Create modes** — `POST /mode` with `{"name":..., "title":..., "description":...}`
3. **Create resources** — `POST /resources/{module}/{type}` with JSON array `[{...config, "name": name}]`
4. **Import projects** — `stream_upload("POST", "/projects/import/{name}", zip_path)` then `POST /scan/projects`
5. **Import tags** — `client.post("/tags/import", content=tag_data, params={"provider":..., "type":"json", "collisionPolicy":...})`
6. **Verify** — list projects, modes to confirm
7. **Print summary** — Rich output with checkmarks/failures

Error handling: catches failures per-item, continues, reports summary. Exit code 1 if any failures.

---

## Implementation Order

1. Add errors to `client/errors.py` (`DockerNotFoundError`, `CloudProviderError`)
2. Add `DEPLOYMENTS_FILE` to `config/constants.py`
3. Create `docker/` package: `compose.py` (shared by both docker and deploy)
4. Create `provision/` package: `template.py`, `engine.py`
5. Add `provision` command to `commands/gateway.py`
6. Create `deploy/` package: `providers.py`, `cloud_init.py`, `state.py`
7. Create `commands/docker.py` and `commands/deploy.py`
8. Register both sub-apps in `app.py`
9. Write unit tests
10. Write integration tests
11. Run full test suite + linting
12. Update docs

---

## Key Reuse Points

| Existing Code | Location | Reused For |
|---|---|---|
| `make_client()` | `_common.py:42-50` | provision command |
| `extract_items()` | `_common.py:53-67` | provision verify step |
| `error_handler` | `errors.py:70-81` | all new commands |
| `GatewayClient` | `gateway.py:25-213` | provision engine |
| `GatewayProfile` | `models.py` | deploy creates temp profile for provisioning |
| `ConfigManager` | `manager.py` | deploy saves profile after creation |
| `stream_upload()` | `gateway.py:188-193` | provision project import |
| Option aliases | `_common.py:16-39` | provision command signature |

---

## Verification

1. `pytest tests/` — all existing + new tests pass
2. `ruff check src/ tests/` — no lint errors
3. Smoke tests:
   - `ignition-cli docker init --admin-password test123` — generates valid docker-compose.yml
   - `ignition-cli docker up` — starts local container (requires Docker)
   - `ignition-cli gateway provision ./templates --url http://localhost:8088 --token KEY --dry-run` — shows plan
   - `ignition-cli deploy create --provider digitalocean --api-key $DO_TOKEN --name test-gw --admin-password test123 --template-dir ./templates` — full zero-touch (requires DO account)
   - `ignition-cli deploy list` — shows deployment
   - `ignition-cli deploy destroy --name test-gw --provider digitalocean --api-key $DO_TOKEN` — cleans up
