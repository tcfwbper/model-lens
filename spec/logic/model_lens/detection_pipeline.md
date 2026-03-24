# DetectionPipeline Specification for ModelLens

## Core Principle

`DetectionPipeline` is the background component that owns the frame loop: it reads frames from
`CameraCapture`, runs inference via `InferenceEngine`, converts the raw BGR frame to JPEG bytes,
and publishes `PipelineResult` objects to a bounded in-memory queue consumed by the Stream API.
It reacts to runtime camera configuration changes without restarting the server, and its lifecycle
is synchronised with the FastAPI application lifecycle.

---

## Entities Owned by This Module

### `PipelineResult`

A single published output produced by one successful frame iteration.

| Field | Type | Description |
|---|---|---|
| `jpeg_bytes` | `bytes` | JPEG-encoded RGB image, converted from the original BGR frame before inference |
| `timestamp` | `float` | POSIX timestamp (seconds since 1970-01-01T00:00:00 UTC) copied from `Frame.timestamp` |
| `source` | `str` | Camera source identifier copied from `Frame.source` |
| `detections` | `list[DetectionResult]` | Filtered, label-resolved detections from `InferenceEngine.detect()`, ordered by descending confidence |

#### Rules

- Implemented as a **frozen dataclass** (`@dataclass(frozen=True)`).
- `jpeg_bytes` is always a complete, valid JPEG buffer. Encoding is performed by the pipeline
  using `cv2.imencode(".jpg", rgb_frame)` before the result is published.
- `PipelineResult` is consumed exclusively by the Stream API. No other component holds a
  reference to it.
- `timestamp` and `source` are copied directly from the `Frame` produced by `CameraCapture`;
  they are never recomputed by the pipeline.

---

## Class: `DetectionPipeline`

### Responsibility

- Own the frame loop in a background `threading.Thread`.
- Hold the active `CameraCapture` instance and recreate it when the camera configuration changes.
- Hold a reference to the shared `InferenceEngine` instance (never recreated at runtime).
- Maintain the current `RuntimeConfig` in a thread-safe slot; expose a setter for the Config API.
- Publish `PipelineResult` objects to a bounded `queue.Queue`; drop the oldest item when the
  queue is full.
- Enforce a maximum output rate of 30 FPS; drop source frames that arrive faster than this cap.
- Handle camera errors gracefully: clear the `CameraCapture` instance and wait for a new camera
  configuration from the Config API.
- Shut down gracefully in the correct order when the application exits.

### Constructor

```python
def __init__(
    self,
    engine: InferenceEngine,
    initial_config: RuntimeConfig,
) -> None:
    ...
```

#### Parameters

| Parameter | Type | Description |
|---|---|---|
| `engine` | `InferenceEngine` | The shared inference engine instance, created once at server startup and never replaced |
| `initial_config` | `RuntimeConfig` | The initial runtime configuration seeded from `AppConfig` at startup |

#### Behaviour

1. Stores `engine` and sets the current `RuntimeConfig` to `initial_config`.
2. Constructs the initial `CameraCapture` instance from `initial_config.camera`.
   - If construction raises `DeviceNotFoundError`, logs the error, sets the internal camera
     state to `None`, and continues — the pipeline will wait for a new camera config before
     starting the frame loop.
3. Initialises the result queue: `queue.Queue(maxsize=5)`.
4. Initialises a `threading.Lock` to protect the `RuntimeConfig` slot.
5. Initialises a `threading.Event` (`_stop_event`) used to signal the background thread to exit.
6. Initialises a `threading.Event` (`_camera_changed_event`) used to signal that a new camera
   configuration has been set by the Config API.
7. Does **not** start the background thread; `start()` must be called explicitly.

#### Raises

No exceptions are raised from the constructor. Camera construction failures are handled
internally (see point 2 above).

---

### Public Interface

#### `start() -> None`

Starts the background `threading.Thread` that runs the frame loop. Must be called exactly once,
during the FastAPI startup lifecycle hook. Calling `start()` more than once raises `RuntimeError`.

#### `stop() -> None`

Signals the background thread to exit and blocks until it terminates. Called during the FastAPI
shutdown lifecycle hook. The shutdown sequence is:

