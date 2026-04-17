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

# Generate the full report via Python (matching project convention: python3 for JSON parsing)
AUDIT_DIR="$AUDIT_DIR" RULES="$RULES" REPORT="$REPORT" python3 << 'PYEOF'
import json, os, sys
from datetime import datetime

audit_dir = os.environ["AUDIT_DIR"]
rules_file = os.environ["RULES"]
report_file = os.environ["REPORT"]

# Load rules
with open(rules_file) as f:
    rules = json.load(f)

min_version = rules.get("min_version", "8.3.0")
required_modules = rules.get("required_modules", [])
max_error_count = rules.get("max_error_count", 25)

# Discover gateway directories
gateways = sorted([
    d for d in os.listdir(audit_dir)
    if os.path.isdir(os.path.join(audit_dir, d))
])

if not gateways:
    print("ERROR: No gateway data directories found.")
    sys.exit(1)


def load_json(gw, filename):
    path = os.path.join(audit_dir, gw, filename)
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def extract_items(data, *keys):
    """Mirror the CLI's extract_items helper: list → as-is, dict → items/fallback keys."""
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


# ── Collect results ──────────────────────────────────────────────────────────
results = {}   # gw -> list of (check_name, status, detail)
summary = {}   # gw -> {pass, fail, warn}

for gw in gateways:
    checks = []

    # 1. Version check
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

    # 2. Required modules
    modules_data = load_json(gw, "modules.json")
    modules = extract_items(modules_data, "modules")
    installed_ids = {m.get("id", "") for m in modules}
    missing = [mid for mid in required_modules if mid not in installed_ids]
    if not missing:
        checks.append(("Required Modules", "PASS",
                        "All {} required modules present".format(len(required_modules))))
    else:
        checks.append(("Required Modules", "FAIL",
                        "Missing: {}".format(", ".join(missing))))

    # 3. Faulted devices
    devices_data = load_json(gw, "devices.json")
    devices = extract_items(devices_data, "resources")
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

    # 4. Error log spike
    logs_data = load_json(gw, "logs.json")
    logs = extract_items(logs_data, "logs")
    error_count = sum(1 for entry in logs if entry.get("level", "") == "ERROR")
    if error_count == 0:
        checks.append(("Error Log Count", "PASS", "No ERROR entries in recent logs"))
    elif error_count <= max_error_count:
        checks.append(("Error Log Count", "PASS",
                        "{} errors (threshold: {})".format(error_count, max_error_count)))
    else:
        checks.append(("Error Log Count", "FAIL",
                        "{} errors exceeds threshold of {}".format(error_count, max_error_count)))

    # 5. Tag provider health
    providers_data = load_json(gw, "providers.json")
    providers = extract_items(providers_data, "resources")
    unhealthy = []
    for p in providers:
        name = p.get("name", "?")
        hc = p.get("healthchecks", {})
        if isinstance(hc, dict):
            for _check_name, check_val in hc.items():
                status = ""
                if isinstance(check_val, dict):
                    status = str(check_val.get("status", ""))
                if status and status.upper() != "GOOD":
                    unhealthy.append(name)
                    break
    if not providers:
        checks.append(("Tag Provider Health", "WARN", "No tag providers found"))
    elif not unhealthy:
        checks.append(("Tag Provider Health", "PASS",
                        "All {} providers healthy".format(len(providers))))
    else:
        checks.append(("Tag Provider Health", "FAIL",
                        "Unhealthy: {}".format(", ".join(unhealthy))))

    # 6. Project inventory
    projects_data = load_json(gw, "projects.json")
    projects = extract_items(projects_data, "projects")
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

    # 7. Mode inventory
    modes_data = load_json(gw, "modes.json")
    modes = extract_items(modes_data)
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


# ── Generate Markdown ────────────────────────────────────────────────────────
lines = []
lines.append("# Compliance Audit Report")
lines.append("")
lines.append("**Generated:** {}".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
lines.append("**Data collected:** {}".format(audit_dir))
lines.append("**Rules:** {}".format(rules_file))
lines.append("**Gateways audited:** {}".format(len(gateways)))
lines.append("")

# Rules summary
lines.append("## Compliance Rules")
lines.append("")
lines.append("| Rule | Value |")
lines.append("|------|-------|")
lines.append("| Minimum version | {} |".format(min_version))
lines.append("| Required modules | {} |".format(", ".join(required_modules) or "(none)"))
lines.append("| Max ERROR log entries | {} |".format(max_error_count))
lines.append("")

# Per-gateway sections
for gw in gateways:
    checks = results[gw]
    s = summary[gw]
    total = s["pass"] + s["fail"] + s["warn"]
    score = round(s["pass"] / total * 100) if total > 0 else 0
    if s["fail"] > 0:
        status_label = "FAIL"
    elif s["warn"] > 0:
        status_label = "WARN"
    else:
        status_label = "PASS"

    lines.append("## Gateway: {} — {} ({}%)".format(gw, status_label, score))
    lines.append("")
    lines.append("| Check | Status | Detail |")
    lines.append("|-------|--------|--------|")
    for check_name, status, detail in checks:
        lines.append("| {} | **{}** | {} |".format(check_name, status, detail))
    lines.append("")

# Summary table
lines.append("## Fleet Summary")
lines.append("")
lines.append("| Gateway | Pass | Fail | Warn | Score |")
lines.append("|---------|------|------|------|-------|")
total_pass = 0
total_fail = 0
total_warn = 0
for gw in gateways:
    s = summary[gw]
    total = s["pass"] + s["fail"] + s["warn"]
    score = round(s["pass"] / total * 100) if total > 0 else 0
    lines.append("| {} | {} | {} | {} | {}% |".format(gw, s["pass"], s["fail"], s["warn"], score))
    total_pass += s["pass"]
    total_fail += s["fail"]
    total_warn += s["warn"]

grand_total = total_pass + total_fail + total_warn
fleet_score = round(total_pass / grand_total * 100) if grand_total > 0 else 0
lines.append("| **Fleet Total** | **{}** | **{}** | **{}** | **{}%** |".format(
    total_pass, total_fail, total_warn, fleet_score))
lines.append("")

# Overall verdict
if total_fail == 0:
    lines.append("## Verdict: COMPLIANT")
    lines.append("")
    lines.append("All gateways pass compliance checks. Fleet score: {}%.".format(fleet_score))
else:
    lines.append("## Verdict: NON-COMPLIANT")
    lines.append("")
    failing_gws = [gw for gw in gateways if summary[gw]["fail"] > 0]
    lines.append("{} of {} gateway(s) have compliance failures. Fleet score: {}%.".format(
        len(failing_gws), len(gateways), fleet_score))
lines.append("")

report_text = "\n".join(lines)
with open(report_file, "w") as f:
    f.write(report_text)

print("Report written to {}".format(report_file))
print("Fleet score: {}% ({} pass, {} fail, {} warn)".format(
    fleet_score, total_pass, total_fail, total_warn))
sys.exit(1 if total_fail > 0 else 0)
PYEOF

echo ""
echo "Done. Open $REPORT to review."
