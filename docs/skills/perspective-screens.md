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

---

## Drawing Container and SVG Shapes

The `ia.container.drawing` and `ia.shapes.*` components provide a native SVG drawing system inside Perspective. Confirmed working on Ignition 8.3.3 (used extensively in OnlineDemo HMI High Performance views and Water treatment app).

### ia.container.drawing

An SVG viewport container. Children are `ia.shapes.*` components rendered as SVG elements.

```json
{
  "type": "ia.container.drawing",
  "meta": { "name": "pump" },
  "position": { "height": 1, "width": 1 },
  "props": {
    "viewBox": "-100 -100 1200 1200",
    "preserveAspectRatio": "none"
  },
  "children": [
    { "type": "ia.shapes.path", "props": { "path": "M0,498 l456,-228 ..." } },
    { "type": "ia.shapes.rect", "props": { "width": 100, "height": 50 } }
  ]
}
```

**Key props:**
- `viewBox` — SVG coordinate system: `"minX minY width height"`
- `preserveAspectRatio` — Usually `"none"` for stretching to fill position

**Styling:** Apply `fill` and `stroke` on the container's `props.style` to set defaults for all children:

```json
"props": {
  "preserveAspectRatio": "none",
  "style": { "fill": "#EBEBEB", "stroke": "#2E2E2E", "strokeWidth": "1px" }
}
```

### ia.shapes.path

Arbitrary SVG paths. The workhorse for custom equipment outlines, complex pipe bends, and any shape not covered by built-in symbols.

```json
{
  "type": "ia.shapes.path",
  "meta": { "name": "valve-body" },
  "props": {
    "path": "M0,498 l456,-228 0,228 -456,-228 0,228z",
    "style": { "fill": "#D5D5D5", "stroke": "#2E2E2E", "strokeWidth": "10px" }
  }
}
```

### ia.shapes.rect

Rectangles — used for tank bodies, pipe segments, backgrounds.

```json
{
  "type": "ia.shapes.rect",
  "meta": { "name": "tank-body" },
  "props": { "x": 5, "y": 5, "width": 90, "height": 90 }
}
```

### ia.shapes.circle

Circles — used for tank caps, flanges, connection points.

```json
{
  "type": "ia.shapes.circle",
  "meta": { "name": "tank-top" },
  "props": { "cx": 50, "cy": 50, "r": 48 }
}
```

### ia.shapes.ellipse, ia.shapes.polygon

```json
{ "type": "ia.shapes.ellipse", "props": { "cx": 50, "cy": 50, "rx": 40, "ry": 25 } }
{ "type": "ia.shapes.polygon", "props": { "points": "0,0 100,0 50,100" } }
```

### ia.shapes.group

Groups child shapes for collective transforms or styling.

### ia.shapes.svg (Element-Based SVG)

An alternative SVG approach that embeds elements directly in a `props.elements` array rather than using child components. Used extensively in the Water treatment app and oil-and-gas demo.

```json
{
  "type": "ia.shapes.svg",
  "meta": { "name": "separationTank" },
  "position": { "height": 0.4583, "width": 0.7538, "x": 0.1396, "y": 0.2131 },
  "props": {
    "elements": [
      {
        "type": "group",
        "name": "Group_TankBody",
        "elements": [
          {
            "type": "path",
            "name": "path",
            "d": "M97.973,56.194c0,0,13.84-1.688,13.84-27.815c0-25.869-13.84-27.929-13.84-27.929H14.415c0,0-13.964,0.902-13.964,27.928c0,25.226,13.964,27.815,13.964,27.815H97.973z",
            "fill": { "paint": "#C0C0C0" }
          },
          {
            "type": "path",
            "name": "path",
            "d": "M14.415,0.451v55.744",
            "fill": { "paint": "none" },
            "stroke": { "paint": "#4C4C4C", "width": "0.25" }
          }
        ]
      }
    ],
    "viewBox": "0 0 112.5 56.758",
    "preserveAspectRatio": "none"
  }
}
```

**Fill/stroke with gradients:**

```json
"fill": {
  "paint": {
    "type": "linear",
    "x1": "0%", "y1": "0%", "x2": "100%", "y2": "0%",
    "stops": [
      { "offset": "0%", "style": { "stopColor": "#ECECEC" } },
      { "offset": "100%", "style": { "stopColor": "#4D4D4D" } }
    ]
  }
}
```

