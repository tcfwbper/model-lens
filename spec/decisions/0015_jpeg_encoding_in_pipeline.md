# ADR 0015: JPEG Encoding Inside the Detection Pipeline

**Date:** 2026-03-24
**Status:** Accepted

## Context

Each published frame must ultimately reach the browser as a JPEG image inside an SSE stream.
The question is where in the pipeline JPEG encoding should be performed: inside the Detection
Pipeline before queuing, or in the Stream API when serving the SSE response.

A related question is what colour space the JPEG should encode: BGR (OpenCV's native format)
or RGB.

## Decision

JPEG encoding is performed **inside the Detection Pipeline**, directly from the BGR
`frame.data`, and before the result is placed on the queue. No intermediate BGR→RGB
conversion is performed.

The sequence within the frame loop is:

1. Read frame (`Frame.data` is BGR from OpenCV).
2. Encode JPEG: `success, buffer = cv2.imencode(".jpg", frame.data)`.
3. Run inference: `engine.detect(frame.data, target_labels)` — engine receives BGR `frame.data`.
4. Publish `PipelineResult(jpeg_bytes=buffer.tobytes(), ...)`.

`PipelineResult.jpeg_bytes` always contains a complete, valid JPEG buffer encoded from BGR
`frame.data`. The Stream API wraps `jpeg_bytes` in an SSE `multipart/x-mixed-replace` boundary
and sends it verbatim.
The Stream API wraps `jpeg_bytes` in an SSE `multipart/x-mixed-replace` boundary and sends
it verbatim; no encoding or colour-space conversion is needed at the Stream layer.

## Rationale

### Why encode in the pipeline, not the Stream API?

- **Encode once, serve many times** — if multiple SSE clients connect simultaneously in a
  future release, encoding in the pipeline means encoding happens once per frame regardless of
  consumer count. Encoding in the Stream API would require re-encoding for each consumer.
- **Separation of concerns** — the Stream API's responsibility is HTTP/SSE framing and
  transmission; it should not perform CPU-intensive image processing. Keeping encoding in the
  pipeline keeps the Stream API thin.
- **Simpler queue contents** — `PipelineResult.jpeg_bytes` is a plain `bytes` object. Placing
  a `numpy.ndarray` in the queue would require the Stream API to know about OpenCV and perform
  encoding, coupling it to the image processing stack.
- **Deterministic queue memory** — a JPEG-compressed frame is predictably small (50–200 KB
  vs. 3–4 MB uncompressed). Encoding before queuing bounds queue memory at ~1 MB rather than
  ~20 MB.

### Why use `cv2.imencode(".jpg", ...)` specifically?

- **Already a dependency** — OpenCV is already required for `CameraCapture`; no additional
  dependency is needed.
- **In-memory encoding** — `cv2.imencode` returns bytes without writing to disk, which is
  appropriate for a streaming pipeline.
- **Acceptable quality at default settings** — default JPEG quality (~95) provides a good
  size/quality trade-off for live-stream preview purposes.

## Error Handling

If `cv2.imencode` returns `success=False`, the pipeline logs a `WARNING` and **skips the
frame** (continues to the next loop iteration). This is treated as a transient encoding
failure; no retry is attempted because the next frame will be a fresh attempt anyway.

## Constraints

- JPEG quality is not configurable for MVP. `cv2.imencode(".jpg", frame.data)` uses the default
  quality (~95). A future release could expose quality as a config parameter if bandwidth
  becomes a concern.
- The pipeline does **not** draw bounding boxes or annotations on the JPEG. Bounding box
  rendering is performed by the frontend using the `DetectionResult` normalised coordinates
  bundled in `PipelineResult.detections`.

## Alternatives Considered

- **Encode in Stream API** — rejected; re-encodes per consumer, adds image processing
  responsibility to the HTTP layer, and increases queue memory footprint.
- **Store raw numpy arrays in queue** — rejected; ~20× larger queue items and requires
  consumers to handle OpenCV types.
- **Encode as PNG** — rejected; PNG is lossless and significantly larger than JPEG for typical
  camera frames; unnecessary for live-stream preview.
- **Use PIL/Pillow for encoding** — rejected; OpenCV is already a dependency; adding Pillow
  for encoding alone would add weight without benefit.

## Consequences

- `PipelineResult.jpeg_bytes` is always a ready-to-transmit JPEG buffer; the Stream API is
  a thin wrapper around it.
- Queue memory is bounded by compressed (JPEG) frame sizes, not raw array sizes.
- All frame colour-space handling is centralised in the pipeline; the Stream API and frontend
  need not be aware of BGR.

## Superseded By / Supersedes

- **Step 2 updated by:** [ADR 0024](0024_bgr_rgb_conversion_in_pipeline.md) — JPEG is encoded directly from BGR `frame.data` using `cv2.imencode(".jpg", frame.data)`; no intermediate BGR→RGB conversion is performed.
