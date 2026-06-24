# DetectionPipeline

## Overview

Owns the background frame loop: reads frames from `CameraCapture`, runs inference via `InferenceEngine`, converts BGR frames to JPEG bytes, and publishes `PipelineResult` objects to a bounded in-memory queue consumed by the Stream API. Reacts to runtime camera configuration changes without restarting the server. Does not perform frame annotation, manage the `InferenceEngine` lifecycle, or serve HTTP responses.

## Boundaries

- Owns: the background frame loop thread and its lifecycle (`start` / `stop`).
- Owns: construction and destruction of `CameraCapture` instances in response to config changes.
- Owns: JPEG encoding of BGR frames via `cv2.imencode`.
- Owns: publishing `PipelineResult` to the bounded queue (including drop-oldest overflow policy).
- Owns: FPS throttle enforcement (max 30 FPS output rate).
- Owns: thread-safe storage and access of the current `RuntimeConfig`.
- Delegates: frame acquisition and retry logic to `CameraCapture`.
- Delegates: inference execution to `InferenceEngine`.
- Delegates: queue consumption and HTTP delivery to the Stream API.
- Delegates: `InferenceEngine` teardown to the Web Server (after `stop()` returns).
- Must not: draw bounding boxes or annotate frames.
- Must not: call `InferenceEngine.teardown()`.
- Must not: serve HTTP responses or interact with SSE directly.
- Must not: instruct the source camera to change its capture rate.
- Must not: create more than one background thread.

## Dependencies

| Collaborator | Role | Allowed Interaction | Forbidden Interaction |
|---|---|---|---|
| `model_lens.camera_capture.LocalCamera` | Camera backend | Construct via `LocalCamera(config)`, call `read()`, `close()` | Must not call any other methods |
| `model_lens.camera_capture.RtspCamera` | Camera backend | Construct via `RtspCamera(config)`, call `read()`, `close()` | Must not call any other methods |
| `model_lens.inference_engine.InferenceEngine` | Inference dependency | Call `detect(frame, target_labels)` | Must not call `teardown()` |
| `model_lens.entities.RuntimeConfig` | Configuration state | Read `camera` and `target_labels` fields | Must not mutate |
| `model_lens.entities.LocalCameraConfig` | Type dispatch | `isinstance` check for camera construction | — |
| `model_lens.entities.RtspCameraConfig` | Type dispatch | `isinstance` check for camera construction | — |
| `model_lens.entities.DetectionResult` | Output field type | Stored in `PipelineResult.detections` | — |
| `model_lens.exceptions.DeviceNotFoundError` | Error signal | Caught during camera construction | — |
| `model_lens.exceptions.OperationError` | Error signal | Caught from `camera.read()` and `engine.detect()` | — |
| `model_lens.exceptions.ParseError` | Error signal | Caught from `engine.detect()` — triggers fatal process shutdown | — |
| `cv2.imencode` | JPEG encoder | Call with `(".jpg", frame_data)` | — |
| `queue.Queue` | Output channel | `full()`, `get_nowait()`, `put_nowait()` | — |
| `threading.Thread` | Background execution | Construct with `target=self._run, daemon=True`; call `start()`, `is_alive()`, `join()` | — |
| `threading.Lock` | Config protection | `acquire` / `release` (via `with`) | — |
| `threading.Event` | Signaling | `set()`, `clear()`, `is_set()`, `wait(timeout=...)` | — |
| `time.monotonic` | Throttle timing | Read current monotonic time | — |
| `os.kill` | Process termination | Call with `(os.getpid(), signal.SIGINT)` on unrecoverable `ParseError` | Must not call for recoverable errors |
| `os.getpid` | Process identity | Read own PID for signal delivery | — |
| `signal.SIGINT` | Shutdown signal | Used as the signal argument to `os.kill` | Must not use `SIGKILL` or `SIGTERM` |

Construction constraint: `DetectionPipeline` is constructed directly via `__init__(engine, initial_config)`. The `InferenceEngine` instance is injected — never constructed internally.

## Behavior

### Entity: `PipelineResult`

1. Implemented as a frozen dataclass (`@dataclass(frozen=True)`).
2. Fields: `jpeg_bytes: bytes`, `timestamp: float`, `source: str`, `detections: list[DetectionResult]`.
3. `jpeg_bytes` is always a complete JPEG buffer produced by `cv2.imencode(".jpg", bgr_frame)`.
4. `timestamp` and `source` are copied directly from the `Frame` produced by `CameraCapture`.
5. Consumed exclusively by the Stream API via the queue.

### Class: `DetectionPipeline`

#### Construction