1. Set `_stop_event`.
2. Join the background thread (wait for it to exit the frame loop).
3. Close the active `CameraCapture` instance (if any) via `close()`.
4. The `InferenceEngine` is **not** closed by the pipeline; the caller (Web Server) is
   responsible for any engine teardown after `stop()` returns.

`stop()` is idempotent: calling it more than once is safe.

#### `update_config(new_config: RuntimeConfig) -> None`

Called by the Config API to apply a new `RuntimeConfig`. Thread-safe.

1. Acquires the `RuntimeConfig` lock.
2. Replaces the stored `RuntimeConfig` reference with `new_config`.
3. Releases the lock.
4. Sets `_camera_changed_event` to signal the frame loop that the camera configuration may have
   changed and a new `CameraCapture` should be constructed.

This method returns immediately; the camera recreation happens asynchronously inside the frame
loop on the next iteration.

#### `get_queue() -> queue.Queue[PipelineResult]`

Returns the result queue. Called once by the Stream API at startup to obtain the queue reference.
The Stream API consumes `PipelineResult` objects from this queue.

---

### Frame Loop

The background thread runs the following loop until `_stop_event` is set:

```
loop:
    ① Check _stop_event → exit if set
    ② Check _camera_changed_event → recreate CameraCapture if set
    ③ If no active CameraCapture → wait for _camera_changed_event, then go to ①
    ④ FPS throttle check → drop frame if within minimum inter-frame interval
    ⑤ frame = camera.read()
    ⑥ Convert BGR → RGB (copy; do not modify Frame.data)
    ⑦ jpeg_bytes = cv2.imencode(".jpg", rgb_frame)
    ⑧ results = engine.detect(frame.data, runtime_config.target_labels)
    ⑨ Construct PipelineResult
    ⑩ Publish to queue (drop oldest if full)
```

#### Step-by-step Rules

**① Stop check**
- Checked at the top of every iteration before any blocking call.

**② Camera changed event**
- If `_camera_changed_event` is set, clear it, then:
  1. Close the existing `CameraCapture` instance (if any) via `close()`.
  2. Read the current `RuntimeConfig` under the lock to obtain the new `CameraConfig`.
  3. Attempt to construct a new `CameraCapture` subclass instance from the new `CameraConfig`.
     - `LocalCameraConfig` → `LocalCamera`
     - `RtspCameraConfig` → `RtspCamera`
  4. If construction raises `DeviceNotFoundError`:
     - Log the error at `ERROR` level with the source identifier.
     - Set the internal camera reference to `None`.
     - Continue to step ③ (wait for another config change).
  5. On success, store the new `CameraCapture` instance.

**③ No active camera**
- If the internal camera reference is `None`, the loop calls
  `_camera_changed_event.wait(timeout=1.0)` and then restarts from step ①.
  This avoids a busy-wait spin while the user has not yet supplied a valid camera config.

**④ FPS throttle**
- The pipeline tracks `_last_frame_time` (POSIX timestamp of the last successfully published
  frame).
- Minimum inter-frame interval: `1.0 / 30` seconds (~33.3 ms).
- If `time.monotonic() - _last_frame_time < min_interval`, the pipeline calls
  `time.sleep(remaining)` to pace itself, then continues.
- This cap applies to the **output** rate. If the source delivers frames slower than 30 FPS,
  the pipeline runs at the source rate with no artificial delay.

**⑤ Frame read**
- Calls `camera.read()` (blocking).
- If `OperationError` is raised (all retries exhausted inside `CameraCapture`):
  1. Log the error at `ERROR` level.
  2. Close and discard the `CameraCapture` instance (set internal reference to `None`).
  3. Continue to step ③ (wait for a new camera config from the user).

**⑥ BGR → RGB conversion**
- `rgb_frame = frame.data[:, :, ::-1].copy()`
- The original `frame.data` array is never modified.

**⑦ JPEG encoding**
- `success, buffer = cv2.imencode(".jpg", rgb_frame)`
- If `success` is `False`, log a `WARNING` and skip this frame (continue to next iteration).
- `jpeg_bytes = buffer.tobytes()`

