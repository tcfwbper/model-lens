# StreamViewer

## Overview

Component that renders the live detection stream on a `<canvas>` element. Receives frame data from the `useStream` hook (activated by the `sseActive` prop) and draws the JPEG image with bounding box overlays for target detections. Also displays the confidence threshold value below the canvas.

## Boundaries

- Owns: canvas rendering (image drawing, bounding box overlays, label text); idle state display; confidence threshold text display; invoking `useStream` hook.
- Delegates: SSE connection lifecycle to `useStream` hook.
- Delegates: SSE toggle control to parent (buttons are in App, not here).
- Must not: manage the `sseActive` state (receives it as prop).
- Must not: call `fetch()` or manage API communication.
- Must not: buffer frames or maintain frame history.

## Dependencies

| Collaborator | Role | Allowed Interaction | Forbidden Interaction |
|---|---|---|---|
| `useStream` hook | Frame data provider | Call `useStream(sseActive)`, read `frame` | Must not manage EventSource directly |
| Canvas 2D API | Rendering | `getContext("2d")`, `drawImage`, `strokeRect`, `fillRect`, `fillText`, `clearRect`, `measureText` | — |
| `Image` (browser API) | JPEG decoding | Construct `Image`, set `src` to data URL, use `onload` | — |

Construction constraint: Functional React component. Uses `useRef`, `useEffect` from React.

## Behavior

### Props

| Prop | Type | Description |
|---|---|---|
| `sseActive` | `boolean` | Whether the SSE stream should be active |
| `onToggleSSE` | `(active: boolean) => void` | Callback for toggling stream (received but not used internally by this component) |
| `confidenceThreshold` | `number \| null` | Confidence threshold to display. `null` if config not loaded. |

### Frame Rendering (via useEffect on `frame`)

1. Gets canvas ref and 2D context.
2. Creates an `Image` object with `src` set to `data:image/jpeg;base64,{frame.jpeg_b64}`.
3. On image load (handles both async `onload` and synchronous `img.complete`):
   - Clears the canvas.
   - Draws the image scaled to fill canvas dimensions (800×450 logical pixels).
   - For each detection in `frame.detections` where `is_target` is `true`:
     a. Converts normalised `[x1, y1, x2, y2]` to pixel coordinates by multiplying by canvas width/height.
     b. Draws a stroke rectangle (no fill) in `#5B8CB8`, line width 2.
     c. Draws a label above the top-left corner: `"{label} {confidence*100 rounded}%"` (e.g. "cat 87%").
     d. Label background: filled rectangle in `#5B8CB8`, sized to text metrics width + 8px padding, height 18px.
     e. Label text: white (`#FFFFFF`), 14px sans-serif font.
4. Uses a `drawn` flag to prevent double-drawing (both `onload` and `img.complete` paths).

### Detections where `is_target` is `false` are not rendered.

### Idle State

When `sseActive` is `false` OR `frame` is `null`:
- Hides the canvas (`display: none`).
- Shows a placeholder div with same aspect ratio (16:9), white background, centered text "Stream inactive" in `#6B7B8D`.

### Confidence Threshold Display

Below the canvas/placeholder area:
- If `confidenceThreshold` is not `null`: renders right-aligned text "Confidence Threshold: {value.toFixed(2)}" in `#6B7B8D`, 0.8rem font.
- If `confidenceThreshold` is `null`: nothing rendered.

### Canvas Dimensions

- Logical size: 800×450 pixels (width × height attribute).
- CSS: `width: 100%`, `aspect-ratio: 16/9` — responsive scaling.

## Inputs

| Field | Type | Constraints | Required |
|---|---|---|---|
| `sseActive` | `boolean` | — | Yes |
| `onToggleSSE` | `(active: boolean) => void` | — | Yes |
| `confidenceThreshold` | `number \| null` | 0–1 range when present | Yes |

## Outputs

JSX element containing the canvas (or placeholder) and optional confidence threshold text.

## Invariants

- Only detections with `is_target === true` produce bounding box overlays.
- Canvas is always cleared before each new frame is drawn (no ghosting from previous frames).
- At most one image decode is rendered per frame update (guarded by `drawn` flag).
- The canvas element always has fixed logical dimensions (800×450) regardless of container size.
- `onToggleSSE` prop is accepted for interface compatibility but not invoked within this component.

## Edge Cases

- Condition: `frame` arrives but canvas ref is null (component not yet mounted or unmounted).
  Expected: Early return; no drawing attempted.

- Condition: `frame.detections` is an empty array.
  Expected: Image is drawn without any bounding boxes.

- Condition: `frame.jpeg_b64` is invalid base64.
  Expected: `Image` `onload` never fires (or fires with broken image). Canvas may show previous frame or remain cleared.

- Condition: `img.complete` is `true` immediately after setting `src` (synchronous environments, cached images).
  Expected: Drawing proceeds via the `img.complete` check after setting `onload`, guarded by `drawn` flag.

## Related

- [useStream](../hooks/useStream.md): provides frame data.
- [App](../App.md): parent that passes props and renders Start/Stop buttons separately.