6. Stores `engine` reference (never replaced).
7. Stores `initial_config` as the current `RuntimeConfig`.
8. Initialises `threading.Lock` to protect the `RuntimeConfig` slot.
9. Initialises `queue.Queue(maxsize=5)` as the result queue.
10. Initialises `threading.Event` (`_stop_event`) for shutdown signaling.
11. Initialises `threading.Event` (`_camera_changed_event`) for config-change signaling.
12. Initialises `_started = False` (double-start guard).
13. Initialises `_last_frame_time = 0.0`.
14. Sets `_camera = None` initially.
15. Creates the `threading.Thread(target=self._run, daemon=True)` — does NOT start it.
16. Attempts to build the initial camera via `_build_camera(initial_config)`:
    - On `DeviceNotFoundError`: logs `ERROR`, `_camera` remains `None`.
    - On success: stores the camera instance.

#### `start()`

17. If `_started` is `True`, raises `RuntimeError("Pipeline is already running")`.
18. Sets `_started = True`.
19. Calls `self._thread.start()` to spawn the background thread.

#### `stop()`

20. Sets `_stop_event`.
21. If the thread is alive, calls `self._thread.join()`.
22. If `_camera` is not `None`, calls `self._camera.close()`.
23. Idempotent: safe to call more than once.
24. Does NOT call `engine.teardown()`.

#### `update_config(new_config)`

25. Acquires the config lock, replaces `_config` with `new_config`, releases the lock.
26. Sets `_camera_changed_event`.
27. Returns immediately — camera recreation happens asynchronously in the frame loop.

#### `get_config()`

28. Acquires the config lock, reads `_config`, releases the lock, returns the reference.

#### `get_queue()`

29. Returns `self._queue` directly.

#### `_build_camera(config)` (internal helper)

30. If `config.camera` is `LocalCameraConfig`: constructs `LocalCamera(config.camera)`.
31. If `config.camera` is `RtspCameraConfig`: constructs `RtspCamera(config.camera)`.
32. If `config.camera` is not a recognised type: returns `None` (implicit fall-through).
33. Catches `DeviceNotFoundError`: logs `ERROR`, returns `None`.
34. Returns the constructed camera instance on success, or `None` on failure.

#### Frame Loop (`_run` / `_run_one_iteration`)

34. `_run()` loops `while not self._stop_event.is_set()`, calling `_run_one_iteration()` each cycle.
35. `_run_one_iteration()` implements the following steps:

**Step 1 — Camera changed event:**
36. If `_camera_changed_event` is set: clear it, close existing camera (if any) via `close()`, set `_camera = None`, read current config under lock, call `_build_camera` to construct a new camera.

**Step 2 — No active camera:**
37. If `_camera` is `None`: call `_camera_changed_event.wait(timeout=1.0)`, then return (avoids busy-wait spin).

**Step 3 — FPS throttle:**
38. Only applies when `_last_frame_time != 0.0` (first frame is never throttled).
39. Computes `remaining = (1.0 / 30) - (time.monotonic() - _last_frame_time)`.
40. If `remaining > 0`: calls `_stop_event.wait(timeout=remaining)` (interruptible).
41. If `_stop_event` is set after wait, returns immediately.

**Step 4 — Frame read:**
42. Calls `self._camera.read()`.
43. On `OperationError`: logs `ERROR`, calls `self._camera.close()`, sets `_camera = None`, returns.

**Step 5 — JPEG encoding:**
44. Calls `cv2.imencode(".jpg", frame.data)`.
45. If `success` is `False`: logs `WARNING`, returns (skip frame).
46. Converts buffer to bytes via `.tobytes()`.

**Step 6 — Inference:**
47. Reads `target_labels` from `_config` under the lock (snapshot; lock released before `detect()`).
48. Calls `self._engine.detect(frame.data, target_labels)`.
49. On `OperationError`: logs `ERROR`, returns (skip frame).
50. On `ParseError`: logs `CRITICAL`, sets `_stop_event`, sends `SIGINT` to own process via `os.kill(os.getpid(), signal.SIGINT)`, then returns. This terminates the frame loop and triggers uvicorn's graceful shutdown path (which invokes the lifespan `finally` block, calling `pipeline.stop()` and `engine.teardown()`).

**Step 7 — Construct `PipelineResult`:**
51. Creates `PipelineResult(jpeg_bytes=jpeg_bytes, timestamp=frame.timestamp, source=frame.source, detections=results)`.

**Step 8 — Publish to queue:**
52. If `self._queue.full()`: calls `self._queue.get_nowait()` (drop oldest), logs `DEBUG`.
53. Calls `self._queue.put_nowait(pipeline_result)`.
54. Updates `_last_frame_time = time.monotonic()`.

## Inputs

### `DetectionPipeline.__init__`

| Field | Type | Constraints | Required? |
|---|---|---|---|
| `engine` | `InferenceEngine` | Fully initialised, shared instance | Yes |
| `initial_config` | `RuntimeConfig` | Valid `RuntimeConfig` instance | Yes |

