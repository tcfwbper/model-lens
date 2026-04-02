# StreamViewer Component Specification

## Core Principle

`StreamViewer.tsx` renders the live detection stream on a `<canvas>` element. It receives
SSE frame data from the `useStream` hook and draws the JPEG image with bounding box overlays
for target detections.

---

## Module Location

`src/ui/components/StreamViewer.tsx`

---

## Props

| Prop | Type | Description |
|---|---|---|
| `sseActive` | `boolean` | Whether the SSE connection should be active. |
| `onToggleSSE` | `(active: boolean) => void` | Callback to start or stop the SSE connection. |
| `confidenceThreshold` | `number \| null` | Read-only value to display below the canvas. `null` if initial load failed. |

---

## SSE Connection

StreamViewer uses the `useStream` hook internally. The hook is activated/deactivated based
on `props.sseActive`.

---

## Canvas Rendering

### Image Layer

Each SSE frame contains `jpeg_b64`. The component:

1. Decodes the base64 string into a `Blob` or data URL.
2. Draws it onto the canvas via `drawImage()`, scaling to fill the canvas dimensions.

The canvas maintains a **16:9 aspect ratio** by default. The actual canvas pixel dimensions
adapt to the container width (responsive).

### Bounding Box Overlay

For each detection in the frame's `detections` array where `is_target` is `true`:

1. Convert normalised coordinates `[x1, y1, x2, y2]` to canvas pixel coordinates:
   - `px_x1 = x1 * canvas.width`
   - `px_y1 = y1 * canvas.height`
   - `px_x2 = x2 * canvas.width`
   - `px_y2 = y2 * canvas.height`

2. Draw a rectangle outline (stroke, no fill) in the `Primary` theme colour (`#5B8CB8`),
   line width 2px.

3. Draw a text label above the top-left corner of the box:
   - Format: **"{label} {confidence:.0%}"** (e.g. `"cat 87%"`)
   - White text on a small filled background rectangle using the `Primary` colour for
     readability.

Detections where `is_target` is `false` are **not rendered** at all.

### Idle State

When `sseActive` is `false` or no frame has been received yet, the canvas displays a
centred text: **"Stream inactive"** in `Text Secondary` colour on a `Surface` background.

---

## Confidence Threshold Display

Below the canvas, right-aligned, small text in `Text Secondary` colour:

```
Confidence Threshold: 0.50
```

If `confidenceThreshold` is `null`, this line is not rendered.

---

## SSE Control Buttons

Two buttons are rendered in the right column, below the TargetLabels component (not inside
StreamViewer itself — see App.md layout). However, the toggle callback is passed through
StreamViewer's props for the parent to wire up. The buttons are rendered by the **parent
(App)** directly:

- **"Start Stream"** button — calls `onToggleSSE(true)`. Disabled when `sseActive` is `true`.
  Uses `Primary` colour.
- **"Stop Stream"** button — calls `onToggleSSE(false)`. Disabled when `sseActive` is `false`.
  Uses a neutral/grey style.

Default state on page load: `sseActive` is `false` (stream not started).
