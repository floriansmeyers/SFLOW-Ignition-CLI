# Scenario 4: Bulk Device Connection Commissioning from CSV

## Problem

Commissioning a new site or production line means creating dozens of OPC-UA device connections — one per PLC, one per I/O rack, one per VFD. Each connection is configured manually in the gateway web UI: name, hostname, port, scan class, security settings. For a 40-device site, that's an entire afternoon of repetitive clicking and a high risk of typos.

## What This Automates

- Reads device definitions from a CSV file
- Generates Ignition-compatible resource config for each device
- Creates all connections via the CLI in a single run
- Polls device status until connections come online (or timeout)
- Produces a commissioning report with success/faulted/timeout counts

## Script

```bash
#!/usr/bin/env bash
# commission-devices.sh — Bulk-create device connections from CSV
# Usage: commission-devices.sh <csv-file> [gateway-profile]
set -euo pipefail

CSV_FILE="${1:?Usage: commission-devices.sh <csv-file> [gateway-profile]}"
GATEWAY="${2:-production}"
POLL_TIMEOUT=120  # seconds to wait for devices to come online
POLL_INTERVAL=10
DATE=$(date +%Y%m%d-%H%M%S)
REPORT="commission-report-$DATE.txt"

if [ ! -f "$CSV_FILE" ]; then
    echo "ERROR: CSV file not found: $CSV_FILE"
    exit 1
fi

TOTAL=0
CREATED=0
FAILED=0

echo "=== Device Commissioning ==="
echo "CSV:      $CSV_FILE"
echo "Gateway:  $GATEWAY"
echo "Date:     $DATE"
echo ""

# Step 1: Parse CSV and create devices
echo "[1/3] Creating device connections..." | tee "$REPORT"

# Skip header line, process each row
tail -n +2 "$CSV_FILE" | while IFS=',' read -r name host port device_type scan_class; do
    # Trim whitespace
    name=$(echo "$name" | xargs)
    host=$(echo "$host" | xargs)
    port=$(echo "$port" | xargs)
    device_type=$(echo "$device_type" | xargs)
    scan_class=$(echo "$scan_class" | xargs)

    if [ -z "$name" ] || [ -z "$host" ]; then
        echo "  SKIP: Empty name or host — $name / $host" | tee -a "$REPORT"
        continue
    fi

    TOTAL=$((TOTAL + 1))

    # Build config JSON for this device
    config_json=$(python3 -c "
import json
config = {
    'Hostname': '$host',
    'Port': int('${port:-4840}'),
    'DeviceType': '${device_type:-OPC_UA}',
    'ScanClass': '${scan_class:-Default}'
}
print(json.dumps(config))
")

    echo "  Creating: $name ($host:${port:-4840})..." | tee -a "$REPORT"

    if ignition-cli resource create com.inductiveautomation.opcua/device \
        -g "$GATEWAY" \
        --name "$name" \
        --config "$config_json" 2>>"$REPORT"; then
        echo "    OK" | tee -a "$REPORT"
        CREATED=$((CREATED + 1))
    else
        echo "    FAILED" | tee -a "$REPORT"
        FAILED=$((FAILED + 1))
    fi
done

echo "" | tee -a "$REPORT"

# Step 2: Wait for devices to come online
echo "[2/3] Waiting for devices to connect (timeout: ${POLL_TIMEOUT}s)..." | tee -a "$REPORT"

elapsed=0
while [ $elapsed -lt $POLL_TIMEOUT ]; do
    sleep $POLL_INTERVAL
    elapsed=$((elapsed + POLL_INTERVAL))

    status_json=$(ignition-cli device list -g "$GATEWAY" -f json 2>/dev/null || echo "[]")

    counts=$(echo "$status_json" | python3 -c "
import sys, json
devices = json.load(sys.stdin)
connected = sum(1 for d in devices if 'connect' in str(d.get('status','')).lower())
faulted = sum(1 for d in devices if 'fault' in str(d.get('status','')).lower())
total = len(devices)
print(f'{connected} {faulted} {total}')
")
    connected=$(echo "$counts" | cut -d' ' -f1)
    faulted=$(echo "$counts" | cut -d' ' -f2)
    total_devices=$(echo "$counts" | cut -d' ' -f3)

    echo "  ${elapsed}s — connected: $connected, faulted: $faulted, total: $total_devices"

    if [ "$faulted" = "0" ] && [ "$connected" = "$total_devices" ] && [ "$total_devices" -gt 0 ]; then
        echo "  All devices connected." | tee -a "$REPORT"
        break
    fi
done

echo "" | tee -a "$REPORT"

# Step 3: Generate final report
echo "[3/3] Commissioning Report" | tee -a "$REPORT"
echo "=========================" | tee -a "$REPORT"
echo "" | tee -a "$REPORT"
echo "Device status after commissioning:" | tee -a "$REPORT"
ignition-cli device list -g "$GATEWAY" -f table 2>/dev/null | tee -a "$REPORT"
echo "" | tee -a "$REPORT"
echo "Summary:" | tee -a "$REPORT"
echo "  Created:  $CREATED" | tee -a "$REPORT"
echo "  Failed:   $FAILED" | tee -a "$REPORT"
echo "" | tee -a "$REPORT"
echo "Report saved: $REPORT"
```

