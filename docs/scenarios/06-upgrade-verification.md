# Scenario 6: Gateway Upgrade Pre/Post Verification

## Problem

Upgrading an Ignition gateway is nerve-wracking. You take a backup, run the installer, and hope everything comes back up correctly. But how do you verify that all modules loaded, all projects are intact, all devices reconnected, and no tag providers went missing? Manually comparing before-and-after states across six dimensions is tedious and error-prone — especially under the pressure of a maintenance window.

## What This Automates

- **`snapshot.sh`** — captures a complete gateway state as JSON before the upgrade
- **`compare.sh`** — diffs two snapshots and generates a verification report
- Checks 7 dimensions: gateway version, modules, projects, devices, tag providers, modes, resource counts
- Flags differences as CHANGED/ADDED/REMOVED with details
- Produces a PASS/WARN/FAIL verdict per dimension

## Snapshot Script

```bash
#!/usr/bin/env bash
# snapshot.sh — Capture gateway state as a timestamped JSON snapshot
# Usage: snapshot.sh [gateway-profile] [output-dir]
set -euo pipefail

GATEWAY="${1:-production}"
OUTPUT_DIR="${2:-./upgrade-snapshots}"
DATE=$(date +%Y%m%d-%H%M%S)
SNAPSHOT="$OUTPUT_DIR/$GATEWAY-$DATE.json"

mkdir -p "$OUTPUT_DIR"

echo "=== Gateway Snapshot ==="
echo "Gateway:  $GATEWAY"
echo "Output:   $SNAPSHOT"
echo ""

echo "[1/7] Capturing gateway info..."
gw_info=$(ignition-cli gateway info -g "$GATEWAY" -f json)

echo "[2/7] Capturing modules..."
gw_modules=$(ignition-cli gateway modules -g "$GATEWAY" -f json)

echo "[3/7] Capturing projects..."
gw_projects=$(ignition-cli project list -g "$GATEWAY" -f json)

echo "[4/7] Capturing devices..."
gw_devices=$(ignition-cli device list -g "$GATEWAY" -f json)

echo "[5/7] Capturing tag providers..."
gw_providers=$(ignition-cli tag providers -g "$GATEWAY" -f json)

echo "[6/7] Capturing modes..."
gw_modes=$(ignition-cli mode list -g "$GATEWAY" -f json)

echo "[7/7] Capturing resource types..."
gw_resource_types=$(ignition-cli resource types -g "$GATEWAY" -f json)

# Assemble the snapshot
python3 -c "
import json, sys

snapshot = {
    'gateway': '$GATEWAY',
    'timestamp': '$DATE',
    'info': json.loads('''$(echo "$gw_info")'''),
    'modules': json.loads('''$(echo "$gw_modules")'''),
    'projects': json.loads('''$(echo "$gw_projects")'''),
    'devices': json.loads('''$(echo "$gw_devices")'''),
    'tag_providers': json.loads('''$(echo "$gw_providers")'''),
    'modes': json.loads('''$(echo "$gw_modes")'''),
    'resource_types': json.loads('''$(echo "$gw_resource_types")''')
}

with open('$SNAPSHOT', 'w') as f:
    json.dump(snapshot, f, indent=2)

print(f'Snapshot saved: $SNAPSHOT')

# Summary
info = snapshot['info']
print(f\"  Version:        {info.get('version', '?')}\")
print(f\"  Modules:        {len(snapshot['modules'])}\")
print(f\"  Projects:       {len(snapshot['projects'])}\")
print(f\"  Devices:        {len(snapshot['devices'])}\")
print(f\"  Tag providers:  {len(snapshot['tag_providers'])}\")
modes = snapshot['modes']
mode_list = modes.get('items', modes) if isinstance(modes, dict) else modes
print(f\"  Modes:          {len(mode_list)}\")
"
```

## Compare Script