### State-Based Shape Styling

Bind `props.style.classes` to switch colors based on equipment state (from HMI High Performance):

```json
{
  "propConfig": {
    "props.style.classes": {
      "binding": {
        "type": "property",
        "config": { "path": "view.params.state" },
        "transforms": [{
          "type": "map",
          "inputType": "scalar",
          "outputType": "scalar",
          "fallback": "HMI_Off",
          "mappings": [
            { "input": 0, "output": "HMI_Off" },
            { "input": 1, "output": "HMI_On" }
          ]
        }]
      }
    }
  }
}
```

Or bind `props.style.fill` directly for simpler cases:

```json
"propConfig": {
  "props.style.fill": {
    "binding": {
      "type": "property",
      "config": { "path": "session.custom.hmi.pipeColor" }
    }
  }
}
```

---

## Full Component Catalog

All 76 component types found across 487 exported Perspective views, organized by category.

### Containers (7 types)

| Type | Use |
|---|---|
| `ia.container.coord` | Absolute positioning (P&ID layouts). Children have `position: {x, y, width, height}`. Supports `mode: "percent"` for responsive |
| `ia.container.flex` | Flexbox layout (dashboards, forms). Props: `direction`, `wrap`, `justify`, `alignItems` |
| `ia.container.column` | Responsive grid columns |
| `ia.container.breakpt` | Breakpoint-responsive (show different layouts at different screen widths) |
| `ia.container.split` | Resizable split panes |
| `ia.container.tab` | Tabbed interface |
| `ia.container.drawing` | SVG viewport for `ia.shapes.*` children. Props: `viewBox`, `preserveAspectRatio` |

### Display (28 types)

| Type | Use |
|---|---|
| `ia.display.label` | Text, values, status badges, pipe segments (via backgroundColor) |
| `ia.display.icon` | Material Design icons |
| `ia.display.image` | Static images, SVG via data URI |
| `ia.display.markdown` | Formatted text (no raw HTML) |
| `ia.display.view` | Embed another view. Props: `path`, `params` |
| `ia.display.flex-repeater` | Repeat a view for each item in a data array. Props: `path`, `instances` |
| `ia.display.table` | Data table with columns, sorting, filtering |
| `ia.display.sparkline` | Inline mini chart. Props: `data` (array of numbers), `desired.high/low` |
| `ia.display.progress` | Progress bar |
| `ia.display.thermometer` | Temperature display |
| `ia.display.cylindrical-tank` | 3D cylindrical tank graphic |
| `ia.display.led-display` | LED-style numeric readout |
| `ia.display.linear-scale` | Horizontal/vertical scale indicator |
| `ia.display.moving-analog-indicator` | Analog gauge pointer |
| `ia.display.map` | Geographic map (Google Maps) |
| `ia.display.tree` | Hierarchical tree display |
| `ia.display.tag-browse-tree` | Tag browser tree widget |
| `ia.display.accordion` | Collapsible sections |
| `ia.display.carousel` | Image/content carousel |
| `ia.display.dashboard` | Dashboard layout container |
| `ia.display.barcode` | Barcode/QR code renderer |
| `ia.display.iframe` | Embedded iframe |
| `ia.display.audio` | Audio player |
| `ia.display.video-player` | Video player |
| `ia.display.pdf-viewer` | PDF document viewer |
| `ia.display.viewcanvas` | Scrollable/zoomable view canvas |
| `ia.display.alarmstatustable` | Live alarm status table |
| `ia.display.alarmjournaltable` | Historical alarm journal |
| `ia.display.equipmentschedule` | Equipment schedule display |
| `ia.display.svg` | SVG display (**may not work on all versions** — test first) |

### Input (17 types)

