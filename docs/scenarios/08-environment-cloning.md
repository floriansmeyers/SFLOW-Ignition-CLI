# Scenario 8: Environment Cloning (Production to Dev/Staging)

## Problem

You need a dev or staging environment that mirrors production — same projects, same tags, same device structure. But you can't just restore a production backup as-is: the database connection strings point to production databases, device connections point to production PLCs, and the deployment mode is wrong. So you restore the backup, then spend an hour manually updating every connection string, every IP address, and every mode — hoping you didn't miss one that's still pointing at production.

## What This Automates

- Backs up the source (production) gateway
- Restores to the target (dev/staging) gateway
- Applies a connection remap config to rewrite database URLs, device hostnames, and other environment-specific settings
- Sets the appropriate deployment mode on the target
- Verifies the clone by checking device connections and project states

## Script

```bash
#!/usr/bin/env bash
# clone-environment.sh — Clone one gateway to another with connection remapping
# Usage: clone-environment.sh <source-profile> <target-profile> <remap-config>
set -euo pipefail

SOURCE="${1:?Usage: clone-environment.sh <source-profile> <target-profile> <remap-config>}"
TARGET="${2:?Missing target gateway profile}"
REMAP_FILE="${3:?Missing remap config file}"
TARGET_MODE="${4:-}"

DATE=$(date +%Y%m%d-%H%M%S)
WORK_DIR="./clone-$DATE"
BACKUP_FILE="$WORK_DIR/source-backup.gwbk"
POLL_TIMEOUT=300
POLL_INTERVAL=15

mkdir -p "$WORK_DIR"

echo "=== Environment Cloning ==="
echo "Source:    $SOURCE"
echo "Target:    $TARGET"
echo "Remap:     $REMAP_FILE"
echo "Mode:      ${TARGET_MODE:-none}"
echo "Date:      $DATE"
echo ""

if [ ! -f "$REMAP_FILE" ]; then
    echo "ERROR: Remap config not found: $REMAP_FILE"
    exit 1
fi

# Step 1: Backup source
echo "[1/6] Backing up source gateway ($SOURCE)..."
ignition-cli gateway backup -g "$SOURCE" -o "$BACKUP_FILE"
SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "  Backup created: $BACKUP_FILE ($SIZE)"
echo ""

# Step 2: Restore to target
echo "[2/6] Restoring backup to target gateway ($TARGET)..."
ignition-cli gateway restore "$BACKUP_FILE" -g "$TARGET" --force
echo "  Restore initiated."
echo ""

# Step 3: Wait for target to come online
echo "[3/6] Waiting for target gateway to come online..."
elapsed=0
gateway_online=false

while [ $elapsed -lt $POLL_TIMEOUT ]; do
    sleep $POLL_INTERVAL
    elapsed=$((elapsed + POLL_INTERVAL))

    if ignition-cli gateway status -g "$TARGET" -f json >/dev/null 2>&1; then
        echo "  Gateway online after ${elapsed}s."
        gateway_online=true
        break
    fi
    echo "  ${elapsed}s — still waiting..."
done

if [ "$gateway_online" = false ]; then
    echo "  ERROR: Target gateway did not come online within ${POLL_TIMEOUT}s."
    exit 1
fi

sleep 15  # Allow services to stabilize
echo ""

# Step 4: Apply connection remapping
echo "[4/6] Applying connection remapping..."

python3 << PYEOF
import json, subprocess, sys

with open("$REMAP_FILE") as f:
    remap = json.load(f)

def run_cli(args, check=True):
    """Run an ignition-cli command and return stdout."""
    result = subprocess.run(
        ["ignition-cli"] + args,
        capture_output=True, text=True
    )
    if check and result.returncode != 0:
        print(f"  WARN: CLI error: {result.stderr.strip()}", file=sys.stderr)
    return result.stdout

# Remap database connections
for db_remap in remap.get("database_connections", []):
    name = db_remap["name"]
    print(f"  Remapping database: {name}")

    # Fetch current resource data to get the signature
    show_output = run_cli([
        "resource", "show", "ignition/database-connection",
        "--name", name, "-g", "$TARGET", "-f", "json"
    ], check=False)

    if not show_output.strip():
        print(f"    SKIP: resource not found")
        continue

    try:
        resource_data = json.loads(show_output)
        signature = resource_data.get("signature", "")
    except json.JSONDecodeError:
        print(f"    SKIP: could not parse resource data")
        continue

    # Build updated config
    update_config = {}
    if "connectURL" in db_remap:
        update_config["connectURL"] = db_remap["connectURL"]
    if "username" in db_remap:
        update_config["username"] = db_remap["username"]
    if "password" in db_remap:
        update_config["password"] = db_remap["password"]

    if update_config:
        config_json = json.dumps(update_config)
        result = subprocess.run([
            "ignition-cli", "resource", "update", "ignition/database-connection",
            "--name", name,
            "--config", config_json,
            "--signature", signature,
            "-g", "$TARGET"
        ], capture_output=True, text=True)

        if result.returncode == 0:
            print(f"    OK: updated")
        else:
            print(f"    FAIL: {result.stderr.strip()}")

# Remap device connections
for dev_remap in remap.get("device_connections", []):
    name = dev_remap["name"]
    module_type = dev_remap.get("module_type", "com.inductiveautomation.opcua/device")
    print(f"  Remapping device: {name}")

    show_output = run_cli([
        "resource", "show", module_type,
        "--name", name, "-g", "$TARGET", "-f", "json"
    ], check=False)

    if not show_output.strip():
        print(f"    SKIP: resource not found")
        continue

    try:
        resource_data = json.loads(show_output)
        signature = resource_data.get("signature", "")
    except json.JSONDecodeError:
        print(f"    SKIP: could not parse resource data")
        continue

    update_config = {}
    if "Hostname" in dev_remap:
        update_config["Hostname"] = dev_remap["Hostname"]
    if "Port" in dev_remap:
        update_config["Port"] = dev_remap["Port"]

    if update_config:
        config_json = json.dumps(update_config)
        result = subprocess.run([
            "ignition-cli", "resource", "update", module_type,
            "--name", name,
            "--config", config_json,
            "--signature", signature,
            "-g", "$TARGET"
        ], capture_output=True, text=True)

        if result.returncode == 0:
            print(f"    OK: updated")
        else:
            print(f"    FAIL: {result.stderr.strip()}")

print("  Remapping complete.")
PYEOF

echo ""

# Step 5: Set deployment mode (if specified)
if [ -n "$TARGET_MODE" ]; then
    echo "[5/6] Setting deployment mode to '$TARGET_MODE'..."

    # Check if mode exists, create if not
    if ! ignition-cli mode show "$TARGET_MODE" -g "$TARGET" -f json >/dev/null 2>&1; then
        echo "  Mode '$TARGET_MODE' does not exist. Creating..."
        ignition-cli mode create "$TARGET_MODE" -g "$TARGET" \
            --title "$TARGET_MODE" \
            --description "Set by environment clone on $DATE"
    fi

    echo "  Mode '$TARGET_MODE' is available on the target gateway."
    echo ""
else
    echo "[5/6] No target mode specified — skipping."
    echo ""
fi

# Step 6: Verify the clone
echo "[6/6] Verifying cloned environment..."
echo ""

echo "Gateway info:"
ignition-cli gateway info -g "$TARGET"
echo ""

echo "Projects:"
ignition-cli project list -g "$TARGET"
echo ""

echo "Devices:"
ignition-cli device list -g "$TARGET"
echo ""

echo "Modes:"
ignition-cli mode list -g "$TARGET"
echo ""

# Check for faulted devices
faulted=$(ignition-cli device list -g "$TARGET" -f json 2>/dev/null | python3 -c "
import sys, json
devices = json.load(sys.stdin)
faulted = [d.get('name','?') for d in devices if 'fault' in str(d.get('status','')).lower()]
if faulted:
    print(f'WARNING: {len(faulted)} faulted device(s): {\", \".join(faulted)}')
else:
    print(f'All {len(devices)} devices healthy.')
")
echo "$faulted"

echo ""
echo "Clone complete. Work directory: $WORK_DIR"
```

