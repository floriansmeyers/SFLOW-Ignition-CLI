# Scenario 3: Full Gateway Resource Inventory and Documentation

## Problem

You need a complete inventory of what's configured on a gateway — database connections, device connections, tag providers, custom resources — for documentation, compliance audits, migration planning, or disaster recovery. Gathering this manually from the web UI means clicking through dozens of pages and copy-pasting into a spreadsheet.

## What This Automates

- Discovers all resource types on the gateway via the OpenAPI spec
- Lists every resource instance of each type
- Exports full configuration for each resource
- Produces a structured inventory (JSON and CSV)
- Creates a human-readable summary report

## Script

```bash
#!/usr/bin/env bash
# gateway-inventory.sh — Export a full resource inventory from a gateway
set -uo pipefail

GATEWAY="${1:?Usage: gateway-inventory.sh <gateway-profile> [output-dir]}"
OUTPUT_DIR="${2:-./inventory-$(date +%Y%m%d)}"

mkdir -p "$OUTPUT_DIR"

echo "=== Gateway Resource Inventory ==="
echo "Gateway: $GATEWAY"
echo "Output:  $OUTPUT_DIR"
echo ""

# Gateway info header
echo "--- Gateway Info ---"
ignition-cli gateway info -g "$GATEWAY" -f json > "$OUTPUT_DIR/gateway-info.json"
ignition-cli gateway info -g "$GATEWAY"
echo ""

# Modules
echo "--- Installed Modules ---"
ignition-cli gateway modules -g "$GATEWAY" -f json > "$OUTPUT_DIR/modules.json"
ignition-cli gateway modules -g "$GATEWAY"
echo ""

# Projects
echo "--- Projects ---"
ignition-cli project list -g "$GATEWAY" -f json > "$OUTPUT_DIR/projects.json"
ignition-cli project list -g "$GATEWAY" -f csv > "$OUTPUT_DIR/projects.csv"
ignition-cli project list -g "$GATEWAY"
echo ""

# Deployment modes
echo "--- Deployment Modes ---"
ignition-cli mode list -g "$GATEWAY" -f json > "$OUTPUT_DIR/modes.json"
ignition-cli mode list -g "$GATEWAY"
echo ""

# Devices
echo "--- Device Connections ---"
ignition-cli device list -g "$GATEWAY" -f json > "$OUTPUT_DIR/devices.json"
ignition-cli device list -g "$GATEWAY" -f csv > "$OUTPUT_DIR/devices.csv"
ignition-cli device list -g "$GATEWAY"
echo ""

# Tag providers
echo "--- Tag Providers ---"
ignition-cli tag providers -g "$GATEWAY" -f json > "$OUTPUT_DIR/tag-providers.json"
ignition-cli tag providers -g "$GATEWAY"
echo ""

# Discover and inventory all resource types
echo "--- Resource Types ---"
resource_types=$(ignition-cli resource types -g "$GATEWAY" 2>/dev/null | \
    python3 -c "
import sys
lines = sys.stdin.readlines()
# Skip table header/footer, extract module/type values
for line in lines:
    line = line.strip().strip('│').strip()
    if '/' in line and not line.startswith('─') and not line.startswith('Module') and 'Module/Type' not in line:
        print(line)
" 2>/dev/null)

mkdir -p "$OUTPUT_DIR/resources"

echo "$resource_types" | while IFS= read -r rtype; do
    [ -z "$rtype" ] && continue
    safe_name=$(echo "$rtype" | tr '/' '_')
    echo "  Inventorying: $rtype"

    # List resources of this type
    ignition-cli resource list "$rtype" -g "$GATEWAY" -f json \
        > "$OUTPUT_DIR/resources/${safe_name}.json" 2>/dev/null || true
done
echo ""

# Summary report
echo "--- Generating Summary ---"
python3 << PYSCRIPT
import json
import os
import csv

output_dir = "$OUTPUT_DIR"

summary = []
summary.append("=" * 60)
summary.append("GATEWAY INVENTORY REPORT")
summary.append("=" * 60)
summary.append("")

# Gateway info
try:
    with open(f"{output_dir}/gateway-info.json") as f:
        info = json.load(f)
    summary.append(f"Gateway: {info.get('name', '?')}")
    summary.append(f"Version: {info.get('ignitionVersion', '?')}")
    summary.append(f"Edition: {info.get('edition', '?')}")
    summary.append("")
except:
    pass

# Projects
try:
    with open(f"{output_dir}/projects.json") as f:
        data = json.load(f)
    projects = data.get("items", data) if isinstance(data, dict) else data
    if isinstance(projects, list):
        summary.append(f"Projects: {len(projects)}")
        for p in projects:
            name = p.get("name", "?")
            enabled = p.get("enabled", "?")
            summary.append(f"  - {name} (enabled={enabled})")
        summary.append("")
except:
    pass

# Devices
try:
    with open(f"{output_dir}/devices.json") as f:
        data = json.load(f)
    devices = data.get("items", data) if isinstance(data, dict) else data
    if isinstance(devices, list):
        summary.append(f"Device Connections: {len(devices)}")
        for d in devices:
            name = d.get("name", "?")
            status = d.get("status", "?")
            summary.append(f"  - {name} ({status})")
        summary.append("")
except:
    pass

# Resources
summary.append("Resources by Type:")
res_dir = f"{output_dir}/resources"
if os.path.isdir(res_dir):
    for fname in sorted(os.listdir(res_dir)):
        if not fname.endswith(".json"):
            continue
        try:
            with open(f"{res_dir}/{fname}") as f:
                data = json.load(f)
            items = data.get("items", data) if isinstance(data, dict) else data
            count = len(items) if isinstance(items, list) else 0
            rtype = fname.replace(".json", "").replace("_", "/", 1)
            if count > 0:
                summary.append(f"  {rtype}: {count}")
        except:
            pass
summary.append("")

report = "\n".join(summary)
print(report)
with open(f"{output_dir}/SUMMARY.txt", "w") as f:
    f.write(report)
PYSCRIPT

echo ""
echo "Inventory exported to: $OUTPUT_DIR/"
echo "Files:"
ls -la "$OUTPUT_DIR/"
```

## Usage

```bash
# Inventory a single gateway
./gateway-inventory.sh production

# Inventory with custom output directory
./gateway-inventory.sh production ./audits/production-2026-Q1

# Inventory all gateways
for gw in production staging edge-site-1; do
    ./gateway-inventory.sh "$gw" "./inventory/$gw"
done
```

## Output Structure

```
inventory-20260210/
├── SUMMARY.txt
├── gateway-info.json
├── modules.json
├── projects.json
├── projects.csv
├── modes.json
├── devices.json
├── devices.csv
├── tag-providers.json
└── resources/
    ├── ignition_database-connection.json
    ├── ignition_tag-provider.json
    ├── com.inductiveautomation.opcua_device.json
    └── ...
```

## Native Alternatives

No native equivalent. Gateway backup contains all configuration but as a binary blob, not browsable JSON/CSV.

## Time Saved

**Manual:** 10-20 minutes per gateway, clicking through config pages and copy-pasting into a spreadsheet.
**Automated:** Under 2 minutes per gateway. Machine-readable output ready for audits or diffing.