## Sample CSV

Save as `devices.csv`:

```csv
name,host,port,device_type,scan_class
PLC-Line1-Main,192.168.10.10,4840,OPC_UA,Default
PLC-Line1-Safety,192.168.10.11,4840,OPC_UA,Safety_1s
PLC-Line2-Main,192.168.10.20,4840,OPC_UA,Default
PLC-Line2-Safety,192.168.10.21,4840,OPC_UA,Safety_1s
PLC-Packaging-1,192.168.10.30,4840,OPC_UA,Default
PLC-Packaging-2,192.168.10.31,4840,OPC_UA,Default
PLC-Palletizer,192.168.10.40,4840,OPC_UA,Default
VFD-Conveyor-1,192.168.10.50,502,Modbus,Fast_500ms
VFD-Conveyor-2,192.168.10.51,502,Modbus,Fast_500ms
VFD-Conveyor-3,192.168.10.52,502,Modbus,Fast_500ms
IO-Rack-Line1,192.168.10.100,4840,OPC_UA,Default
IO-Rack-Line2,192.168.10.101,4840,OPC_UA,Default
HMI-Panel-1,192.168.10.200,4840,OPC_UA,Slow_5s
HMI-Panel-2,192.168.10.201,4840,OPC_UA,Slow_5s
Temp-Monitor-1,192.168.10.110,4840,OPC_UA,Default
Temp-Monitor-2,192.168.10.111,4840,OPC_UA,Default
```

## Usage

```bash
# Commission devices on the production gateway
./commission-devices.sh devices.csv production

# Commission on a staging gateway
./commission-devices.sh devices.csv staging

# View the report
cat commission-report-*.txt
```

## Sample Output

```
=== Device Commissioning ===
CSV:      devices.csv
Gateway:  production
Date:     20260215-091500

[1/3] Creating device connections...
  Creating: PLC-Line1-Main (192.168.10.10:4840)...
    OK
  Creating: PLC-Line1-Safety (192.168.10.11:4840)...
    OK
  Creating: VFD-Conveyor-1 (192.168.10.50:502)...
    OK
  ...

[2/3] Waiting for devices to connect (timeout: 120s)...
  10s — connected: 8, faulted: 0, total: 16
  20s — connected: 14, faulted: 1, total: 16
  30s — connected: 15, faulted: 1, total: 16
  40s — connected: 16, faulted: 0, total: 16
  All devices connected.

[3/3] Commissioning Report
=========================
  Created:  16
  Failed:   0
```

## Native Alternatives

**EAM** can push device connection configurations from a controller to agents. The **Ignition web UI** supports creating devices one at a time.

The CLI approach is preferable when:
- You're commissioning a new site with dozens of devices
- Device specs come from an engineering spreadsheet (CSV/Excel)
- You need a repeatable process for identical sites (template CSV per site type)
- You want a commissioning report for project documentation

## Time Saved

**Manual:** 2-5 minutes per device in the web UI. A 40-device site takes 1-3 hours.
**Automated:** All devices created and verified in under 5 minutes. Same CSV can be reused for identical sites.
