# Scenario 7: Fleet Compliance Audit Report

## Problem

You manage a fleet of Ignition gateways across multiple sites or environments. Regulatory requirements, internal SOPs, or customer contracts demand periodic proof that every gateway meets baseline standards — correct firmware version, required modules installed, no faulted devices, acceptable error rates. Today this means logging into each gateway's web UI, manually checking each item, and pasting screenshots into a spreadsheet. It doesn't scale, and it's easy to miss something.

## What This Automates

- Queries every configured gateway for version, modules, devices, logs, tags, projects, and modes
- Applies configurable compliance rules (minimum version, required modules, error thresholds)
- Flags faulted device connections and unhealthy tag providers
- Inventories projects (flagging disabled ones) and deployment modes
- Produces a timestamped Markdown audit report with per-gateway sections and a fleet summary
- Separates data collection from report generation so you can re-run reports with different rules without re-querying gateways

## Scripts

This scenario uses a **two-phase approach** with three files:

| File | Purpose |
|------|---------|
| `audit-rules.json` | Configurable compliance rules (version, modules, error threshold) |
| `audit-collect.sh` | Phase 1 — queries all gateways, saves raw JSON to an output directory |
| `audit-report.sh` | Phase 2 — reads collected JSON, applies rules, emits a Markdown report |

### Phase 1: Data Collection (`audit-collect.sh`)

```bash
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
```

### Phase 2: Report Generation (`audit-report.sh`)

