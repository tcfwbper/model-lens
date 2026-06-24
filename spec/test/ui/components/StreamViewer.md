# Test Specification: `StreamViewer.test.tsx`

## Source File Under Test
`src/ui/src/components/StreamViewer.tsx`

## Test File
`src/ui/src/components/StreamViewer.test.tsx`

---

## `StreamViewer`

### Happy Path — Rendering

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `shows_placeholder_when_inactive` | `unit` | Shows "Stream inactive" placeholder when sseActive is false. | Mock `useStream` to return `{ frame: null }`. | Render `<StreamViewer sseActive={false} onToggleSSE={vi.fn()} confidenceThreshold={0.5} />` | Text "Stream inactive" is visible. Canvas is hidden (`display: none`). |
| `shows_placeholder_when_active_but_no_frame` | `unit` | Shows placeholder when active but no frame received yet. | Mock `useStream` to return `{ frame: null }`. | Render `<StreamViewer sseActive={true} onToggleSSE={vi.fn()} confidenceThreshold={0.5} />` | Text "Stream inactive" is visible. Canvas is hidden. |
| `shows_canvas_when_frame_available` | `unit` | Canvas is visible when frame data is available. | Mock `useStream` to return `{ frame: { jpeg_b64: "abc", timestamp: 1, source: "cam", detections: [] } }`. Mock `Image` to fire `onload` synchronously. | Render `<StreamViewer sseActive={true} onToggleSSE={vi.fn()} confidenceThreshold={0.5} />` | Canvas element is visible (not `display: none`). Placeholder is hidden. |
| `displays_confidence_threshold` | `unit` | Shows confidence threshold text when value is provided. | Mock `useStream` to return `{ frame: null }`. | Render `<StreamViewer sseActive={false} onToggleSSE={vi.fn()} confidenceThreshold={0.75} />` | Text "Confidence Threshold: 0.75" is visible. |
| `hides_confidence_threshold_when_null` | `unit` | No threshold text rendered when confidenceThreshold is null. | Mock `useStream` to return `{ frame: null }`. | Render `<StreamViewer sseActive={false} onToggleSSE={vi.fn()} confidenceThreshold={null} />` | No text containing "Confidence Threshold" is in the document. |

### Happy Path — Frame Drawing

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `draws_image_on_canvas` | `unit` | Draws decoded JPEG image on canvas when frame arrives. | Mock `useStream` to return a frame with `jpeg_b64: "validbase64"` and empty detections. Mock `Image` to fire `onload`. Spy on canvas 2D context methods. | Render with `sseActive={true}`. | `clearRect` called on canvas context. `drawImage` called with the image object. |
| `draws_bounding_boxes_for_target_detections` | `unit` | Draws stroke rectangles for detections where is_target is true. | Mock `useStream` to return frame with `detections: [{ label: "cat", confidence: 0.87, bounding_box: [0.1, 0.2, 0.5, 0.6], is_target: true }]`. Mock `Image` onload. Spy on context. | Render with `sseActive={true}`. | `strokeRect` called with pixel coordinates approximately (80, 90, 320, 180) — use `toBeCloseTo` or `expect.closeTo` for each argument to tolerate floating-point imprecision. `fillText` called with string containing "cat 87%". |
| `skips_non_target_detections` | `unit` | Does not draw bounding boxes for detections where is_target is false. | Mock `useStream` to return frame with `detections: [{ label: "dog", confidence: 0.9, bounding_box: [0.1, 0.1, 0.5, 0.5], is_target: false }]`. Mock `Image` onload. Spy on context. | Render with `sseActive={true}`. | `strokeRect` not called. No label text drawn. |
| `prevents_double_drawing` | `unit` | Does not draw twice when both img.complete and onload fire. | Mock `useStream` to return a valid frame. Mock `Image` with `complete=true` immediately and also fire `onload`. Spy on context. | Render with `sseActive={true}`. | `drawImage` called exactly once. |

### Null / Empty Input

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `no_draw_when_canvas_ref_null` | `unit` | Early return when canvas ref is null (unmounted). | Mock `useStream` to return a valid frame. Mock `useRef` to return `{ current: null }` for canvas. | Render then immediately unmount before effect runs. | No canvas context methods are called. No error thrown. |
| `empty_detections_draws_image_only` | `unit` | Frame with empty detections array draws image without boxes. | Mock `useStream` to return frame with `detections: []`. Mock `Image` onload. Spy on context. | Render with `sseActive={true}`. | `drawImage` called. `strokeRect` not called. |

### Mock / Dependency Interaction

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `calls_use_stream_with_sse_active` | `unit` | Passes sseActive prop to useStream hook. | Mock `useStream`. | Render `<StreamViewer sseActive={true} onToggleSSE={vi.fn()} confidenceThreshold={0.5} />` | `useStream` called with `true`. |
| `does_not_invoke_on_toggle_sse` | `unit` | onToggleSSE prop is not invoked internally. | Mock `useStream` to return `{ frame: null }`. | Render with `sseActive={true}`, `onToggleSSE={vi.fn()}`. Interact with component. | `onToggleSSE` is never called. |

### Boundary Values — Canvas Dimensions

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `canvas_has_fixed_logical_dimensions` | `unit` | Canvas element has width=800 and height=450 attributes. | Mock `useStream` to return a valid frame. Mock `Image` onload. | Render with `sseActive={true}`. | Canvas element has `width` attribute `800` and `height` attribute `450`. |
