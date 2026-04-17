# Scenario 7: Compliance Audit Report Generator

## Problem

Auditors show up and ask: "Show us the current state of all your Ignition gateways. Are they all on supported versions? Are there any faulted devices? Any error spikes in the logs? Are required modules installed everywhere?" Answering these questions means logging into every gateway, taking screenshots, pasting into a Word document, and hoping you didn't miss anything. For a fleet of 10+ gateways, this takes a full day.

## What This Automates

- Queries all fleet gateways for version, modules, projects, devices, modes, and logs
- Applies configurable compliance rules (minimum version, required modules, max errors)
- Generates a markdown report with per-gateway compliance status
- Highlights non-compliant items for immediate attention
- Timestamps the report for audit trail purposes

## Script

```bash
#!/usr/bin/env bash
# compliance-audit.sh — Generate a compliance audit report across all gateways
# Usage: compliance-audit.sh [rules-file]
set -euo pipefail

RULES_FILE="${1:-./compliance-rules.json}"
DATE=$(date +%Y%m%d-%H%M%S)
REPORT="compliance-report-$DATE.md"

# Default fleet — override via FLEET_GATEWAYS env var
IFS=',' read -ra GATEWAYS <<< "${FLEET_GATEWAYS:-production,staging,edge-1,edge-2,edge-3}"

echo "=== Compliance Audit Report Generator ==="
echo "Gateways: ${GATEWAYS[*]}"
echo "Rules:    $RULES_FILE"
echo "Date:     $DATE"
echo ""

# Step 1: Load compliance rules
echo "[1/3] Loading compliance rules..."

if [ -f "$RULES_FILE" ]; then
    echo "  Using rules from $RULES_FILE"
else
    echo "  No rules file found. Using defaults."
    cat > "$RULES_FILE" << 'RULES'
{
    "min_version": "8.3.0",
    "required_modules": [
        "OPC-UA",
        "Perspective",
        "Allen-Bradley Drivers"
    ],
    "max_error_log_lines": 50,
    "required_modes": [],
    "max_faulted_devices": 0
}
RULES
    echo "  Default rules written to $RULES_FILE"
fi

echo ""

# Step 2: Collect data and generate report
echo "[2/3] Collecting data from all gateways..."

# Start the report
cat > "$REPORT" << HEADER
# Compliance Audit Report

**Generated:** $(date '+%Y-%m-%d %H:%M:%S')
**Gateways audited:** ${#GATEWAYS[@]}
**Rules file:** $RULES_FILE

---

HEADER

# Collect data from each gateway
for gw in "${GATEWAYS[@]}"; do
    echo "  Querying $gw..."

    gw_info=$(ignition-cli gateway info -g "$gw" -f json 2>/dev/null || echo '{"error":"unreachable"}')
    gw_modules=$(ignition-cli gateway modules -g "$gw" -f json 2>/dev/null || echo '[]')
    gw_projects=$(ignition-cli project list -g "$gw" -f json 2>/dev/null || echo '[]')
    gw_devices=$(ignition-cli device list -g "$gw" -f json 2>/dev/null || echo '[]')
    gw_modes=$(ignition-cli mode list -g "$gw" -f json 2>/dev/null || echo '[]')
    gw_logs=$(ignition-cli gateway logs -g "$gw" -f json --level WARN 2>/dev/null || echo '[]')

    # Run compliance checks and append to report
    python3 << PYEOF
import json

gw_name = "$gw"
rules_file = "$RULES_FILE"
report_file = "$REPORT"

with open(rules_file) as f:
    rules = json.load(f)

info = json.loads('''$(echo "$gw_info" | sed "s/'/\\\\'/g")''')
modules = json.loads('''$(echo "$gw_modules" | sed "s/'/\\\\'/g")''')
projects = json.loads('''$(echo "$gw_projects" | sed "s/'/\\\\'/g")''')
devices = json.loads('''$(echo "$gw_devices" | sed "s/'/\\\\'/g")''')
modes_data = json.loads('''$(echo "$gw_modes" | sed "s/'/\\\\'/g")''')
logs = json.loads('''$(echo "$gw_logs" | sed "s/'/\\\\'/g")''')

findings = []
compliant = True

# Check: Gateway reachable
if "error" in info:
    findings.append(("FAIL", "Gateway unreachable"))
    compliant = False
else:
    findings.append(("PASS", f"Gateway reachable"))

    # Check: Version
    version = info.get("version", "0.0.0")
    min_ver = rules.get("min_version", "0.0.0")
    ver_parts = [int(x) for x in version.split(".")[:3]]
    min_parts = [int(x) for x in min_ver.split(".")[:3]]
    if ver_parts >= min_parts:
        findings.append(("PASS", f"Version {version} >= {min_ver}"))
    else:
        findings.append(("FAIL", f"Version {version} < {min_ver} (minimum required)"))
        compliant = False

    # Check: Required modules
    module_names = [m.get("name", "") for m in modules]
    for req in rules.get("required_modules", []):
        if req in module_names:
            findings.append(("PASS", f"Module present: {req}"))
        else:
            findings.append(("FAIL", f"Module MISSING: {req}"))
            compliant = False

    # Check: Quarantined modules
    quarantined = [m.get("name", "?") for m in modules if m.get("state", "").lower() == "quarantined"]
    if quarantined:
        findings.append(("WARN", f"Quarantined modules: {', '.join(quarantined)}"))
    else:
        findings.append(("PASS", "No quarantined modules"))

    # Check: Faulted devices
    faulted = [d.get("name", "?") for d in devices if "fault" in str(d.get("status", "")).lower()]
    max_faulted = rules.get("max_faulted_devices", 0)
    if len(faulted) > max_faulted:
        findings.append(("FAIL", f"Faulted devices ({len(faulted)}): {', '.join(faulted)}"))
        compliant = False
    elif faulted:
        findings.append(("WARN", f"Faulted devices ({len(faulted)}): {', '.join(faulted)}"))
    else:
        findings.append(("PASS", f"All {len(devices)} devices healthy"))

    # Check: Error log count
    log_list = logs if isinstance(logs, list) else []
    max_errors = rules.get("max_error_log_lines", 50)
    if len(log_list) > max_errors:
        findings.append(("WARN", f"Warning/error log entries: {len(log_list)} (threshold: {max_errors})"))
    else:
        findings.append(("PASS", f"Warning/error log entries: {len(log_list)} (within threshold)"))

    # Check: Required modes
    if isinstance(modes_data, dict):
        modes_list = modes_data.get("items", [])
    else:
        modes_list = modes_data
    mode_names = [m.get("name", "") for m in modes_list]
    for req_mode in rules.get("required_modes", []):
        if req_mode in mode_names:
            findings.append(("PASS", f"Mode present: {req_mode}"))
        else:
            findings.append(("FAIL", f"Mode MISSING: {req_mode}"))
            compliant = False

# Write gateway section to report
with open(report_file, "a") as f:
    status_label = "COMPLIANT" if compliant else "NON-COMPLIANT"
    f.write(f"## {gw_name} — {status_label}\n\n")

    if "error" not in info:
        f.write(f"- **Version:** {info.get('version', '?')}\n")
        f.write(f"- **Edition:** {info.get('edition', '?')}\n")
        f.write(f"- **Modules:** {len(modules)}\n")
        f.write(f"- **Projects:** {len(projects)}\n")
        f.write(f"- **Devices:** {len(devices)}\n")
        f.write(f"- **Modes:** {len(modes_list)}\n")
    f.write(f"\n")

    f.write(f"| Status | Finding |\n")
    f.write(f"|--------|---------|\n")
    for status, msg in findings:
        f.write(f"| {status} | {msg} |\n")
    f.write(f"\n---\n\n")

status_word = "COMPLIANT" if compliant else "NON-COMPLIANT"
print(f"    {gw_name}: {status_word} ({sum(1 for s,_ in findings if s=='PASS')} pass, {sum(1 for s,_ in findings if s=='FAIL')} fail, {sum(1 for s,_ in findings if s=='WARN')} warn)")
PYEOF
done

echo ""

# Step 3: Add summary
echo "[3/3] Generating summary..."

python3 << PYEOF
report_file = "$REPORT"

with open(report_file) as f:
    content = f.read()

pass_total = content.count("| PASS |")
fail_total = content.count("| FAIL |")
warn_total = content.count("| WARN |")
compliant_gw = content.count("COMPLIANT") - content.count("NON-COMPLIANT")
non_compliant_gw = content.count("NON-COMPLIANT")

summary = f"""## Summary

| Metric | Count |
|--------|-------|
| Gateways audited | {compliant_gw + non_compliant_gw} |
| Compliant | {compliant_gw} |
| Non-compliant | {non_compliant_gw} |
| Total checks passed | {pass_total} |
| Total checks failed | {fail_total} |
| Total warnings | {warn_total} |

"""

if non_compliant_gw > 0:
    summary += "**Overall: NON-COMPLIANT** — Review failed checks above.\n"
else:
    summary += "**Overall: COMPLIANT** — All gateways meet compliance requirements.\n"

with open(report_file, "a") as f:
    f.write(summary)

print(f"  Compliant: {compliant_gw}, Non-compliant: {non_compliant_gw}")
print(f"  Checks: {pass_total} pass, {fail_total} fail, {warn_total} warn")
PYEOF

echo ""
echo "Report saved: $REPORT"
```

