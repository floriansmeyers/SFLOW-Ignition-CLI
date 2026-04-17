#!/usr/bin/env bash
# audit-collect.sh — Phase 1: Collect gateway data for compliance audit
# Usage: audit-collect.sh [output-directory]
set -uo pipefail

OUTDIR="${1:-audit-data}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
OUTDIR="$OUTDIR/$TIMESTAMP"

echo "=== Compliance Audit — Data Collection ==="
echo "Output:    $OUTDIR"
echo "Timestamp: $TIMESTAMP"
echo ""

# Get list of configured gateways
GATEWAYS=$(ignition-cli config list -f json | python3 -c "
import sys, json
data = json.load(sys.stdin)
for p in data.get('profiles', []):
    print(p['name'])
")

if [ -z "$GATEWAYS" ]; then
    echo "ERROR: No gateway profiles configured. Run 'ignition-cli config add' first."
    exit 1
fi

echo "Gateways found:"
for gw in $GATEWAYS; do
    echo "  - $gw"
done
echo ""

collect_gateway() {
    local gw="$1"
    local dir="$OUTDIR/$gw"
    mkdir -p "$dir"

    echo "[$gw] Collecting data..."

    ignition-cli gateway info -g "$gw" -f json > "$dir/info.json" 2>/dev/null \
        || echo '{}' > "$dir/info.json"

    ignition-cli gateway status -g "$gw" -f json > "$dir/status.json" 2>/dev/null \
        || echo '{}' > "$dir/status.json"

    ignition-cli gateway modules -g "$gw" -f json > "$dir/modules.json" 2>/dev/null \
        || echo '{}' > "$dir/modules.json"

    ignition-cli gateway logs -g "$gw" -n 200 -f json > "$dir/logs.json" 2>/dev/null \
        || echo '{}' > "$dir/logs.json"

    ignition-cli project list -g "$gw" -f json > "$dir/projects.json" 2>/dev/null \
        || echo '{}' > "$dir/projects.json"

    ignition-cli mode list -g "$gw" -f json > "$dir/modes.json" 2>/dev/null \
        || echo '{}' > "$dir/modes.json"

    ignition-cli device list -g "$gw" -f json > "$dir/devices.json" 2>/dev/null \
        || echo '{}' > "$dir/devices.json"

    ignition-cli tag providers -g "$gw" -f json > "$dir/providers.json" 2>/dev/null \
        || echo '{}' > "$dir/providers.json"

    echo "[$gw] Done (8 files)"
}

for gw in $GATEWAYS; do
    collect_gateway "$gw"
done

echo "$TIMESTAMP" > "$OUTDIR/timestamp.txt"

echo ""
echo "Collection complete: $OUTDIR"
echo "Run audit-report.sh to generate the compliance report."
