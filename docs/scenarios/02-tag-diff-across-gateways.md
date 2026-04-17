# Scenario 2: Tag Configuration Diff Across Gateways

## Problem

After a project promotion or a long development cycle, the tag trees on dev and production have diverged. You need to know: what tags were added? Removed? Changed? Doing this visually by browsing two tag trees is impossible for anything beyond a handful of tags.

## What This Automates

- Exports tag configuration from two gateways
- Normalizes and sorts the JSON for clean comparison
- Produces a structural diff showing added, removed, and modified tags
- Outputs a human-readable summary

## Script

```bash
#!/usr/bin/env bash
# tag-diff.sh — Compare tag configurations between two gateways
set -euo pipefail

SOURCE="${1:?Usage: tag-diff.sh <source-profile> <target-profile> [provider]}"
TARGET="${2:?Missing target gateway profile}"
PROVIDER="${3:-default}"
WORK_DIR=$(mktemp -d)

echo "=== Tag Diff ==="
echo "Source:   $SOURCE"
echo "Target:   $TARGET"
echo "Provider: $PROVIDER"
echo ""

# Export from both gateways
echo "Exporting tags from $SOURCE..."
ignition-cli tag export -g "$SOURCE" --provider "$PROVIDER" -o "$WORK_DIR/source.json"

echo "Exporting tags from $TARGET..."
ignition-cli tag export -g "$TARGET" --provider "$PROVIDER" -o "$WORK_DIR/target.json"

# Normalize JSON for clean diff
python3 << 'PYSCRIPT'
import json
import sys
import os

work_dir = os.environ.get("WORK_DIR", "/tmp")

def flatten_tags(obj, prefix=""):
    """Flatten a tag tree into a dict of path -> tag config."""
    result = {}
    if isinstance(obj, dict):
        name = obj.get("name", "")
        path = f"{prefix}/{name}" if prefix else name
        tag_type = obj.get("tagType", obj.get("nodeType", ""))

        if tag_type and tag_type != "Folder" and tag_type != "Provider":
            # Leaf tag — capture its config
            config = {k: v for k, v in obj.items()
                      if k not in ("name", "tags")}
            result[path] = config

        # Recurse into children
        for child in obj.get("tags", []):
            result.update(flatten_tags(child, path))
    elif isinstance(obj, list):
        for item in obj:
            result.update(flatten_tags(item, prefix))
    return result

for name in ["source", "target"]:
    with open(f"{work_dir}/{name}.json") as f:
        data = json.load(f)
    flat = flatten_tags(data)
    with open(f"{work_dir}/{name}_flat.json", "w") as f:
        json.dump(flat, f, indent=2, sort_keys=True)

# Compare
with open(f"{work_dir}/source_flat.json") as f:
    source_tags = json.load(f)
with open(f"{work_dir}/target_flat.json") as f:
    target_tags = json.load(f)

source_paths = set(source_tags.keys())
target_paths = set(target_tags.keys())

added = sorted(source_paths - target_paths)
removed = sorted(target_paths - source_paths)
common = source_paths & target_paths

modified = []
for path in sorted(common):
    if source_tags[path] != target_tags[path]:
        modified.append(path)

print(f"\n{'='*60}")
print(f"Tag Diff Summary")
print(f"{'='*60}")
print(f"Tags in source only (would be added):   {len(added)}")
print(f"Tags in target only (would be removed):  {len(removed)}")
print(f"Tags with different config (modified):   {len(modified)}")
print(f"Tags identical:                          {len(common) - len(modified)}")

if added:
    print(f"\n--- Added (in {os.environ.get('SOURCE','source')} but not {os.environ.get('TARGET','target')}) ---")
    for p in added[:20]:
        print(f"  + {p}")
    if len(added) > 20:
        print(f"  ... and {len(added) - 20} more")

if removed:
    print(f"\n--- Removed (in {os.environ.get('TARGET','target')} but not {os.environ.get('SOURCE','source')}) ---")
    for p in removed[:20]:
        print(f"  - {p}")
    if len(removed) > 20:
        print(f"  ... and {len(removed) - 20} more")

if modified:
    print(f"\n--- Modified ---")
    for p in modified[:20]:
        print(f"  ~ {p}")
    if len(modified) > 20:
        print(f"  ... and {len(modified) - 20} more")

print()
PYSCRIPT

# Also produce a line-level diff file
diff "$WORK_DIR/source_flat.json" "$WORK_DIR/target_flat.json" > "$WORK_DIR/diff.txt" || true
echo "Detailed diff saved to: $WORK_DIR/diff.txt"

# Cleanup
echo "Working directory: $WORK_DIR"
```

## Usage

```bash
# Compare dev vs production tags
./tag-diff.sh dev production

# Compare specific provider
./tag-diff.sh dev production "HistoricalProvider"
```

## Sample Output

```
=== Tag Diff ===
Source:   dev
Target:   production
Provider: default

Exporting tags from dev...
Exporting tags from production...

============================================================
Tag Diff Summary
============================================================
Tags in source only (would be added):   12
Tags in target only (would be removed):  3
Tags with different config (modified):   7
Tags identical:                          145

--- Added (in dev but not production) ---
  + Pumps/Station3/Flow
  + Pumps/Station3/Pressure
  + Pumps/Station3/Temp
  ... and 9 more

--- Removed (in production but not dev) ---
  - Legacy/OldSensor1
  - Legacy/OldSensor2
  - Legacy/OldSensor3

--- Modified ---
  ~ Pumps/Station1/FlowSetpoint
  ~ Pumps/Station2/AlarmLimits
  ... and 5 more
```

## Native Alternatives

No native equivalent. Ignition provides no way to structurally compare tag trees between gateways.

## Time Saved

**Manual:** Impossible to do accurately by hand for any non-trivial tag tree.
**Automated:** Full structural comparison in seconds, no matter how large the tag tree.