**⑧ Inference**
- Reads `target_labels` from the current `RuntimeConfig` under the lock (snapshot only; lock
  released before calling `detect()`).
- Calls `engine.detect(frame.data, target_labels)`.
- **`OperationError`**: log at `ERROR` level, skip this frame, continue loop.
- **`ParseError`**: log at `CRITICAL` level with full exception detail, then call
  `sys.exit(1)`. The model and label map are permanently mismatched; no future frame will
  succeed.

**⑨ Construct `PipelineResult`**

```python
PipelineResult(
    jpeg_bytes=jpeg_bytes,
    timestamp=frame.timestamp,
    source=frame.source,
    detections=results,
)
```

**⑩ Publish to queue**
- If the queue is full (`queue.Queue.full()` returns `True`):
  1. Discard the oldest item with a non-blocking `queue.Queue.get_nowait()` (ignore the
     discarded value).
  2. Log a `DEBUG` message indicating a frame was dropped due to a slow consumer.
- Put the new `PipelineResult` with `queue.Queue.put_nowait()`.
- Update `_last_frame_time = time.monotonic()`.

---

## Lifecycle

```
FastAPI startup hook
    │
    ▼
DetectionPipeline.__init__(engine, initial_config)
    ├── construct initial CameraCapture (or set to None on DeviceNotFoundError)
    ├── initialise queue, locks, events
    │
    ▼
DetectionPipeline.start()
    └── spawn background threading.Thread → enters frame loop
    │
    ▼
[Frame loop runs continuously]
    │
    ├── Config API calls update_config(new_config)
    │       └── swaps RuntimeConfig, sets _camera_changed_event
    │
    ▼
FastAPI shutdown hook
    │
    ▼
DetectionPipeline.stop()
    ├── sets _stop_event
    ├── joins background thread
    └── closes active CameraCapture (if any)
    │
    ▼
Web Server tears down InferenceEngine (outside pipeline responsibility)
```

---

## Thread Safety Summary

| Shared Resource | Protection Mechanism |
|---|---|
| `RuntimeConfig` reference | `threading.Lock` acquired for read (snapshot) and write (swap) |
| `CameraCapture` instance | Owned exclusively by the background thread; only recreated inside the frame loop; `close()` called from `stop()` only after the thread has exited |
| `InferenceEngine` | Per-instance lock inside `InferenceEngine.detect()` (owned by the engine) |
| `queue.Queue` | Thread-safe by design (`queue.Queue` is internally synchronised) |
| `_stop_event` | `threading.Event` (thread-safe) |
| `_camera_changed_event` | `threading.Event` (thread-safe) |

---

## Error Handling Summary

| Situation | Action |
|---|---|
| `DeviceNotFoundError` at `CameraCapture` construction (init or loop) | Log `ERROR`, set camera to `None`, wait for new config |
| `OperationError` from `camera.read()` (all retries exhausted) | Log `ERROR`, close and discard `CameraCapture`, set to `None`, wait for new config |
| `cv2.imencode` failure | Log `WARNING`, skip frame, continue loop |
| `OperationError` from `engine.detect()` | Log `ERROR`, skip frame, continue loop |
| `ParseError` from `engine.detect()` | Log `CRITICAL`, call `sys.exit(1)` |

All exceptions are subtypes of `ModelLensError` as defined in `spec/errors.md`, except
`sys.exit(1)` which terminates the process.

---

## Constraints and Non-Goals

- The pipeline does **not** draw bounding boxes or annotate frames. Bounding box rendering is
  the responsibility of the frontend, using the normalised coordinates in `DetectionResult`.
- The pipeline does **not** manage the `InferenceEngine` lifecycle. The engine is created before
  the pipeline and torn down after it.
- The pipeline does **not** serve HTTP responses or interact with SSE directly. It only writes
  to the queue; the Stream API reads from it.
- A single `DetectionPipeline` instance is created per server process. Multiple instances are
  not supported.
- `PipelineResult` is consumed exclusively by the Stream API. No other component should hold a
  reference to the queue or its contents.
- The 30 FPS cap applies to the pipeline output rate only. The source camera is never
  instructed to change its capture rate.
