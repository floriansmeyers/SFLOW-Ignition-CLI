# Scenario 1: Tag Configuration Snapshots for Version Control

## Problem

Tag configuration changes happen constantly — new tags added, datatypes changed, scaling modified, folders reorganized. There's no built-in version history for tags. When something breaks ("who changed that tag's scaling factor?"), there's no way to diff or roll back.

## What This Automates

- Exports the full tag tree from each gateway on a schedule
- Commits tag exports to a git repository
- Git diff shows exactly what changed between snapshots
- Easy rollback by importing a previous snapshot
- Tracks changes per provider (default, historical, custom)

## Script

```bash
#!/usr/bin/env bash
# tag-snapshot.sh — Snapshot tag configs into a git repo
# Schedule: 0 */4 * * * /opt/scripts/tag-snapshot.sh (every 4 hours)
set -euo pipefail

REPO_DIR="/opt/tag-snapshots"
GATEWAYS=("production" "staging")
PROVIDERS=("default")
DATE=$(date +%Y-%m-%d_%H%M)

cd "$REPO_DIR"

# Ensure git repo exists
if [ ! -d .git ]; then
    git init
    echo "Tag configuration snapshots" > README.md
    git add README.md && git commit -m "Initial commit"
fi

CHANGES=0

for gw in "${GATEWAYS[@]}"; do
    for provider in "${PROVIDERS[@]}"; do
        DIR="$REPO_DIR/$gw/$provider"
        mkdir -p "$DIR"

        echo "Exporting tags: $gw / $provider"
        if ignition-cli tag export \
            -g "$gw" \
            --provider "$provider" \
            -o "$DIR/tags.json" 2>/dev/null; then

            # Pretty-print for readable diffs
            python3 -c "
import json, sys
with open('$DIR/tags.json') as f:
    data = json.load(f)
with open('$DIR/tags.json', 'w') as f:
    json.dump(data, f, indent=2, sort_keys=True)
"
            echo "  OK"
        else
            echo "  FAILED (gateway unreachable or provider not found)"
        fi
    done
done

# Commit if anything changed
git add -A
if ! git diff --cached --quiet; then
    SUMMARY=$(git diff --cached --stat | tail -1)
    git commit -m "Tag snapshot $DATE

$SUMMARY"
    CHANGES=1
    echo ""
    echo "Changes committed: $SUMMARY"
else
    echo ""
    echo "No tag changes detected."
fi

exit 0
```

## Reviewing Changes

```bash
cd /opt/tag-snapshots

# See recent tag change history
git log --oneline -20

# What changed in the last snapshot?
git diff HEAD~1

# What changed to production tags this week?
git log --since="1 week ago" --oneline -- production/

# Show exact tag changes between two snapshots
git diff abc1234 def5678 -- production/default/tags.json

# Find when a specific tag was modified
git log -p --all -S '"Pumps/Station1/FlowSetpoint"' -- '*/tags.json'
```

## Rollback

```bash
# Restore tags to a previous snapshot
git show HEAD~3:production/default/tags.json > /tmp/restore-tags.json
ignition-cli tag import /tmp/restore-tags.json -g production --collision-policy MergeOverwrite
```

## Native Alternatives

No native equivalent. Ignition has no built-in tag configuration versioning or diffing.

## Time Saved

**Manual:** No one does this manually — it simply doesn't get done. Tag changes are invisible.
**Automated:** Full audit trail of every tag change, searchable, diffable, reversible.