| Type | Key Props |
|---|---|
| `ia.input.button` | `text`, action events |
| `ia.input.text-field` | `value`, `placeholder` |
| `ia.input.text-area` | Multi-line text |
| `ia.input.numeric-entry-field` | `value`, `min`, `max` |
| `ia.input.password-field` | Masked input |
| `ia.input.dropdown` | `options`, `value` |
| `ia.input.checkbox` | `selected` |
| `ia.input.radio-group` | `options`, `value` |
| `ia.input.toggle-switch` | `selected`, label |
| `ia.input.slider` | `value`, `min`, `max` |
| `ia.input.multi-state-button` | Multiple states with colors/labels |
| `ia.input.oneshotbutton` | One-shot trigger button |
| `ia.input.date-time-picker` | Calendar popup |
| `ia.input.date-time-input` | Date/time text input |
| `ia.input.fileupload` | File upload control |
| `ia.input.barcodescannerinput` | Barcode scanner (mobile) |
| `ia.input.signature-pad` | Signature capture |

### Charts (7 types)

| Type | Use |
|---|---|
| `ia.chart.timeseries` | Time series line/area chart. Bind `series[N].data` to `tag-history` binding |
| `ia.chart.xy` | XY scatter/line chart |
| `ia.chart.pie` | Pie/donut chart |
| `ia.chart.gauge` | Radial gauge |
| `ia.chart.simple-gauge` | Simplified radial gauge |
| `ia.chart.powerchart` | Advanced power chart with built-in controls |
| `ia.chart.chartrangeselector` | Time range selector companion |

### Shapes (7 types)

| Type | Props |
|---|---|
| `ia.shapes.path` | `path` (SVG d attribute) |
| `ia.shapes.rect` | `x`, `y`, `width`, `height` |
| `ia.shapes.circle` | `cx`, `cy`, `r` |
| `ia.shapes.ellipse` | `cx`, `cy`, `rx`, `ry` |
| `ia.shapes.polygon` | `points` |
| `ia.shapes.group` | Groups child shapes |
| `ia.shapes.svg` | `elements[]` array, `viewBox` |

### Navigation (3 types)

| Type | Use |
|---|---|
| `ia.navigation.link` | Navigation link. Props: `text`, `url`, `target` |
| `ia.navigation.menutree` | Tree-based navigation menu |
| `ia.navigation.horizontalmenu` | Horizontal menu bar |

### Symbols (5 types)

| Type | Use |
|---|---|
| `ia.symbol.vessel` | Tank/vessel with level, liquid animation |
| `ia.symbol.pump` | Pump with rotation animation |
| `ia.symbol.valve` | Valve (open/closed states) |
| `ia.symbol.motor` | Motor symbol |
| `ia.symbol.sensor` | Instrumentation sensor |

### Reporting (1 type)

| Type | Use |
|---|---|
| `ia.reporting.report-viewer` | Embedded report viewer |

---

## Complex Piping Patterns

### Approach 1: Labels (Simple Pipes)

Best for straight horizontal/vertical segments. Fast and simple.

```json
// Horizontal pipe
{ "type": "ia.display.label", "position": { "x": 135, "y": 462, "width": 150, "height": 8 },
  "props": { "text": "", "style": { "backgroundColor": "#546e7a", "borderRadius": "4px" } } }

// Vertical pipe
{ "type": "ia.display.label", "position": { "x": 135, "y": 360, "width": 8, "height": 110 },
  "props": { "text": "", "style": { "backgroundColor": "#546e7a", "borderRadius": "4px" } } }

// Rotated pipe (diagonal) — use position.rotate
{ "type": "ia.display.label", "position": { "height": 0.0239, "width": 0.0443,
  "x": 0.6728, "y": 0.1754, "rotate": { "angle": 90 } },
  "props": { "style": { "backgroundColor": "#C0C0C0" } } }
```

### Approach 2: Drawing Container + Shapes (Complex Routing)

Best for curves, bends, and complex routing. Uses `ia.container.drawing` with `ia.shapes.rect` children for pipe segments, bound to a session color property.

```json
{
  "type": "ia.container.drawing",
  "meta": { "name": "pipe-inlet" },
  "position": { "height": 0.0056, "width": 0.6469, "x": 0.3349, "y": 0.1553 },
  "props": { "preserveAspectRatio": "none" },
  "propConfig": {
    "props.style.fill": {
      "binding": { "type": "property", "config": { "path": "session.custom.hmi.pipeColor" } }
    }
  },
  "children": [
    { "type": "ia.shapes.rect", "props": { "height": 100, "width": 100 } }
  ]
}
```

### Approach 3: SVG Path (Arbitrary Routing)