```bash
#!/usr/bin/env bash
# audit-report.sh — Phase 2: Generate Markdown compliance report from collected data
# Usage: audit-report.sh [data-directory] [rules-file]
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATADIR="${1:-audit-data}"
RULES="${2:-$SCRIPT_DIR/audit-rules.json}"

# Find the most recent collection if a timestamp dir isn't specified directly
if [ -f "$DATADIR/timestamp.txt" ]; then
    AUDIT_DIR="$DATADIR"
else
    AUDIT_DIR=$(ls -1d "$DATADIR"/[0-9]* 2>/dev/null | sort -r | head -1)
    if [ -z "$AUDIT_DIR" ] || [ ! -f "$AUDIT_DIR/timestamp.txt" ]; then
        echo "ERROR: No audit data found in $DATADIR"
        echo "Run audit-collect.sh first."
        exit 1
    fi
fi

TIMESTAMP=$(cat "$AUDIT_DIR/timestamp.txt")
REPORT="compliance-report-$TIMESTAMP.md"

echo "=== Compliance Audit — Report Generation ==="
echo "Data:   $AUDIT_DIR"
echo "Rules:  $RULES"
echo "Report: $REPORT"
echo ""

AUDIT_DIR="$AUDIT_DIR" RULES="$RULES" REPORT="$REPORT" python3 << 'PYEOF'
import json, os, sys
from datetime import datetime

audit_dir = os.environ["AUDIT_DIR"]
rules_file = os.environ["RULES"]
report_file = os.environ["REPORT"]

with open(rules_file) as f:
    rules = json.load(f)

min_version = rules.get("min_version", "8.3.0")
required_modules = rules.get("required_modules", [])
max_error_count = rules.get("max_error_count", 25)

gateways = sorted([
    d for d in os.listdir(audit_dir)
    if os.path.isdir(os.path.join(audit_dir, d))
])

def load_json(gw, filename):
    path = os.path.join(audit_dir, gw, filename)
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def extract_items(data, *keys):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ("items",) + keys:
            if k in data and isinstance(data[k], list):
                return data[k]
    return []

def version_tuple(v):
    try:
        return tuple(int(x) for x in str(v).split("."))
    except (ValueError, AttributeError):
        return (0, 0, 0)

results = {}
summary = {}

for gw in gateways:
    checks = []

    # Version check
    info = load_json(gw, "info.json")
    raw_version = info.get("ignitionVersion", info.get("version", "unknown"))
    version = raw_version.split(" ")[0] if raw_version != "unknown" else "unknown"
    if version == "unknown":
        checks.append(("Gateway Version", "FAIL", "Could not read version"))
    elif version_tuple(version) >= version_tuple(min_version):
        checks.append(("Gateway Version", "PASS",
                        "v{} (minimum: {})".format(version, min_version)))
    else:
        checks.append(("Gateway Version", "FAIL",
                        "v{} below minimum {}".format(version, min_version)))

    # Required modules
    modules = extract_items(load_json(gw, "modules.json"), "modules")
    installed_ids = {m.get("id", "") for m in modules}
    missing = [mid for mid in required_modules if mid not in installed_ids]
    if not missing:
        checks.append(("Required Modules", "PASS",
                        "All {} required modules present".format(len(required_modules))))
    else:
        checks.append(("Required Modules", "FAIL",
                        "Missing: {}".format(", ".join(missing))))

    # Faulted devices
    devices = extract_items(load_json(gw, "devices.json"), "resources")
    faulted = [d.get("name", "?") for d in devices
               if "Connected" not in str(d.get("state", ""))]
    if not devices:
        checks.append(("Device Connections", "PASS", "No devices configured"))
    elif not faulted:
        checks.append(("Device Connections", "PASS",
                        "All {} devices connected".format(len(devices))))
    else:
        names = ", ".join(faulted[:5])
        suffix = " (+{} more)".format(len(faulted) - 5) if len(faulted) > 5 else ""
        checks.append(("Device Connections", "FAIL",
                        "{} of {} not connected: {}{}".format(
                            len(faulted), len(devices), names, suffix)))

    # Error log spike
    logs = extract_items(load_json(gw, "logs.json"), "logs")
    error_count = sum(1 for e in logs if e.get("level", "") == "ERROR")
    if error_count == 0:
        checks.append(("Error Log Count", "PASS", "No ERROR entries in recent logs"))
    elif error_count <= max_error_count:
        checks.append(("Error Log Count", "PASS",
                        "{} errors (threshold: {})".format(error_count, max_error_count)))
    else:
        checks.append(("Error Log Count", "FAIL",
                        "{} errors exceeds threshold of {}".format(
                            error_count, max_error_count)))

    # Tag provider health
    providers = extract_items(load_json(gw, "providers.json"), "resources")
    unhealthy = []
    for p in providers:
        hc = p.get("healthchecks", {})
        if isinstance(hc, dict):
            for _, check_val in hc.items():
                if isinstance(check_val, dict):
                    st = str(check_val.get("status", ""))
                    if st and st.upper() != "GOOD":
                        unhealthy.append(p.get("name", "?"))
                        break
    if not providers:
        checks.append(("Tag Provider Health", "WARN", "No tag providers found"))
    elif not unhealthy:
        checks.append(("Tag Provider Health", "PASS",
                        "All {} providers healthy".format(len(providers))))
    else:
        checks.append(("Tag Provider Health", "FAIL",
                        "Unhealthy: {}".format(", ".join(unhealthy))))

    # Project inventory
    projects = extract_items(load_json(gw, "projects.json"), "projects")
    disabled = [p.get("name", "?") for p in projects if not p.get("enabled", True)]
    if not projects:
        checks.append(("Project Inventory", "WARN", "No projects found"))
    elif not disabled:
        checks.append(("Project Inventory", "PASS",
                        "{} project(s), all enabled".format(len(projects))))
    else:
        checks.append(("Project Inventory", "WARN",
                        "{} of {} disabled: {}".format(
                            len(disabled), len(projects), ", ".join(disabled))))

    # Mode inventory
    modes = extract_items(load_json(gw, "modes.json"))
    mode_names = [m.get("name", "?") for m in modes]
    if modes:
        checks.append(("Deployment Modes", "PASS",
                        "{} mode(s): {}".format(len(modes), ", ".join(mode_names))))
    else:
        checks.append(("Deployment Modes", "WARN", "No deployment modes configured"))

    results[gw] = checks
    summary[gw] = {
        "pass": sum(1 for _, s, _ in checks if s == "PASS"),
        "fail": sum(1 for _, s, _ in checks if s == "FAIL"),
        "warn": sum(1 for _, s, _ in checks if s == "WARN"),
    }

# Generate Markdown
lines = []
lines.append("# Compliance Audit Report")
lines.append("")
lines.append("**Generated:** {}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
lines.append("**Data collected:** {}".format(audit_dir))
lines.append("**Rules:** {}".format(rules_file))
lines.append("**Gateways audited:** {}".format(len(gateways)))
lines.append("")
lines.append("## Compliance Rules")
lines.append("")
lines.append("| Rule | Value |")
lines.append("|------|-------|")
lines.append("| Minimum version | {} |".format(min_version))
lines.append("| Required modules | {} |".format(", ".join(required_modules) or "(none)"))
lines.append("| Max ERROR log entries | {} |".format(max_error_count))
lines.append("")

for gw in gateways:
    s = summary[gw]
    total = s["pass"] + s["fail"] + s["warn"]
    score = round(s["pass"] / total * 100) if total > 0 else 0
    label = "FAIL" if s["fail"] > 0 else ("WARN" if s["warn"] > 0 else "PASS")
    lines.append("## Gateway: {} — {} ({}%)".format(gw, label, score))
    lines.append("")
    lines.append("| Check | Status | Detail |")
    lines.append("|-------|--------|--------|")
    for check_name, status, detail in results[gw]:
        lines.append("| {} | **{}** | {} |".format(check_name, status, detail))
    lines.append("")

lines.append("## Fleet Summary")
lines.append("")
lines.append("| Gateway | Pass | Fail | Warn | Score |")
lines.append("|---------|------|------|------|-------|")
tp, tf, tw = 0, 0, 0
for gw in gateways:
    s = summary[gw]
    total = s["pass"] + s["fail"] + s["warn"]
    score = round(s["pass"] / total * 100) if total > 0 else 0
    lines.append("| {} | {} | {} | {} | {}% |".format(
        gw, s["pass"], s["fail"], s["warn"], score))
    tp += s["pass"]; tf += s["fail"]; tw += s["warn"]

grand = tp + tf + tw
fleet_score = round(tp / grand * 100) if grand > 0 else 0
lines.append("| **Fleet Total** | **{}** | **{}** | **{}** | **{}%** |".format(
    tp, tf, tw, fleet_score))
lines.append("")

if tf == 0:
    lines.append("## Verdict: COMPLIANT")
    lines.append("")
    lines.append("All gateways pass compliance checks. Fleet score: {}%.".format(fleet_score))
else:
    lines.append("## Verdict: NON-COMPLIANT")
    lines.append("")
    failing = [gw for gw in gateways if summary[gw]["fail"] > 0]
    lines.append("{} of {} gateway(s) have compliance failures. Fleet score: {}%.".format(
        len(failing), len(gateways), fleet_score))
lines.append("")

with open(report_file, "w") as f:
    f.write("\n".join(lines))
print("Report written to {}".format(report_file))
print("Fleet score: {}% ({} pass, {} fail, {} warn)".format(fleet_score, tp, tf, tw))
sys.exit(1 if tf > 0 else 0)
PYEOF

echo ""
echo "Done. Open $REPORT to review."
```

