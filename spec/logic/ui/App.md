# App Specification for ModelLens UI

## Core Principle

`App.tsx` is the root React component. It orchestrates layout, owns page-level initialisation
(fetching config and labels on mount), and distributes shared state to child components.

---

## Module Location

`src/ui/App.tsx`

---

## Theme

| Token | Value | Usage |
|---|---|---|
| Primary | `#5B8CB8` | Buttons, active controls, dropdown highlights |
| Primary Hover | `#4A7BA6` | Button hover state |
| Primary Disabled | `#A8C4DC` | Disabled buttons |
| Background | `#F5F6F8` | Page background |
| Surface | `#FFFFFF` | Card / section backgrounds |
| Border | `#D4DAE0` | Section borders, input borders |
| Text Primary | `#2C3E50` | Headings, body text |
| Text Secondary | `#6B7B8D` | Labels, captions, small text |
| Error | `#D9534F` | Error-related accents (used in alert dialogs only) |

All colours follow a desaturated blue palette on a light warm-grey background.

---

## Layout

```
┌──────────────────────────────────────────────────────────┐
│  ModelLens                                    (Header)   │
├──────────────────────────────────────────────────────────┤
│  Camera Config Area                      (full width)    │
│  [source_type ▼] [device_index / rtsp_url] [更新]        │
├────────────────────────────────┬─────────────────────────┤
│                                │  Target Labels Config   │
│   Stream Viewer (2/3)          │  [multi-select ▼]       │
│   (Canvas: JPEG + BBoxes)      │  [更新]                 │
│                                │                         │
│                                │  SSE Controls           │
│                                │  [啟用] [終止]           │
├────────────────────────────────┴─────────────────────────┤
│                          confidence_threshold: 0.50  (右) │
└──────────────────────────────────────────────────────────┘
```

- Header spans full width.
- Camera Config section spans full width, directly below the header.
- Below Camera Config, the page splits into two columns:
  - **Left (~2/3 width):** StreamViewer (Canvas).
  - **Right (~1/3 width):** TargetLabels config, then SSE control buttons beneath it.
- Below the stream area (spanning the left column), `confidence_threshold` is displayed as
  small right-aligned text.

---

## Page Load Behaviour

On mount, App fires two parallel requests:

1. `GET /config` — populates camera config display, `target_labels` selection, and
   `confidence_threshold` display.
2. `GET /config/labels` — populates the full label list for the TargetLabels dropdown.

If either request fails, an `alert()` dialog is shown with the HTTP status code and error
message (or `404` with a "Server unreachable" message for network errors). The page renders
normally with empty/default values in the areas that depend on the failed data.

---

## State Ownership

| State | Owner | Consumers |
|---|---|---|
| `runtimeConfig` | App (from `useConfig`) | CameraConfig, TargetLabels, StreamViewer |
| `validLabels` | App (from `useConfig`) | TargetLabels |
| `sseActive` | App | StreamViewer, SSE control buttons |

App passes down state and callbacks as props; child components do not fetch data independently.

---

## Error Handling

All API errors (from any `PUT` or initial `GET`) are surfaced via the browser's native
`alert()` dialog. The alert message format:

```
Error {status_code}: {error_message}
```

For network failures (server unreachable):

```
Error 404: Server unreachable
```

No inline error banners or toast notifications — `alert()` only.