### `update_config`

| Field | Type | Constraints | Required? |
|---|---|---|---|
| `new_config` | `RuntimeConfig` | Valid `RuntimeConfig` instance | Yes |

## Outputs

### `get_queue()`

| Field | Type | Description |
|---|---|---|
| return | `queue.Queue[PipelineResult]` | The bounded queue that receives pipeline results |

### `get_config()`

| Field | Type | Description |
|---|---|---|
| return | `RuntimeConfig` | Snapshot of the current runtime configuration |

### Exceptions

| Exception | Condition | Raised by |
|---|---|---|
| `RuntimeError` | `start()` called when already started | `start()` |

### Side Effects

| Effect | Condition | Triggered by |
|---|---|---|
| `os.kill(os.getpid(), signal.SIGINT)` | `ParseError` caught from `engine.detect()` | Frame loop step 6 |

## Invariants

- A single `DetectionPipeline` instance is created per server process.
- `start()` must be called exactly once; double-call raises `RuntimeError`.
- The background thread is created as `daemon=True`.
- `_camera` is only mutated by the background thread (after `start()`) or during construction / after `join()` in `stop()`.
- `RuntimeConfig` is accessed only under the config lock (both read and write).
- `InferenceEngine` is never replaced or torn down by the pipeline.
- The result queue has `maxsize=5`.
- The FPS cap is `1.0 / 30` seconds (~33.3 ms) between published frames.
- FPS throttle uses `_stop_event.wait(timeout=...)` — never `time.sleep()` — so shutdown is not blocked.
- `_last_frame_time` is updated only after successful publish (not after skipped frames).
- The first frame after start is never throttled (`_last_frame_time == 0.0` at construction). Camera recreation does NOT reset `_last_frame_time`.
- `stop()` closes the camera only after the thread has exited (via `join()`).
- The `get_nowait()` call for drop-oldest is wrapped in a `try/except queue.Empty` guard for safety.
- On unrecoverable `ParseError`, the pipeline must terminate the entire process — not just the thread. It does so by sending `SIGINT` to its own process, which triggers uvicorn's graceful shutdown.
- `_stop_event` is always set before sending `SIGINT`, so the frame loop exits cleanly even if the signal is handled asynchronously.

## Edge Cases

- Condition: `start()` called twice.
  Expected: `RuntimeError("Pipeline is already running")` raised on second call; no thread spawned.

- Condition: Camera device unavailable at construction.
  Expected: `DeviceNotFoundError` caught, `_camera` set to `None`, pipeline constructed successfully; frame loop waits for config change.

- Condition: Camera fails mid-operation (`OperationError` from `read()`).
  Expected: Camera closed and discarded (`_camera = None`); loop waits for new config.

- Condition: `cv2.imencode` returns failure.
  Expected: `WARNING` logged, frame skipped, loop continues.

- Condition: `engine.detect()` raises `OperationError`.
  Expected: `ERROR` logged, frame skipped, loop continues.

- Condition: `engine.detect()` raises `ParseError`.
  Expected: `CRITICAL` logged, `_stop_event` set, `SIGINT` sent to own process via `os.kill(os.getpid(), signal.SIGINT)`, frame loop exits. Uvicorn's signal handler triggers graceful shutdown (lifespan `finally` block runs `pipeline.stop()` and `engine.teardown()`).

- Condition: Queue is full when publishing.
  Expected: Oldest item discarded via `get_nowait()`, new result enqueued, `DEBUG` logged.

- Condition: `stop()` called while FPS throttle is waiting.
  Expected: `_stop_event.wait()` returns immediately (event set), loop exits promptly.

- Condition: `stop()` called multiple times.
  Expected: Idempotent — second call is a no-op (thread already joined, camera already closed or `None`).

- Condition: `update_config()` called while loop is waiting for camera (step 2).
  Expected: `_camera_changed_event.set()` unblocks the `wait(timeout=1.0)`, next iteration picks up the new config.

- Condition: Source camera delivers frames slower than 30 FPS.
  Expected: Pipeline runs at source rate with no artificial delay (throttle only fires when frames arrive faster than 30 FPS).

## Related

- [CameraCapture](./camera_capture.md): frame source; lifecycle managed by this pipeline.
- [InferenceEngine](./inference_engine.md): inference dependency; lifecycle NOT managed by this pipeline.
- [RuntimeConfig](./entities/runtime_config.md): configuration state swapped atomically via `update_config`.
- [DetectionResult](./entities/detection_result.md): field type within `PipelineResult.detections`.
- [Frame](./entities/frame.md): intermediate entity read from camera and passed to encoder/engine.
- [exceptions](./exceptions.md): `DeviceNotFoundError`, `OperationError`, `ParseError`.
