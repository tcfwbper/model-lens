# ADR 0024: JPEG Encoding Directly from BGR frame.data; No Colour Conversion in Pipeline

**Date:** 2026-04-02
**Status:** Accepted

## Context

When a frame is read from `CameraCapture`, `Frame.data` is a BGR `numpy.ndarray` (OpenCV's
native colour order). ADR 0015 originally described an intermediate BGR→RGB conversion step
before JPEG encoding (first via a numpy channel-reversal slice, later updated to `cv2.cvtColor`).
ADR 0009 stated that colour-space conversion was the responsibility of `InferenceEngine`.

The actual implementation encodes JPEG directly from the original BGR `frame.data` using
`cv2.imencode(".jpg", frame.data)` with no intermediate conversion. This ADR records that
decision and supersedes the colour-conversion clauses in ADR 0009 and the conversion step
described in ADR 0015.

## Decision

1. **No BGR→RGB conversion is performed before JPEG encoding.** The pipeline calls
   `cv2.imencode(".jpg", frame.data)` directly on the BGR array returned by `CameraCapture`.
2. **`InferenceEngine.detect()` receives BGR `frame.data` unchanged.** The engine must not
   perform any colour-space conversion internally.
3. **`Frame.data` is never modified** by any consumer. The immutability contract from ADR 0009
   remains in force.

The frame-loop sequence in `DetectionPipeline` is:

1. Read frame (`Frame.data` is BGR).
2. Encode JPEG: `success, buffer = cv2.imencode(".jpg", frame.data)`.
3. Run inference: `engine.detect(frame.data, target_labels)` — engine receives BGR.
4. Publish `PipelineResult(jpeg_bytes=buffer.tobytes(), ...)`.

`Frame.data` is never modified.

## Rationale

- **Simplicity** — encoding directly from `frame.data` eliminates an allocation and a
  `memcpy`-equivalent operation per frame. No intermediate `rgb_frame` array is created.
- **Engine agnosticism** — YOLO and most CV frameworks natively consume BGR. No conversion is
  needed to pass the frame to `detect()`, so no conversion should be introduced solely for
  encoding.
- **Consistent use of cv2** — `cv2.imencode` is already used for encoding and `cv2` is the
  only image-processing dependency; keeping encoding in the pipeline without an extra
  conversion step maintains a uniform, minimal code path.
- **Frame.data immutability** — encoding from `frame.data` directly (read-only access) is
  fully consistent with the immutability contract from ADR 0009; no copy or view is needed.

## Alternatives Considered

- **Convert BGR→RGB before encoding (numpy slice or `cv2.cvtColor`)** — rejected; adds an
  allocation and a `memcpy` per frame without a clear benefit for the MVP use case.
- **Assign colour conversion to the engine** — rejected; the engine concerns itself with
  inference, not with producing browser-ready image artefacts.

## Consequences

- `DetectionPipeline` passes `frame.data` (BGR) to both `cv2.imencode` and `engine.detect()`
  unchanged. No intermediate array is created.
- `InferenceEngine.detect()` must not perform any colour-space conversion internally.
- The immutability contract on `Frame.data` (ADR 0009) is unchanged.
- ADR 0015 step 2 (conversion) is removed; encoding is now a single `cv2.imencode` call.
- ADR 0009's colour-space clause (engine responsibility) is superseded by this ADR.

## Superseded By / Supersedes

- **Supersedes:** colour-space clause in ADR 0009; BGR→RGB conversion step in ADR 0015
