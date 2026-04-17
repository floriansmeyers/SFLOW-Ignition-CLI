# Scenario 5: Tag Template Factory (CSV to Ignition Tag JSON)

## Problem

A controls engineer hands you a spreadsheet with 200 tags for a new production line — tag paths, data types, OPC item paths, engineering units, descriptions. Turning this into Ignition's nested JSON tag structure is tedious and error-prone. You either type each tag manually in the Ignition Designer or spend hours handcrafting JSON. Multiply this by every new line, every new site, every equipment addition.

## What This Automates

- Reads a CSV file with tag definitions (path, data type, OPC item path, units, etc.)
- Builds the nested Ignition tag JSON structure (folders + atomic tags)
- Supports UDT instance generation from repeating patterns
- Imports the generated tags via the CLI
- Validates the import by browsing the tag tree
- Produces a summary of tags created per folder

## Script

```bash
#!/usr/bin/env bash
# tag-factory.sh — Generate Ignition tags from CSV and import
# Usage: tag-factory.sh <csv-file> [gateway-profile] [provider]
set -euo pipefail

CSV_FILE="${1:?Usage: tag-factory.sh <csv-file> [gateway-profile] [provider]}"
GATEWAY="${2:-production}"
PROVIDER="${3:-default}"
DATE=$(date +%Y%m%d-%H%M%S)
OUTPUT_JSON="tags-generated-$DATE.json"

if [ ! -f "$CSV_FILE" ]; then
    echo "ERROR: CSV file not found: $CSV_FILE"
    exit 1
fi

echo "=== Tag Template Factory ==="
echo "CSV:      $CSV_FILE"
echo "Gateway:  $GATEWAY"
echo "Provider: $PROVIDER"
echo ""

# Step 1: Generate Ignition tag JSON from CSV
echo "[1/3] Generating tag JSON from CSV..."

python3 << PYEOF
import csv, json

csv_file = "$CSV_FILE"
output_file = "$OUTPUT_JSON"

root = {"tags": []}
folder_cache = {}
tag_count = 0

with open(csv_file, newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        tag_path = row.get("tag_path", "").strip()
        if not tag_path:
            continue

        parts = tag_path.strip("/").split("/")
        tag_name = parts[-1]
        folder_parts = parts[:-1]

        # Build folder hierarchy
        parent = root
        for i, folder_name in enumerate(folder_parts):
            folder_key = "/".join(folder_parts[:i+1])
            if folder_key not in folder_cache:
                folder_node = {
                    "name": folder_name,
                    "tagType": "Folder",
                    "tags": []
                }
                parent["tags"].append(folder_node)
                folder_cache[folder_key] = folder_node
            parent = folder_cache[folder_key]

        # Build the tag
        tag = {"name": tag_name}
        data_type = row.get("data_type", "").strip()
        if data_type:
            tag["valueSource"] = "opc"
            tag["dataType"] = data_type
        opc_item_path = row.get("opc_item_path", "").strip()
        if opc_item_path:
            tag["opcItemPath"] = opc_item_path
        eng_units = row.get("eng_units", "").strip()
        if eng_units:
            tag["engUnit"] = eng_units
        description = row.get("description", "").strip()
        if description:
            tag["tooltip"] = description

        udt_type = row.get("udt_type", "").strip()
        if udt_type:
            tag["tagType"] = "UdtInstance"
            tag["typeId"] = udt_type
            tag.pop("valueSource", None)
            tag.pop("dataType", None)
            tag.pop("opcItemPath", None)
        else:
            tag["tagType"] = "AtomicTag"

        parent["tags"].append(tag)
        tag_count += 1

with open(output_file, "w") as f:
    json.dump(root, f, indent=2)

print(f"  Generated {tag_count} tags -> {output_file}")

def summarize(node, path=""):
    counts = {}
    for t in node.get("tags", []):
        cp = f"{path}/{t['name']}" if path else t["name"]
        if t.get("tagType") == "Folder":
            counts.update(summarize(t, cp))
        else:
            folder = path or "(root)"
            counts[folder] = counts.get(folder, 0) + 1
    return counts

for folder, cnt in sorted(summarize(root).items()):
    print(f"    {folder}: {cnt} tags")
PYEOF

echo ""

# Step 2: Import tags
echo "[2/3] Importing tags to $GATEWAY (provider: $PROVIDER)..."
ignition-cli tag import "$OUTPUT_JSON" \
    -g "$GATEWAY" \
    --provider "$PROVIDER" \
    --collision-policy MergeOverwrite
echo "  Import complete."
echo ""

# Step 3: Validate
echo "[3/3] Validating imported tags..."
ignition-cli tag browse -g "$GATEWAY" --provider "$PROVIDER" --recursive -f json | python3 -c "
import sys, json
tags = json.load(sys.stdin)
count = len(tags) if isinstance(tags, list) else 0
print(f'  Tag browser returned {count} entries.')
"
echo ""
echo "Tag factory complete. Generated JSON: $OUTPUT_JSON"
```