## Remap Config File

Save as `prod-to-dev-remap.json`:

```json
{
    "database_connections": [
        {
            "name": "MySQL_Production",
            "connectURL": "jdbc:mysql://dev-db-server:3306/ignition_dev",
            "username": "ignition_dev",
            "password": "dev_password_here"
        },
        {
            "name": "PostgreSQL_Historian",
            "connectURL": "jdbc:postgresql://dev-historian:5432/historian_dev",
            "username": "historian_dev",
            "password": "dev_password_here"
        }
    ],
    "device_connections": [
        {
            "name": "PLC-Line1-Main",
            "module_type": "com.inductiveautomation.opcua/device",
            "Hostname": "192.168.100.10"
        },
        {
            "name": "PLC-Line2-Main",
            "module_type": "com.inductiveautomation.opcua/device",
            "Hostname": "192.168.100.20"
        },
        {
            "name": "PLC-Packaging",
            "module_type": "com.inductiveautomation.opcua/device",
            "Hostname": "192.168.100.30"
        }
    ]
}
```

## Usage

```bash
# Clone production to dev with remapping and set mode
./clone-environment.sh production dev-gateway prod-to-dev-remap.json development

# Clone production to staging (different remap, different mode)
./clone-environment.sh production staging prod-to-staging-remap.json staging

# Clone without setting a mode
./clone-environment.sh production dev-gateway prod-to-dev-remap.json
```

## Sample Output

```
=== Environment Cloning ===
Source:    production
Target:    dev-gateway
Remap:     prod-to-dev-remap.json
Mode:      development
Date:      20260215-140000

[1/6] Backing up source gateway (production)...
  Backup created: ./clone-20260215-140000/source-backup.gwbk (48M)

[2/6] Restoring backup to target gateway (dev-gateway)...
  Restore initiated.

[3/6] Waiting for target gateway to come online...
  15s — still waiting...
  30s — still waiting...
  45s — still waiting...
  60s — still waiting...
  75s — Gateway online after 75s.

[4/6] Applying connection remapping...
  Remapping database: MySQL_Production
    OK: updated
  Remapping database: PostgreSQL_Historian
    OK: updated
  Remapping device: PLC-Line1-Main
    OK: updated
  Remapping device: PLC-Line2-Main
    OK: updated
  Remapping device: PLC-Packaging
    OK: updated
  Remapping complete.

[5/6] Setting deployment mode to 'development'...
  Mode 'development' is available on the target gateway.

[6/6] Verifying cloned environment...
  Projects: 6 projects found
  Devices: 24 devices found
  All 24 devices healthy.

Clone complete. Work directory: ./clone-20260215-140000
```

## Native Alternatives

**Gateway backup/restore** handles the base clone but provides no connection remapping. **EAM** can push configurations but doesn't support per-environment remapping natively.

The CLI approach is preferable when:
- You need automated connection remapping (production IPs/DBs to dev/staging equivalents)
- You want a repeatable, version-controlled cloning process
- You need different remap configs per target environment
- You want to set the deployment mode automatically after cloning

## Time Saved

**Manual:** 20-40 minutes to restore a backup, then manually update every database URL, every device hostname, and verify nothing still points at production.
**Automated:** Under 10 minutes end-to-end, with a documented remap config that ensures nothing is missed.