### Default Rules (`audit-rules.json`)

```json
{
  "min_version": "8.3.2",
  "required_modules": [
    "com.inductiveautomation.opcua",
    "com.inductiveautomation.perspective"
  ],
  "max_error_count": 25
}
```

Customize the rules file for your environment. For example, to require the Alarm Notification module and tighten the error threshold:

```json
{
  "min_version": "8.3.3",
  "required_modules": [
    "com.inductiveautomation.opcua",
    "com.inductiveautomation.perspective",
    "com.inductiveautomation.alarm-notification"
  ],
  "max_error_count": 10
}
```

## Usage

```bash
# 1. Make scripts executable
chmod +x audit-collect.sh audit-report.sh

# 2. Collect data from all configured gateways
./audit-collect.sh

# 3. Generate the compliance report
./audit-report.sh

# Use a custom output directory
./audit-collect.sh /opt/audits
./audit-report.sh /opt/audits

# Re-run the report with stricter rules (no re-collection needed)
./audit-report.sh audit-data strict-rules.json

# Schedule weekly audits (Mondays at 6 AM)
# crontab -e
# 0 6 * * 1 cd /opt/scripts && ./audit-collect.sh && ./audit-report.sh >> /var/log/compliance.log 2>&1
```

## Sample Output

### Terminal (audit-collect.sh)