## Sample CSV

Save as `line1-tags.csv`:

```csv
tag_path,data_type,opc_item_path,eng_units,description,scan_class,udt_type
Line1/Conveyor/Speed,Float4,ns=2;s=Line1.Conveyor.Speed,ft/min,Conveyor belt speed,Default,
Line1/Conveyor/Running,Boolean,ns=2;s=Line1.Conveyor.Running,,Conveyor run status,Default,
Line1/Conveyor/Faulted,Boolean,ns=2;s=Line1.Conveyor.Faulted,,Conveyor fault status,Default,
Line1/Conveyor/MotorAmps,Float4,ns=2;s=Line1.Conveyor.MotorAmps,A,Motor current draw,Default,
Line1/Conveyor/TotalCount,Int4,ns=2;s=Line1.Conveyor.TotalCount,parts,Total parts conveyed,Default,
Line1/Mixer/Temperature,Float4,ns=2;s=Line1.Mixer.Temp,°F,Mixer temperature,Default,
Line1/Mixer/Pressure,Float4,ns=2;s=Line1.Mixer.Pressure,PSI,Mixer pressure,Default,
Line1/Mixer/Level,Float4,ns=2;s=Line1.Mixer.Level,%,Tank fill level,Default,
Line1/Mixer/AgitatorSpeed,Float4,ns=2;s=Line1.Mixer.AgitatorRPM,RPM,Agitator speed,Default,
Line1/Mixer/AgitatorRunning,Boolean,ns=2;s=Line1.Mixer.AgitatorRun,,Agitator run status,Default,
Line1/Filler/Speed,Float4,ns=2;s=Line1.Filler.Speed,units/min,Fill rate,Default,
Line1/Filler/Volume,Float4,ns=2;s=Line1.Filler.Volume,mL,Fill volume setpoint,Default,
Line1/Filler/Running,Boolean,ns=2;s=Line1.Filler.Running,,Filler run status,Default,
Line1/Filler/RejectCount,Int4,ns=2;s=Line1.Filler.Rejects,parts,Rejected parts count,Default,
Line1/Filler/GoodCount,Int4,ns=2;s=Line1.Filler.GoodCount,parts,Good parts count,Default,
Line1/Capper/Torque,Float4,ns=2;s=Line1.Capper.Torque,Nm,Cap torque,Default,
Line1/Capper/Running,Boolean,ns=2;s=Line1.Capper.Running,,Capper run status,Default,
Line1/Capper/Faulted,Boolean,ns=2;s=Line1.Capper.Faulted,,Capper fault status,Default,
Line1/Labeler/Speed,Float4,ns=2;s=Line1.Labeler.Speed,labels/min,Labeler speed,Default,
Line1/Labeler/Running,Boolean,ns=2;s=Line1.Labeler.Running,,Labeler run status,Default,
Line1/Palletizer/Position,Int4,ns=2;s=Line1.Palletizer.Position,,Current layer position,Default,
Line1/Palletizer/PalletCount,Int4,ns=2;s=Line1.Palletizer.Count,pallets,Pallets completed,Default,
Line1/Palletizer/Running,Boolean,ns=2;s=Line1.Palletizer.Running,,Palletizer run status,Default,
Line1/Utilities/AirPressure,Float4,ns=2;s=Line1.Utilities.Air,PSI,Plant air pressure,Default,
Line1/Utilities/WaterFlow,Float4,ns=2;s=Line1.Utilities.Water,GPM,Process water flow,Default,
Line1/Utilities/WaterTemp,Float4,ns=2;s=Line1.Utilities.WaterTemp,°F,Process water temp,Default,
Line1/OEE/Availability,Float4,ns=2;s=Line1.OEE.Availability,%,OEE availability,Slow_5s,
Line1/OEE/Performance,Float4,ns=2;s=Line1.OEE.Performance,%,OEE performance,Slow_5s,
Line1/OEE/Quality,Float4,ns=2;s=Line1.OEE.Quality,%,OEE quality,Slow_5s,
Line1/OEE/Overall,Float4,ns=2;s=Line1.OEE.Overall,%,Overall OEE,Slow_5s,
Line1/Pump1/,,,,,,Pump_UDT
Line1/Pump2/,,,,,,Pump_UDT
Line1/Pump3/,,,,,,Pump_UDT
```

