# Building Perspective Screens Programmatically

Knowledge captured from building live P&ID screens via `ignition-cli perspective` commands.

---

## Key Facts

### Perspective Resources Are Project-Scoped

Perspective views, pages, styles, and session props are **not** in the gateway resource API. They only exist inside project export zips. The CLI uses the export/import cycle transparently.

### URL Format for Page Routes

```
http://<host>:8088/data/perspective/client/<project>/<route>
```

The route portion maps directly to the page config key **without** any `/page/` prefix.

| Page config key | Browser URL |
|---|---|
| `/` | `.../client/MyProject` |
| `/pid` | `.../client/MyProject/pid` |
| `/dashboard/overview` | `.../client/MyProject/dashboard/overview` |

**Wrong:** `.../client/MyProject/page/pid` (this does NOT work)

### Creating a Navigable View (Two Steps Required)

Creating the view alone is not enough. You must also add a page route:

```bash
# Step 1: Create the view
ignition-cli perspective view create MyProject "PID/Overview" --json @view.json

# Step 2: Add a page route pointing to it
# (fetch current config, add route, push back)
ignition-cli perspective page show MyProject -f json > pages.json
# ... add {"/<route>": {"viewPath": "PID/Overview"}} to pages.pages ...
ignition-cli perspective page update MyProject --json @pages.json
```

### Project Scan May Be Needed

After creating views in existing projects, a project scan can help the gateway pick up changes faster:

```bash
ignition-cli gateway scan-projects
```

---

## Component Types

### Native Symbols (Preferred for P&ID)

These render with built-in 3D graphics, animation, and state management:

| Component | Type | Key Props |
|---|---|---|
| Tank/Vessel | `ia.symbol.vessel` | `level` (0-100), `liquidColor`, `state`, `appearance`, `animated`, `label`, `value` |
| Pump | `ia.symbol.pump` | `state` (running/stopped), `orientation`, `animated`, `animationSpeed`, `label`, `value` |
| Valve | `ia.symbol.valve` | `state` (open/closed/partiallyClosed), `animated`, `reverseFlow`, `label` |
| Motor | `ia.symbol.motor` | Similar to pump |
| Sensor | `ia.symbol.sensor` | For instrumentation |

### SVG Component

`ia.display.svg` — **may not be available on all Ignition versions**. On 8.3.3 it returned "ia.display.svg not found". Use native symbols or `ia.display.image` with SVG data URIs instead.

### Common Display Components

| Component | Type | Use |
|---|---|---|
| Label | `ia.display.label` | Text, values, status indicators, pipe segments (via background color) |
| Image | `ia.display.image` | Static graphics, SVG via data URI |
| Markdown | `ia.display.markdown` | Formatted text (does NOT render raw HTML/SVG) |

### Layout Containers

| Container | Type | Use |
|---|---|---|
| Coordinate | `ia.container.coord` | **Best for P&ID** — absolute positioning with x/y/width/height |
| Flex | `ia.container.flex` | Responsive layouts, forms, dashboards |
| Column | `ia.container.column` | Responsive grid-based layouts |
| Breakpoint | `ia.container.breakpoint` | Mobile-responsive designs |

---

## Binding Formats

### Tag Binding

Reads a live tag value. Updates in real-time.

```json
{
  "propConfig": {
    "props.text": {
      "binding": {
        "type": "tag",
        "config": {
          "tagPath": "[default]HMI/tank1",
          "fallbackValue": "--"
        }
      }
    }
  }
}
```

### Expression Binding

For formatting, math, conditionals. Uses Ignition expression language.

```json
{
  "propConfig": {
    "props.text": {
      "binding": {
        "type": "expr",
        "config": {
          "expression": "numberFormat({[default]HMI/tank1}, '#0.0') + '%'"
        }
      }
    }
  }
}
```

### Common Expression Patterns