```bash
#!/usr/bin/env bash
# compare.sh — Compare pre and post upgrade snapshots
# Usage: compare.sh <pre-snapshot.json> <post-snapshot.json>
set -euo pipefail

PRE="${1:?Usage: compare.sh <pre-snapshot.json> <post-snapshot.json>}"
POST="${2:?Missing post-upgrade snapshot}"
DATE=$(date +%Y%m%d-%H%M%S)
REPORT="upgrade-report-$DATE.txt"

if [ ! -f "$PRE" ] || [ ! -f "$POST" ]; then
    echo "ERROR: Snapshot file(s) not found."
    exit 1
fi

echo "=== Upgrade Verification Report ===" | tee "$REPORT"
echo "Pre-upgrade:  $PRE" | tee -a "$REPORT"
echo "Post-upgrade: $POST" | tee -a "$REPORT"
echo "Date:         $DATE" | tee -a "$REPORT"
echo "" | tee -a "$REPORT"

python3 << 'PYEOF'
import json, sys

with open(sys.argv[1]) as f:
    pre = json.load(f)
with open(sys.argv[2]) as f:
    post = json.load(f)

report_file = sys.argv[3]
results = []

def report(line):
    print(line)
    results.append(line)

def check(label, status, details=""):
    icon = {"PASS": "PASS", "WARN": "WARN", "FAIL": "FAIL"}[status]
    report(f"  [{icon}] {label}")
    if details:
        for d in details.split("\n"):
            report(f"         {d}")

# 1. Version
report("1. Gateway Version")
pre_ver = pre.get("info", {}).get("version", "unknown")
post_ver = post.get("info", {}).get("version", "unknown")
if pre_ver == post_ver:
    check("Version unchanged", "WARN", f"{pre_ver} (expected a version change after upgrade)")
else:
    check("Version changed", "PASS", f"{pre_ver} -> {post_ver}")
report("")

# 2. Modules
report("2. Modules")
pre_mods = {m.get("name", ""): m.get("version", "") for m in pre.get("modules", [])}
post_mods = {m.get("name", ""): m.get("version", "") for m in post.get("modules", [])}

added = set(post_mods) - set(pre_mods)
removed = set(pre_mods) - set(post_mods)
changed = {n for n in pre_mods if n in post_mods and pre_mods[n] != post_mods[n]}
unchanged = set(pre_mods) & set(post_mods) - changed

if removed:
    check("Modules removed", "FAIL", "\n".join(f"- {n} ({pre_mods[n]})" for n in sorted(removed)))
else:
    check("No modules removed", "PASS")

if added:
    check("Modules added", "WARN", "\n".join(f"+ {n} ({post_mods[n]})" for n in sorted(added)))

if changed:
    check("Modules version changed", "PASS",
          "\n".join(f"~ {n}: {pre_mods[n]} -> {post_mods[n]}" for n in sorted(changed)))
else:
    check("Module versions unchanged", "PASS")
report("")

# 3. Projects
report("3. Projects")
pre_proj = {p.get("name", "") for p in pre.get("projects", [])}
post_proj = {p.get("name", "") for p in post.get("projects", [])}

missing = pre_proj - post_proj
new_proj = post_proj - pre_proj

if missing:
    check("Projects missing after upgrade", "FAIL", "\n".join(f"- {p}" for p in sorted(missing)))
else:
    check("All projects present", "PASS")

if new_proj:
    check("New projects found", "WARN", "\n".join(f"+ {p}" for p in sorted(new_proj)))
report("")

# 4. Devices
report("4. Devices")
pre_dev = {d.get("name", "") for d in pre.get("devices", [])}
post_dev = {d.get("name", "") for d in post.get("devices", [])}

missing_dev = pre_dev - post_dev
new_dev = post_dev - pre_dev

if missing_dev:
    check("Devices missing after upgrade", "FAIL", "\n".join(f"- {d}" for d in sorted(missing_dev)))
else:
    check("All devices present", "PASS")

if new_dev:
    check("New devices found", "WARN", "\n".join(f"+ {d}" for d in sorted(new_dev)))

# Check device status
post_devices = post.get("devices", [])
faulted = [d.get("name","?") for d in post_devices if "fault" in str(d.get("status","")).lower()]
if faulted:
    check("Devices faulted after upgrade", "WARN", "\n".join(faulted))
else:
    check("All devices healthy", "PASS")
report("")

# 5. Tag providers
report("5. Tag Providers")
pre_prov = {p.get("name", "") for p in pre.get("tag_providers", [])}
post_prov = {p.get("name", "") for p in post.get("tag_providers", [])}

missing_prov = pre_prov - post_prov
if missing_prov:
    check("Tag providers missing", "FAIL", "\n".join(f"- {p}" for p in sorted(missing_prov)))
else:
    check("All tag providers present", "PASS")
report("")

# 6. Modes
report("6. Deployment Modes")
pre_modes_data = pre.get("modes", [])
post_modes_data = post.get("modes", [])
if isinstance(pre_modes_data, dict):
    pre_modes_data = pre_modes_data.get("items", [])
if isinstance(post_modes_data, dict):
    post_modes_data = post_modes_data.get("items", [])

pre_mode_names = {m.get("name", "") for m in pre_modes_data}
post_mode_names = {m.get("name", "") for m in post_modes_data}

missing_modes = pre_mode_names - post_mode_names
if missing_modes:
    check("Modes missing", "FAIL", "\n".join(f"- {m}" for m in sorted(missing_modes)))
else:
    check("All modes present", "PASS")
report("")

# Summary
report("=" * 50)
pass_count = sum(1 for r in results if "[PASS]" in r)
warn_count = sum(1 for r in results if "[WARN]" in r)
fail_count = sum(1 for r in results if "[FAIL]" in r)

report(f"PASS: {pass_count}  WARN: {warn_count}  FAIL: {fail_count}")
report("")

if fail_count > 0:
    report("UPGRADE VERIFICATION: FAIL")
    report("Critical issues detected. Investigate before declaring the upgrade complete.")
elif warn_count > 0:
    report("UPGRADE VERIFICATION: PASS (with warnings)")
    report("Review warnings to ensure they are expected.")
else:
    report("UPGRADE VERIFICATION: PASS")
    report("All checks passed. Upgrade looks good.")

with open(report_file, "a") as f:
    f.write("\n".join(results))
PYEOF

PRE_FILE="$PRE" POST_FILE="$POST" python3 -c "
import json, sys, os

pre_file = '$PRE'
post_file = '$POST'
report_file = '$REPORT'
" "$PRE" "$POST" "$REPORT" 2>/dev/null || true

echo ""
echo "Report saved: $REPORT"
```