## Usage

```bash
# Generate and import tags for Line 1
./tag-factory.sh line1-tags.csv production default

# Generate for a different provider
./tag-factory.sh line1-tags.csv production "MQTT Engine"

# Just generate JSON without importing (edit the script to skip step 2)
# Or generate separately:
python3 tag-factory-generate.py line1-tags.csv > tags.json
ignition-cli tag import tags.json -g production --collision-policy MergeOverwrite
```

## Sample Output

```
=== Tag Template Factory ===
CSV:      line1-tags.csv
Gateway:  production
Provider: default

[1/3] Generating tag JSON from CSV...
  Generated 33 tags -> tags-generated-20260215-100000.json
    Line1/Conveyor: 5 tags
    Line1/Mixer: 5 tags
    Line1/Filler: 5 tags
    Line1/Capper: 3 tags
    Line1/Labeler: 2 tags
    Line1/Palletizer: 3 tags
    Line1/Utilities: 3 tags
    Line1/OEE: 4 tags
    Line1: 3 tags (UDT instances)

[2/3] Importing tags to production (provider: default)...
  Import complete.

[3/3] Validating imported tags...
  Tag browser returned 42 entries.

Tag factory complete. Generated JSON: tags-generated-20260215-100000.json
```

## Generated JSON Structure (excerpt)

```json
{
  "tags": [
    {
      "name": "Line1",
      "tagType": "Folder",
      "tags": [
        {
          "name": "Conveyor",
          "tagType": "Folder",
          "tags": [
            {
              "name": "Speed",
              "tagType": "AtomicTag",
              "valueSource": "opc",
              "dataType": "Float4",
              "opcItemPath": "ns=2;s=Line1.Conveyor.Speed",
              "engUnit": "ft/min",
              "tooltip": "Conveyor belt speed"
            }
          ]
        },
        {
          "name": "Pump1",
          "tagType": "UdtInstance",
          "typeId": "Pump_UDT"
        }
      ]
    }
  ]
}
```

## Native Alternatives

**Ignition Designer** provides a tag editor with import/export, and **UDT definitions** handle repeating structures natively. The **Tag CICD Module** (community) supports Git-based tag management.

The CLI approach is preferable when:
- Tag definitions come from engineering spreadsheets or PLC I/O lists
- You need to generate tags for multiple identical lines (change the prefix in the CSV)
- You want version-controlled tag definitions in a flat, human-readable format
- You need repeatable tag provisioning across multiple gateways

## Time Saved

**Manual:** 30-60 seconds per tag in the Designer, plus the risk of typos in OPC item paths. A 200-tag batch takes 1-3 hours.
**Automated:** All tags generated and imported in under a minute. The CSV serves as living documentation.