## Compliance Rules File

Save as `compliance-rules.json`:

```json
{
    "min_version": "8.3.0",
    "required_modules": [
        "OPC-UA",
        "Perspective",
        "Allen-Bradley Drivers",
        "Reporting"
    ],
    "max_error_log_lines": 50,
    "required_modes": ["production", "staging"],
    "max_faulted_devices": 0
}
```

## Usage

```bash
# Run with default rules
./compliance-audit.sh

# Run with custom rules
./compliance-audit.sh ./my-rules.json

# Override fleet list via environment variable
FLEET_GATEWAYS="prod-us,prod-eu,prod-asia" ./compliance-audit.sh

# Schedule quarterly audits (1st of Jan, Apr, Jul, Oct at midnight)
crontab -e
# 0 0 1 1,4,7,10 * /opt/scripts/compliance-audit.sh >> /var/log/compliance-audit.log 2>&1
```

## Sample Report Output

```markdown
# Compliance Audit Report

**Generated:** 2026-03-01 00:00:00
**Gateways audited:** 5
**Rules file:** ./compliance-rules.json

---

## production — COMPLIANT

- **Version:** 8.3.3
- **Modules:** 14
- **Projects:** 6
- **Devices:** 24
- **Modes:** 3

| Status | Finding |
|--------|---------|
| PASS | Gateway reachable |
| PASS | Version 8.3.3 >= 8.3.0 |
| PASS | Module present: OPC-UA |
| PASS | Module present: Perspective |
| PASS | Module present: Allen-Bradley Drivers |
| PASS | Module present: Reporting |
| PASS | No quarantined modules |
| PASS | All 24 devices healthy |
| PASS | Warning/error log entries: 12 (within threshold) |

---

## edge-2 — NON-COMPLIANT

- **Version:** 8.1.33
- **Modules:** 8
- **Projects:** 2
- **Devices:** 6
- **Modes:** 1

| Status | Finding |
|--------|---------|
| PASS | Gateway reachable |
| FAIL | Version 8.1.33 < 8.3.0 (minimum required) |
| PASS | Module present: OPC-UA |
| FAIL | Module MISSING: Perspective |
| PASS | Module present: Allen-Bradley Drivers |
| FAIL | Module MISSING: Reporting |
| PASS | No quarantined modules |
| FAIL | Faulted devices (1): PLC-Aux-1 |
| WARN | Warning/error log entries: 87 (threshold: 50) |

---

## Summary

| Metric | Count |
|--------|-------|
| Gateways audited | 5 |
| Compliant | 4 |
| Non-compliant | 1 |
| Total checks passed | 38 |
| Total checks failed | 4 |
| Total warnings | 2 |

**Overall: NON-COMPLIANT** — Review failed checks above.
```

## Native Alternatives

**EAM** provides a centralized dashboard for managed agents with version and status information. The **Gateway Webpage** shows per-gateway status.

The CLI approach is preferable when:
- You need a single report covering your entire fleet
- You need configurable, version-controlled compliance rules
- You need timestamped reports for audit evidence
- You manage gateways not enrolled in EAM
- You need to integrate compliance checks into CI/CD or scheduled jobs

## Time Saved

**Manual:** 30-60 minutes logging into each gateway, checking each item, assembling a report. More for larger fleets.
**Automated:** Full fleet audit in under 5 minutes with a machine-readable markdown report.
