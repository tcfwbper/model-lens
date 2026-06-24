# Stream Router

## Overview

Pushes a continuous Server-Sent Events (SSE) stream of annotated frames and detection results to connected clients. Owns the SSE event formatting, keepalive emission, idle timeout, and connection lifecycle. Does not perform inference or frame processing.

## Boundaries

- Owns: SSE event generator logic (frame serialization, keepalive, idle timeout).
- Owns: base64 encoding of JPEG bytes for the SSE payload.
- Owns: JSON serialization of detection results into the SSE payload.
- Owns: per-connection idle timeout (30 seconds) and keepalive emission (30-second interval).
- Delegates: frame production and queuing to `DetectionPipeline`.
- Delegates: pipeline access to `request.app.state.pipeline` via `cast()`.
- Must not: perform inference, camera management, or frame annotation.
- Must not: use `Depends(get_pipeline)` — accesses `app.state.pipeline` directly via `cast()`.

## Dependencies

| Collaborator | Role | Allowed Interaction | Forbidden Interaction |
|---|---|---|---|
| `model_lens.detection_pipeline.DetectionPipeline` | Frame source | `get_queue()` | Must not call `start()`, `stop()`, `update_config()` |
| `queue.Queue` | Frame delivery | `.get(timeout=_QUEUE_TIMEOUT)` | — |
| `base64` | Encoding | `b64encode(jpeg_bytes).decode()` | — |
| `json` | Serialization | `json.dumps(payload)` | — |
| `time.monotonic` | Timing | Read current monotonic time (aliased to `_monotonic`) | — |
| `fastapi.APIRouter` | Router framework | Define route | — |
| `fastapi.responses.StreamingResponse` | SSE delivery | Construct with generator and `media_type="text/event-stream"` | — |

Construction constraint: module-level `router = APIRouter()` instance. Module aliases `time.monotonic` as `_monotonic` to allow test patching without affecting the global `time` module.

## Behavior

### Module-Level Constants

1. `_IDLE_TIMEOUT = 30.0` — seconds of continuous idle before closing the connection.
2. `_KEEPALIVE_INTERVAL = 30.0` — seconds between keepalive comments during idle.
3. `_QUEUE_TIMEOUT = 1.0` — seconds to wait on `queue.get()` before checking idle/keepalive.
4. `_monotonic = time.monotonic` — module-level alias for testability.

### `_event_generator(pipeline) -> Generator[bytes, None, None]`

5. Initializes `last_frame_time = _monotonic()` and `last_keepalive_time = last_frame_time`.
6. Enters a `while True` loop (wrapped in `try/finally` for cleanup extensibility).
7. Attempts `pipeline.get_queue().get(timeout=_QUEUE_TIMEOUT)`:
   - On `queue.Empty`: sets `result = None`.
   - On success: stores the `PipelineResult`.
8. Reads `now = _monotonic()`.
9. If `result` is not `None`:
   - Updates `last_frame_time = now`.
   - Serializes each detection in `result.detections` to a dict with keys: `label`, `confidence`, `bounding_box` (as list), `is_target`.
   - Constructs the JSON payload: `{"jpeg_b64": base64(result.jpeg_bytes), "timestamp": result.timestamp, "source": result.source, "detections": [...]}`.
   - Yields `f"data: {payload}\n\n".encode()`.
10. If `result` is `None`:
    - If `now - last_keepalive_time >= _KEEPALIVE_INTERVAL`: updates `last_keepalive_time = now`, yields `b": keepalive\n\n"`.
    - If `now - last_frame_time >= _IDLE_TIMEOUT`: returns (closes generator, ending the SSE stream).

### `GET /stream`

11. Retrieves `DetectionPipeline` from `request.app.state.pipeline` via `cast()`.
12. Returns `StreamingResponse(_event_generator(pipeline), media_type="text/event-stream")`.

## Inputs

None (no request parameters or body).

## Outputs

### SSE event format (per frame)

```
data: {"jpeg_b64":"<base64>","timestamp":1748000400.123,"source":"local:0","detections":[...]}\n\n
```

| Field | Type | Description |
|---|---|---|
| `jpeg_b64` | `str` | Base64-encoded JPEG bytes (standard alphabet, no line breaks) |
| `timestamp` | `float` | POSIX timestamp from `PipelineResult.timestamp` |
| `source` | `str` | Camera source identifier from `PipelineResult.source` |
| `detections` | `array` | Array of detection objects; may be empty |

Each detection object:

| Field | Type | Description |
|---|---|---|
| `label` | `str` | Human-readable label string |
| `confidence` | `float` | Confidence score in `(0.0, 1.0]` |
| `bounding_box` | `[x1, y1, x2, y2]` | Normalised floats as a JSON array |
| `is_target` | `bool` | `true` if label is in `target_labels` |

### Keepalive comment

```
: keepalive\n\n
```

SSE comment line — ignored by SSE clients.

## Invariants

- The idle timeout is tracked per-connection. Each `GET /stream` request spawns an independent generator with its own timers.
- Keepalive comments do NOT reset the idle timeout (`last_frame_time` is only updated on successful frame delivery).
- The generator uses a synchronous `Generator[bytes, None, None]` — not an async generator.
- `_monotonic` alias ensures tests can patch the time source for this module without breaking anyio/asyncio.
- The `bounding_box` field is serialized as a Python list (converted from tuple via `list(d.bounding_box)`).
- The queue `.get()` timeout is 1.0 second — shorter than both the keepalive interval and idle timeout.
- The generator's `finally` block is intentionally empty (placeholder for future cleanup).

## Edge Cases

- Condition: No frames available for 30 consecutive seconds.
  Expected: One keepalive comment is sent at 30 seconds, then the connection is closed (idle timeout also reached at 30 seconds — the keepalive is sent first in the same iteration, then the timeout check closes the stream).

- Condition: Client disconnects mid-stream.
  Expected: The generator is garbage-collected by the ASGI framework; no error logged.

- Condition: Queue is always empty (pipeline has no camera).
  Expected: Keepalive sent every 30 seconds; connection closed after 30 seconds of idle.

- Condition: Frames arrive faster than the queue timeout.
  Expected: Each frame is serialized and sent immediately; keepalive logic never triggers.

## Related

- [App](../app.md): mounts this router.
- [DetectionPipeline](../detection_pipeline.md): produces `PipelineResult` objects consumed via `get_queue()`.
- [DetectionResult](../entities/detection_result.md): fields serialized into the SSE payload.