```
=== Compliance Audit — Data Collection ===
Output:    audit-data/20260210-060000
Timestamp: 20260210-060000

Gateways found:
  - production
  - staging
  - edge-site-1

[production] Collecting data...
[production] Done (8 files)
[staging] Collecting data...
[staging] Done (8 files)
[edge-site-1] Collecting data...
[edge-site-1] Done (8 files)

Collection complete: audit-data/20260210-060000
Run audit-report.sh to generate the compliance report.
```

### Generated Report (compliance-report-20260210-060000.md)

```markdown
# Compliance Audit Report

**Generated:** 2026-02-10 06:00:05
**Data collected:** audit-data/20260210-060000
**Rules:** audit-rules.json
**Gateways audited:** 3

## Compliance Rules

| Rule | Value |
|------|-------|
| Minimum version | 8.3.2 |
| Required modules | com.inductiveautomation.opcua, com.inductiveautomation.perspective |
| Max ERROR log entries | 25 |

## Gateway: production — PASS (100%)

| Check | Status | Detail |
|-------|--------|--------|
| Gateway Version | **PASS** | v8.3.3 (minimum: 8.3.2) |
| Required Modules | **PASS** | All 2 required modules present |
| Device Connections | **PASS** | All 12 devices connected |
| Error Log Count | **PASS** | 3 errors (threshold: 25) |
| Tag Provider Health | **PASS** | All 2 providers healthy |
| Project Inventory | **PASS** | 4 project(s), all enabled |
| Deployment Modes | **PASS** | 3 mode(s): development, staging, production |

## Gateway: staging — WARN (86%)

| Check | Status | Detail |
|-------|--------|--------|
| Gateway Version | **PASS** | v8.3.3 (minimum: 8.3.2) |
| Required Modules | **PASS** | All 2 required modules present |
| Device Connections | **PASS** | All 8 devices connected |
| Error Log Count | **PASS** | 12 errors (threshold: 25) |
| Tag Provider Health | **PASS** | All 1 providers healthy |
| Project Inventory | **WARN** | 1 of 4 disabled: OldDashboard |
| Deployment Modes | **PASS** | 2 mode(s): development, staging |

## Gateway: edge-site-1 — FAIL (57%)

| Check | Status | Detail |
|-------|--------|--------|
| Gateway Version | **FAIL** | v8.3.1 below minimum 8.3.2 |
| Required Modules | **FAIL** | Missing: com.inductiveautomation.perspective |
| Device Connections | **FAIL** | 2 of 6 not connected: PLC-Line3, PLC-Line4 |
| Error Log Count | **PASS** | 8 errors (threshold: 25) |
| Tag Provider Health | **PASS** | All 1 providers healthy |
| Project Inventory | **PASS** | 2 project(s), all enabled |
| Deployment Modes | **WARN** | No deployment modes configured |

## Fleet Summary

| Gateway | Pass | Fail | Warn | Score |
|---------|------|------|------|-------|
| production | 7 | 0 | 0 | 100% |
| staging | 6 | 0 | 1 | 86% |
| edge-site-1 | 4 | 3 | 0 | 57% |
| **Fleet Total** | **17** | **3** | **1** | **81%** |

## Verdict: NON-COMPLIANT

1 of 3 gateway(s) have compliance failures. Fleet score: 81%.
```

## Native Alternatives

**EAM (Enterprise Administration Module)** provides centralized monitoring of managed agents from a controller gateway, including version and module status. However, EAM does not produce exportable audit reports, does not support custom compliance rules, and requires all gateways to be enrolled as EAM agents.

The CLI approach is preferable when:
- You need a persistent, version-controllable audit artifact (Markdown, not just a UI screen)
- You need custom compliance rules that vary by customer or regulation
- You manage gateways not enrolled in EAM (standalone or multi-tenant)
- You need to re-run reports with different rules against the same data snapshot
- You want cron-scheduled audits with automated alerting on non-compliance

## Time Saved

**Manual:** 10-15 minutes per gateway to log in, check each item, take notes. For a 10-gateway fleet, that's 2-3 hours per audit cycle.
**Automated:** Full fleet collection in under 5 minutes, report generation in seconds. Rules changes take effect instantly without re-collecting.