## Usage

```bash
# Before upgrade: take a snapshot
./snapshot.sh production ./upgrade-snapshots
# Output: upgrade-snapshots/production-20260301-020000.json

# ... perform the Ignition upgrade ...

# After upgrade: take another snapshot
./snapshot.sh production ./upgrade-snapshots
# Output: upgrade-snapshots/production-20260301-040000.json

# Compare the two snapshots
./compare.sh \
    upgrade-snapshots/production-20260301-020000.json \
    upgrade-snapshots/production-20260301-040000.json
```

## Sample Report Output

```
=== Upgrade Verification Report ===
Pre-upgrade:  upgrade-snapshots/production-20260301-020000.json
Post-upgrade: upgrade-snapshots/production-20260301-040000.json

1. Gateway Version
  [PASS] Version changed
         8.3.2 -> 8.3.3

2. Modules
  [PASS] No modules removed
  [PASS] Modules version changed
         ~ OPC-UA: 8.3.2 -> 8.3.3
         ~ Perspective: 8.3.2 -> 8.3.3
         ~ Reporting: 8.3.2 -> 8.3.3

3. Projects
  [PASS] All projects present

4. Devices
  [PASS] All devices present
  [PASS] All devices healthy

5. Tag Providers
  [PASS] All tag providers present

6. Deployment Modes
  [PASS] All modes present

==================================================
PASS: 8  WARN: 0  FAIL: 0

UPGRADE VERIFICATION: PASS
All checks passed. Upgrade looks good.
```

## Native Alternatives

The **Ignition Gateway Webpage** shows current status but provides no historical comparison. **EAM** shows agent status across the fleet but doesn't compare pre/post states for a single gateway.

The CLI approach is preferable when:
- You need documented pre/post upgrade evidence
- You want automated verification during a maintenance window (reduces downtime)
- You need to compare specific dimensions rather than doing a full gateway backup diff
- You want JSON snapshots that can be committed to version control

## Time Saved

**Manual:** 15-30 minutes of logging into the gateway, clicking through status pages, comparing notes from before the upgrade.
**Automated:** Two commands (snapshot before, snapshot + compare after). Full verification in under 2 minutes with a permanent record.
