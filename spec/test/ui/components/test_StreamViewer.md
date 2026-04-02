# Test Specification: `test/ui/components/test_StreamViewer.md`

## Source File Under Test

`src/ui/components/StreamViewer.tsx`

## Test File

`test/ui/components/StreamViewer.test.tsx`

## Imports Required

```tsx
import { render, screen } from "@testing-library/react";
import StreamViewer from "../../../src/ui/components/StreamViewer";
```

> **Note:** Canvas drawing operations are verified by mocking `HTMLCanvasElement.prototype.getContext`
> and asserting calls on the returned mock 2D context. The `useStream` hook is mocked to provide
> controlled frame data without a real SSE connection.

---

## 1. `StreamViewer`

### 1.1 Happy Path — Idle State

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_stream_viewer_shows_inactive_text_when_sse_off` | `unit` | Canvas area shows "Stream inactive" when `sseActive` is `false` | `sseActive=false` | text `"Stream inactive"` visible |
| `test_stream_viewer_shows_inactive_text_before_first_frame` | `unit` | Canvas area shows "Stream inactive" when `sseActive` is `true` but no frame received yet | `sseActive=true`; mock `useStream` returns `frame: null` | text `"Stream inactive"` visible |

### 1.2 Happy Path — Frame Rendering

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_stream_viewer_draws_image_on_canvas` | `unit` | When a frame is received, the JPEG is drawn on the canvas | mock `useStream` returns frame with `jpeg_b64` | `ctx.drawImage` called on the canvas 2D context |
| `test_stream_viewer_replaces_previous_frame` | `unit` | Each new frame replaces the previous one (canvas is cleared and redrawn) | mock `useStream` returns two frames sequentially | `ctx.drawImage` called for each frame |

### 1.3 Happy Path — Bounding Box Rendering

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_stream_viewer_draws_bbox_for_target_detection` | `unit` | A detection with `is_target: true` is drawn as a rectangle on the canvas | frame with one detection: `{ label: "cat", confidence: 0.87, bounding_box: [0.1, 0.2, 0.4, 0.6], is_target: true }` | `ctx.strokeRect` called with pixel coordinates derived from normalised values |
| `test_stream_viewer_draws_label_text_for_target` | `unit` | Label and confidence text is drawn above the bounding box | same detection as above | `ctx.fillText` called with `"cat 87%"` |
| `test_stream_viewer_skips_non_target_detection` | `unit` | A detection with `is_target: false` is not drawn | frame with one detection: `{ is_target: false, ... }` | `ctx.strokeRect` not called for that detection |
| `test_stream_viewer_draws_multiple_target_bboxes` | `unit` | Multiple target detections each get their own bounding box | frame with 3 detections, 2 with `is_target: true` | `ctx.strokeRect` called 2 times |
| `test_stream_viewer_bbox_coordinates_normalised_to_canvas` | `unit` | Normalised coordinates are correctly scaled to canvas pixel dimensions | canvas `800x450`; bounding_box `[0.1, 0.2, 0.5, 0.8]` | `strokeRect` called with `(80, 90, 320, 270)` (x, y, width, height) |

### 1.4 Happy Path — Confidence Threshold Display

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_stream_viewer_shows_confidence_threshold` | `unit` | `confidence_threshold` value is displayed below the canvas | `confidenceThreshold=0.5` | text `"Confidence Threshold: 0.50"` is present |
| `test_stream_viewer_hides_confidence_when_null` | `unit` | When `confidenceThreshold` is `null`, the line is not rendered | `confidenceThreshold=null` | text containing `"Confidence Threshold"` is not in the document |

### 1.5 Happy Path — SSE Activation

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_stream_viewer_activates_hook_when_sse_on` | `unit` | `useStream` is called with `true` when `sseActive` is `true` | `sseActive=true` | `useStream` called with `active=true` |
| `test_stream_viewer_deactivates_hook_when_sse_off` | `unit` | `useStream` is called with `false` when `sseActive` is `false` | `sseActive=false` | `useStream` called with `active=false` |

---

## Summary Table

| Entity | Test Count (approx.) | unit | e2e | race | Key Concerns |
|---|---|---|---|---|---|
| `StreamViewer` | 14 | 14 | 0 | 0 | idle state, image drawing, bbox rendering, target filtering, coordinate normalisation, confidence display, hook activation |