For curves, bends, and non-orthogonal routing using SVG path commands:

```
Straight:        M x1,y1 L x2,y2
Right-angle:     M x1,y1 L x2,y1 L x2,y2
Smooth bend:     M x1,y1 L x2,y1 Q x2,y1 x2,y2 L x2,y3
Arc:             M x1,y1 A rx,ry rotation large-arc sweep x2,y2
Close path:      ... Z
```

**Flow arrow (small triangle along pipe):**

```json
{
  "type": "ia.shapes.path",
  "props": { "path": "M0,0 L10,5 L0,10 Z", "style": { "fill": "#1976d2" } }
}
```

### Color Conventions

| State | Color | Hex |
|---|---|---|
| Flowing (water) | Blue | `#1976d2` |
| Flowing (process) | Green | `#2e7d32` |
| Stopped / No flow | Gray | `#546e7a` |
| Hot fluid | Red/Orange | `#e65100` |
| Alarm | Red | `#b71c1c` |

**Stroke widths:** Main lines 6-8px, branch lines 4px, instrument connections 2px.

---

## P&ID Image Interpretation Guide

Instructions for the main agent when interpreting P&ID images or natural language descriptions.

### Standard P&ID Symbol Mapping

| P&ID Symbol | Perspective Component | Notes |
|---|---|---|
| Tank / vessel (cylinder) | `ia.symbol.vessel` | Use `level`, `liquidColor` props |
| Centrifugal pump (circle) | `ia.symbol.pump` | `orientation` for flow direction |
| Control valve (bowtie) | `ia.symbol.valve` | `state`: open/closed |
| Motor (circle with M) | `ia.symbol.motor` | Bind state to running/stopped |
| Sensor / transmitter (circle with letters) | `ia.symbol.sensor` or `ia.display.label` | Show value + unit |
| Heat exchanger | `ia.shapes.svg` or `ia.shapes.path` | Custom SVG (see templates below) |
| Filter / strainer | `ia.shapes.svg` | Custom SVG |
| Tower / column | `ia.shapes.path` + `ia.shapes.rect` | Tall rectangle with internals |
| Flow arrow | `ia.shapes.path` | Small triangle: `M0,0 L10,5 L0,10 Z` |
| Pipe line | Label (simple) or `ia.shapes.path` (complex) | See piping patterns above |

### Layout Coordinate Estimation

Standard canvas: **1400 x 750 pixels** (or 1920 x 1080 for full HD).

1. Divide the image into a grid mentally (e.g., 14 columns x 7.5 rows at 100px each)
2. Place major equipment first (tanks, pumps, exchangers), leaving space for labels and pipes
3. Equipment spacing: ~150-250px between major items
4. Labels: offset 10-20px from equipment, height 24-30px
5. Pipes: route horizontally or vertically between equipment ports
6. Title bar at top: y=10, height=40
7. Status area: bottom 60px

### Tag Path Naming Convention

When creating placeholder tags for equipment identified in images:

```
[default]<Area>/<EquipmentType><Number>/<Parameter>

Examples:
[default]SmokeAbatement/Fan1/Speed
[default]SmokeAbatement/Fan1/Running
[default]SmokeAbatement/Scrubber1/Level
[default]SmokeAbatement/Scrubber1/pH
[default]SmokeAbatement/Pump1/Running
[default]SmokeAbatement/Valve1/Open
```

### Handling Unknown Equipment

When the image shows equipment without a built-in `ia.symbol.*`:

1. Check if `ia.shapes.svg` with custom elements can represent it
2. If complex, delegate to the SVG subagent for path generation
3. Place using `ia.container.drawing` with the generated SVG children
4. Fallback: use `ia.display.image` with a data URI for simple static icons

---

## SVG Generation Instructions

Instructions for generating custom SVG paths for equipment not covered by native `ia.symbol.*` components.

### Target Output Format

Generate either:
- **Drawing container children** — `ia.shapes.path` components placed inside `ia.container.drawing`
- **SVG element arrays** — `elements[]` for `ia.shapes.svg`

### Equipment Templates

