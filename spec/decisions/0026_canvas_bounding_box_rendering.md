# ADR 0026: Bounding Box Overlays Rendered via HTML Canvas 2D API

**Date:** 2026-04-02
**Status:** Accepted

## Context

The `StreamViewer` component receives SSE frames that each contain a JPEG image
(`jpeg_b64`) and a list of detection results (`detections`), each carrying a normalised
bounding box `[x1, y1, x2, y2]` and a label string.

The component must render the JPEG image as a live video-like stream and draw bounding box
rectangles with label text on top of the image for every detection where `is_target` is
`true`. Several approaches exist for compositing an image layer with a dynamic overlay layer.

## Decision

1. **A single `<canvas>` element is used for both the JPEG image layer and the bounding box
   overlay layer.** There is no separate DOM element for the overlay.

2. **On each incoming SSE frame**, the component:
   1. Decodes `jpeg_b64` into a data URL or `Blob` URL and calls
      `ctx.drawImage(imageElement, 0, 0, canvas.width, canvas.height)`, scaling the image to
      fill the canvas.
   2. Iterates over `detections` where `is_target` is `true` and for each:
      - Converts normalised coordinates to pixel coordinates:
        `px = x * canvas.width`, `py = y * canvas.height`.
      - Draws a stroked rectangle (`ctx.strokeRect`) using the `Primary` theme colour
        (`#5B8CB8`), 2 px line width, no fill.
      - Draws a label string above the top-left corner of the box, formatted as
        `"{label} {confidence:.0%}"` (e.g. `"cat 87%"`), white text on a
        `Primary`-coloured filled background rectangle.

3. **The canvas maintains a 16:9 aspect ratio** and adapts its pixel dimensions to the
   container width (responsive sizing).

4. **Idle state** — when no stream is active and no frame has been received, the canvas
   renders centred text **"Stream inactive"** in `Text Secondary` colour on a `Surface`
   background fill.

## Rationale

- **Single compositing surface** — drawing both the JPEG and the overlay onto one `<canvas>`
  eliminates the need to align a separate overlay element to the image, avoiding pixel-perfect
  positioning issues across different container sizes or aspect ratios.
- **Canvas 2D API expressiveness** — `ctx.strokeRect`, `ctx.fillText`, and `ctx.drawImage`
  provide all required primitives with no external library. Fine-grained control over stroke
  width, font, and background fills is available natively.
- **Performance** — Canvas 2D rasterises directly on the GPU-backed bitmap. There is no DOM
  diffing overhead per detection, which matters because the detection list can change every
  frame (~30 FPS).
- **Responsive scaling** — normalised coordinates (`[0, 1]`) are trivially mapped to canvas
  pixel coordinates regardless of canvas size, so responsive layout requires no additional
  logic beyond reading `canvas.width` and `canvas.height` at render time.
- **No extra dependencies** — SVG or an overlay library (e.g. Konva) would add bundle
  weight and conceptual overhead for a straightforward 2D drawing task.

## Alternatives Considered

- **SVG overlay (`<svg>` positioned absolutely over `<img>`)** — rejected; requires keeping
  the SVG viewport in pixel-perfect sync with the `<img>` element's rendered size, which
  complicates responsive layout. SVG also has per-element DOM overhead for potentially many
  bounding boxes per frame.
- **CSS-positioned `<div>` boxes over `<img>`** — rejected; absolute positioning of divs
  requires translating normalised coordinates to CSS `top`/`left`/`width`/`height` in the
  component render cycle. DOM reconciliation at 30 FPS is more expensive than a canvas
  repaint, and label text placement is harder to control.
- **Two stacked `<canvas>` elements (image canvas + overlay canvas)** — rejected; using two
  canvases provides a separation-of-concerns benefit but doubles the compositing surfaces
  without a clear gain for this use case. A single canvas redraw per frame is simpler and
  sufficient.
- **WebGL** — rejected; significantly higher implementation complexity for a 2D drawing task
  with no performance requirement that 2D Canvas cannot meet.

## Consequences

- `StreamViewer.tsx` owns and manages a single `<canvas>` ref; no `<img>` element is used
  for the stream.
- Every incoming SSE frame triggers a full canvas redraw: `clearRect` (implicit in
  `drawImage` fill), draw image, draw bounding boxes.
- Bounding box rendering consumes normalised coordinates directly; no coordinate transform
  state is stored beyond `canvas.width` and `canvas.height` at draw time.
- Adding new overlay primitives (e.g. segmentation masks, keypoints) in future is
  straightforward: extend the per-frame draw loop with additional Canvas 2D API calls.