```
# Number formatting with unit
numberFormat({[default]HMI/tank1Temp}, '#0.0') + '°F'

# Conditional text (pump on/off)
if({[default]HMI/pump1} > 0, 'RUN', 'STOP')

# Conditional color (green when running, red when stopped)
if({[default]HMI/pump1} > 0, '#2e7d32', '#b71c1c')

# Live timestamp
dateFormat(now(1000), 'yyyy-MM-dd HH:mm:ss')

# String concatenation
'Temp: ' + numberFormat({[default]HMI/ambientTemp}, '#0.0') + '°F'
```

### Binding Any Prop

You can bind any prop, not just `text`. Common bindings:

```json
{
  "propConfig": {
    "props.text": { "binding": { ... } },
    "props.style.backgroundColor": { "binding": { ... } },
    "props.state": { "binding": { ... } },
    "props.level": { "binding": { ... } }
  }
}
```

---

## View JSON Structure

### Coordinate Layout (for P&ID screens)

```json
{
  "custom": {},
  "params": {},
  "props": {
    "defaultSize": { "width": 1400, "height": 750 }
  },
  "root": {
    "type": "ia.container.coord",
    "meta": { "name": "root" },
    "props": {
      "style": { "backgroundColor": "#0d1b2a" }
    },
    "children": [
      {
        "type": "ia.symbol.vessel",
        "meta": { "name": "tank1" },
        "position": { "x": 50, "y": 80, "width": 180, "height": 280 },
        "props": { ... },
        "propConfig": { ... }
      }
    ]
  }
}
```

### Position Object (Coordinate Container)

```json
{ "x": 50, "y": 80, "width": 180, "height": 280 }
```

### Vessel Symbol Example

```json
{
  "type": "ia.symbol.vessel",
  "meta": { "name": "tank1" },
  "position": { "x": 50, "y": 80, "width": 180, "height": 280 },
  "props": {
    "appearance": "3d",
    "animated": true,
    "animationSpeed": 50,
    "liquidColor": "#1976d2",
    "liquidWarningColor": "#f44336",
    "state": "running",
    "level": 50,
    "label": { "text": "TANK 1", "location": "bottom", "justify": "center" },
    "value": { "text": "--", "location": "center", "justify": "center" }
  },
  "propConfig": {
    "props.level": {
      "binding": { "type": "expr", "config": {
        "expression": "{[default]HMI/tank1}"
      }}
    },
    "props.value.text": {
      "binding": { "type": "expr", "config": {
        "expression": "numberFormat({[default]HMI/tank1}, '#0.0') + '%'"
      }}
    },
    "props.state": {
      "binding": { "type": "expr", "config": {
        "expression": "if({[default]HMI/pump1} > 0, 'running', 'stopped')"
      }}
    }
  }
}
```

### Pump Symbol Example

```json
{
  "type": "ia.symbol.pump",
  "meta": { "name": "pump1" },
  "position": { "x": 280, "y": 420, "width": 130, "height": 100 },
  "props": {
    "appearance": "3d",
    "animated": true,
    "animationSpeed": 80,
    "orientation": "right",
    "label": { "text": "PUMP 1", "location": "bottom", "justify": "center" },
    "value": { "text": "--", "location": "center", "justify": "center" }
  },
  "propConfig": {
    "props.state": {
      "binding": { "type": "expr", "config": {
        "expression": "if({[default]HMI/pump1} > 0, 'running', 'stopped')"
      }}
    },
    "props.value.text": {
      "binding": { "type": "expr", "config": {
        "expression": "numberFormat({[default]HMI/pump1RPM}, '#0') + ' RPM'"
      }}
    }
  }
}
```

### Valve Symbol Example

```json
{
  "type": "ia.symbol.valve",
  "meta": { "name": "valve1" },
  "position": { "x": 440, "y": 430, "width": 100, "height": 80 },
  "props": {
    "appearance": "3d",
    "animated": true,
    "label": { "text": "VALVE 1", "location": "bottom", "justify": "center" }
  },
  "propConfig": {
    "props.state": {
      "binding": { "type": "expr", "config": {
        "expression": "if({[default]HMI/valve1} > 0, 'open', 'closed')"
      }}
    }
  }
}
```

### Pipe Segments (Using Labels)

Use labels with no text and a background color to simulate pipes:

```json
{
  "type": "ia.display.label",
  "meta": { "name": "pipe-horizontal" },
  "position": { "x": 200, "y": 462, "width": 150, "height": 8 },
  "props": {
    "text": "",
    "style": { "backgroundColor": "#546e7a", "borderRadius": "4px" }
  }
}
```

### Status Badge (Conditional Color Label)

```json
{
  "type": "ia.display.label",
  "meta": { "name": "pump1-status" },
  "position": { "x": 275, "y": 478, "width": 70, "height": 26 },
  "props": {
    "text": "STOP",
    "style": {
      "fontSize": "12px",
      "fontWeight": "bold",
      "textAlign": "center",
      "borderRadius": "13px",
      "paddingTop": "4px",
      "color": "white",
      "backgroundColor": "#b71c1c"
    }
  },
  "propConfig": {
    "props.text": {
      "binding": { "type": "expr", "config": {
        "expression": "if({[default]HMI/pump1} > 0, 'RUN', 'STOP')"
      }}
    },
    "props.style.backgroundColor": {
      "binding": { "type": "expr", "config": {
        "expression": "if({[default]HMI/pump1} > 0, '#2e7d32', '#b71c1c')"
      }}
    }
  }
}
```

---

## Page Config Format

The page config (`config.json`) maps URL routes to views:

```json
{
  "pages": {
    "/": { "viewPath": "Home/Main" },
    "/pid": { "viewPath": "PID/Tank Farm" },
    "/pid/details": { "viewPath": "PID/Details", "title": "Details" }
  }
}
```

Minimal route entry: `{ "viewPath": "Folder/ViewName" }`

Routes with docks (sidebar, header):

```json
{
  "/dashboard": {
    "viewPath": "Dashboard/Main",
    "docks": {
      "left": [{
        "viewPath": "Navigation/Sidebar",
        "size": 250,
        "show": "always",
        "handle": "show",
        "content": "push"
      }]
    }
  }
}
```

---

## Pitfalls and Gotchas

1. **`ia.display.svg` may not exist** on your Ignition version. Use native symbol components instead.
2. **URL format**: `/client/<project>/<route>`, NOT `/client/<project>/page/<route>`.
3. **Two-step for navigable views**: Create the view AND add a page route. View alone won't be URL-accessible.
4. **Vessel level**: Use `props.level` (0-100) for the liquid fill animation, not just `props.value.text`.
5. **Expression syntax**: Tag paths in expressions use `{[provider]path}` with curly braces.
6. **Vessel state**: Controls animation — `"running"` shows bubbling liquid, `"stopped"` is static.
7. **Coordinate container**: Use `ia.container.coord` for P&ID layouts — children need `position: {x, y, width, height}`.
8. **Changes are live immediately**: After `perspective view update`, refreshing the browser shows the new view instantly. Active sessions may need a page refresh.
9. **Complex projects** (like OnlineDemo) have framework wrappers (docks, headers) that may interfere with new page routes. Test on simpler projects first.
10. **Number format locale**: The gateway may use comma as decimal separator (e.g., `0,0` instead of `0.0`) depending on gateway locale settings.

---

## Complete Workflow

```bash
# 1. Browse available tags to find data sources
ignition-cli tag browse --recursive -f json

# 2. Generate view JSON (Python script, AI, template)
python3 generate_pid.py --tags "HMI/tank1,HMI/pump1" > view.json

# 3. Create the view in the project
ignition-cli perspective view create MyProject "PID/Overview" --json @view.json

# 4. Add page route
ignition-cli perspective page show MyProject -f json > /tmp/pages.json
python3 -c "
import json
with open('/tmp/pages.json') as f: cfg = json.load(f)
cfg['pages']['/pid'] = {'viewPath': 'PID/Overview'}
with open('/tmp/pages-updated.json', 'w') as f: json.dump(cfg, f, indent=2)
"
ignition-cli perspective page update MyProject --json @/tmp/pages-updated.json

# 5. Open in browser
open "http://gateway:8088/data/perspective/client/MyProject/pid"

# 6. Iterate — update the view
ignition-cli perspective view update MyProject "PID/Overview" --json @view-v2.json
# Refresh browser to see changes
```