**Absorption Tower / Column** (tall rectangle with internals):
```json
{
  "type": "ia.container.drawing",
  "props": { "viewBox": "0 0 100 300" },
  "children": [
    { "type": "ia.shapes.rect", "props": { "x": 10, "y": 10, "width": 80, "height": 280 },
      "meta": { "name": "shell" } },
    { "type": "ia.shapes.path", "props": { "path": "M15,80 L85,80 M15,160 L85,160 M15,240 L85,240" },
      "meta": { "name": "trays" } },
    { "type": "ia.shapes.circle", "props": { "cx": 50, "cy": 5, "r": 5 },
      "meta": { "name": "top-cap" } }
  ]
}
```

**Heat Exchanger** (shell-and-tube, two overlapping circles):
```json
{
  "type": "ia.container.drawing",
  "props": { "viewBox": "0 0 200 100" },
  "children": [
    { "type": "ia.shapes.circle", "props": { "cx": 70, "cy": 50, "r": 45 },
      "meta": { "name": "shell" } },
    { "type": "ia.shapes.rect", "props": { "x": 60, "y": 20, "width": 130, "height": 60 },
      "meta": { "name": "tubes" } }
  ]
}
```

**Fan / Blower** (circle with blades):
```json
{
  "type": "ia.container.drawing",
  "props": { "viewBox": "0 0 100 100" },
  "children": [
    { "type": "ia.shapes.circle", "props": { "cx": 50, "cy": 50, "r": 45 },
      "meta": { "name": "housing" } },
    { "type": "ia.shapes.path", "props": {
      "path": "M50,50 L50,10 M50,50 L85,30 M50,50 L85,70 M50,50 L50,90 M50,50 L15,70 M50,50 L15,30" },
      "meta": { "name": "blades" } }
  ]
}
```

### Pipe Routing Algorithm

Use Manhattan routing (orthogonal segments) with optional curved corners:

1. Identify source port (equipment connection point) and target port
2. Route horizontally from source to midpoint X, then vertically to target Y, then horizontally to target
3. For curved corners use quadratic bezier: `Q cx,cy x2,y2` at each turn
4. Maintain minimum 20px clearance from equipment boundaries

**Example: L-shaped pipe with curved corner:**
```
M 200,300 L 400,300 Q 420,300 420,280 L 420,100
```

### Color and Stroke Conventions

- Equipment outlines: `stroke: "#2E2E2E"`, `strokeWidth: "1px"` or `"2px"`
- Equipment fill: `"#EBEBEB"` (light gray) for off, `"#4CAF50"` for running
- Pipe segments: `fill` bound to state (flowing vs stopped)
- Text labels: `"#2E2E2E"` on light backgrounds, `"#FFFFFF"` on dark

---

## Dashboard and Form Templates

Ready-to-use JSON templates for non-P&ID screens.

### Dashboard Template (Gauges + Sparklines + Flex Repeater)

```json
{
  "custom": {},
  "params": {},
  "props": { "defaultSize": { "width": 1400, "height": 750 } },
  "root": {
    "type": "ia.container.flex",
    "meta": { "name": "root" },
    "props": { "direction": "column", "style": { "gap": "10px", "padding": "10px" } },
    "children": [
      {
        "type": "ia.display.label",
        "meta": { "name": "title" },
        "position": { "basis": "40px", "shrink": 0 },
        "props": { "text": "Dashboard", "style": { "fontSize": "24px", "fontWeight": "bold" } }
      },
      {
        "type": "ia.container.flex",
        "meta": { "name": "kpi-row" },
        "position": { "basis": "200px", "shrink": 0 },
        "props": { "direction": "row", "style": { "gap": "10px" } },
        "children": [
          {
            "type": "ia.chart.simple-gauge",
            "meta": { "name": "gauge1" },
            "position": { "grow": 1 },
            "props": { "value": 75 },
            "propConfig": {
              "props.value": {
                "binding": { "type": "tag", "config": { "tagPath": "[default]HMI/tank1" } }
              }
            }
          },
          {
            "type": "ia.display.sparkline",
            "meta": { "name": "sparkline1" },
            "position": { "grow": 1 },
            "props": { "data": [] }
          }
        ]
      },
      {
        "type": "ia.display.table",
        "meta": { "name": "data-table" },
        "position": { "grow": 1 },
        "props": { "data": [] }
      }
    ]
  }
}
```

### Table View Template (Table + Filter Dropdowns)

```json
{
  "custom": {},
  "params": {},
  "props": { "defaultSize": { "width": 1400, "height": 750 } },
  "root": {
    "type": "ia.container.flex",
    "meta": { "name": "root" },
    "props": { "direction": "column", "style": { "gap": "10px", "padding": "10px" } },
    "children": [
      {
        "type": "ia.container.flex",
        "meta": { "name": "filters" },
        "position": { "basis": "50px", "shrink": 0 },
        "props": { "direction": "row", "style": { "gap": "10px", "alignItems": "center" } },
        "children": [
          {
            "type": "ia.input.dropdown",
            "meta": { "name": "filter1" },
            "position": { "basis": "200px" },
            "props": { "options": [{"label": "All", "value": "all"}], "value": "all" }
          },
          {
            "type": "ia.input.date-time-input",
            "meta": { "name": "startDate" },
            "position": { "basis": "200px" }
          }
        ]
      },
      {
        "type": "ia.display.table",
        "meta": { "name": "results" },
        "position": { "grow": 1 }
      }
    ]
  }
}
```

### Form Template (Column + Label/Input Pairs)

```json
{
  "custom": {},
  "params": {},
  "props": { "defaultSize": { "width": 600, "height": 500 } },
  "root": {
    "type": "ia.container.flex",
    "meta": { "name": "root" },
    "props": { "direction": "column", "style": { "gap": "16px", "padding": "20px" } },
    "children": [
      {
        "type": "ia.display.label",
        "meta": { "name": "title" },
        "position": { "shrink": 0 },
        "props": { "text": "Settings", "style": { "fontSize": "20px", "fontWeight": "bold" } }
      },
      {
        "type": "ia.container.flex",
        "meta": { "name": "field1" },
        "position": { "shrink": 0 },
        "props": { "direction": "row", "style": { "gap": "10px", "alignItems": "center" } },
        "children": [
          {
            "type": "ia.display.label",
            "meta": { "name": "label" },
            "position": { "basis": "120px" },
            "props": { "text": "Name:" }
          },
          {
            "type": "ia.input.text-field",
            "meta": { "name": "input" },
            "position": { "grow": 1 },
            "props": { "placeholder": "Enter name" }
          }
        ]
      },
      {
        "type": "ia.container.flex",
        "meta": { "name": "buttons" },
        "position": { "shrink": 0 },
        "props": { "direction": "row", "justify": "end", "style": { "gap": "10px" } },
        "children": [
          { "type": "ia.input.button", "meta": { "name": "cancel" }, "props": { "text": "Cancel" } },
          { "type": "ia.input.button", "meta": { "name": "save" }, "props": { "text": "Save" } }
        ]
      }
    ]
  }
}
```

### Navigation Template (Breakpoint + Embedded Views)

```json
{
  "custom": {},
  "params": {},
  "props": { "defaultSize": { "width": 1400, "height": 750 } },
  "root": {
    "type": "ia.container.breakpt",
    "meta": { "name": "root" },
    "children": [
      {
        "type": "ia.container.flex",
        "meta": { "name": "desktop" },
        "props": { "direction": "row" },
        "children": [
          {
            "type": "ia.navigation.menutree",
            "meta": { "name": "nav" },
            "position": { "basis": "250px", "shrink": 0 }
          },
          {
            "type": "ia.display.view",
            "meta": { "name": "content" },
            "position": { "grow": 1 },
            "props": { "path": "Home/Main", "params": {} }
          }
        ]
      }
    ]
  }
}
```

### Time Series Chart with Tag History Binding

```json
{
  "type": "ia.chart.timeseries",
  "meta": { "name": "history-chart" },
  "position": { "grow": 1 },
  "propConfig": {
    "props.series[0].data": {
      "binding": {
        "type": "tag-history",
        "config": {
          "tags": [
            { "path": "[default]HMI/tank1" },
            { "path": "[default]HMI/tank2" }
          ],
          "dateRange": { "mostRecent": "1", "mostRecentUnits": "HOUR" },
          "returnSize": { "numRows": "100", "type": "FIXED" },
          "aggregate": "MinMax",
          "returnFormat": "Wide",
          "valueFormat": "DATASET",
          "polling": { "enabled": true, "rate": "5" }
        }
      }
    }
  }
}
```
