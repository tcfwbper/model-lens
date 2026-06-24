# CameraCapture

## Overview

Abstracts over local (webcam) and RTSP camera sources, vending `Frame` objects on demand via a blocking `read()` call. Contains the `CameraCapture` abstract base class, a shared `_retry_read` helper function, and two concrete subclasses (`LocalCamera`, `RtspCamera`). Does not perform frame annotation, inference, or colour space conversion.

## Boundaries

- Owns: opening, reading from, retrying, and releasing `cv2.VideoCapture` handles.
- Owns: constructing `Frame` objects from successful reads (including buffer copy and timestamping).
- Owns: retry logic with exponential backoff and jitter on frame read failures.
- Owns: input validation of `rtsp_url` prefix (`RtspCamera` only).
- Delegates: frame annotation and inference to `InferenceEngine`.
- Delegates: colour space conversion (BGR → RGB) to `InferenceEngine`.
- Delegates: lifecycle management (when to create/destroy instances) to Detection Pipeline.
- Must not: perform frame annotation, inference, or format conversion.
- Must not: manage `RuntimeConfig` or react to label/threshold changes.
- Must not: support `rtsps://` (TLS-secured RTSP).
- Must not: support multi-consumer fan-out.

## Dependencies

| Collaborator | Role | Allowed Interaction | Forbidden Interaction |
|---|---|---|---|
| `cv2.VideoCapture` | Camera backend | `__init__(source)`, `.isOpened()`, `.read()`, `.release()` | — |
| `model_lens.entities.Frame` | Output entity | Construct via `Frame(data=..., timestamp=..., source=...)` | Must not modify `data` after construction |
| `model_lens.entities.LocalCameraConfig` | Input config | Read `device_index` field | — |
| `model_lens.entities.RtspCameraConfig` | Input config | Read `rtsp_url` field | — |
| `model_lens.exceptions.DeviceNotFoundError` | Error signaling | Raised when device/URL unreachable at construction | — |
| `model_lens.exceptions.OperationError` | Error signaling | Raised when all retry attempts exhausted in `read()` | — |
| `model_lens.exceptions.ValidationError` | Error signaling | Raised when `rtsp_url` has invalid prefix (`RtspCamera`) | — |
| `threading.Lock` | Concurrency | Per-instance lock for thread safety | — |
| `time.time` | Timestamping | Capture POSIX timestamp after successful read | — |
| `time.sleep` | Retry timing | Wait between retry attempts | — |
| `random.uniform` | Jitter | Add uniform jitter `[0.0, 1.0)` to retry waits | — |

Construction constraint: concrete subclasses are constructed directly via their `__init__`. `CameraCapture` is abstract and must never be instantiated directly.

## Behavior

### Abstract Base Class: `CameraCapture`

1. Declares `read()` and `close()` as abstract methods.
2. Implements `__enter__` returning `self` and `__exit__` calling `self.close()`.
3. Subclasses must not override `__enter__` or `__exit__`.

### Module-Level Helper: `_retry_read`

4. Accepts an open `cv2.VideoCapture` handle, a `reopen_fn` callable, a `source` string, and a `threading.Lock`.
5. Attempts to read a frame up to 3 times total (initial attempt + 2 retries).
6. For each attempt:
   - Acquires `lock`, calls `cap.read()`, releases `lock`.
   - On success (`success=True` and `raw is not None`): captures `time.time()` as timestamp, copies the raw buffer via `.copy()`, returns a `Frame`.
   - On failure: acquires `lock`, calls `cap.release()`, releases `lock`.
7. After a failed attempt, waits `base_wait + random.uniform(0.0, 1.0)` seconds before proceeding.
8. Wait schedule: attempt 1 fails → wait 1s + jitter; attempt 2 fails → wait 2s + jitter; attempt 3 fails → wait 4s + jitter then raise.
9. Between waits (except after the final attempt), acquires `lock`, calls `reopen_fn()` to get a fresh handle, releases `lock`.
10. If all 3 attempts are exhausted, raises `OperationError`.

### Concrete Subclass: `LocalCamera`

11. Constructor accepts `LocalCameraConfig`, sets `source` to `f"local:{config.device_index}"`.
12. Opens `cv2.VideoCapture(config.device_index)` immediately.
13. Raises `DeviceNotFoundError` if `cap.isOpened()` returns `False` — no retry at construction.
14. Initialises `threading.Lock` and `_is_closed = False`.
15. `read()` delegates to `_retry_read` passing the current handle, `self._reopen`, source, and lock.
16. `_reopen()` creates a fresh `cv2.VideoCapture(device_index)`, stores it on `self._cap`, returns it.
17. `close()` acquires lock; if not already closed, releases the handle if open, marks `_is_closed = True`.

### Concrete Subclass: `RtspCamera`

18. Constructor accepts `RtspCameraConfig`.
19. Validates `rtsp_url` starts with `"rtsp://"` — raises `ValidationError` if not.
20. Sets `source` to the full RTSP URL string.
21. Opens `cv2.VideoCapture(config.rtsp_url)` immediately.
22. Raises `DeviceNotFoundError` if `cap.isOpened()` returns `False` — no retry at construction.
23. Initialises `threading.Lock` and `_is_closed = False`.
24. `read()` delegates to `_retry_read` identically to `LocalCamera`.
25. `_reopen()` creates a fresh `cv2.VideoCapture(rtsp_url)`, stores it on `self._cap`, returns it.
26. `close()` is identical in logic to `LocalCamera.close()`.

## Inputs

### `LocalCamera.__init__`

| Field | Type | Constraints | Required? |
|---|---|---|---|
| `config` | `LocalCameraConfig` | Valid `LocalCameraConfig` instance | Yes |

### `RtspCamera.__init__`

| Field | Type | Constraints | Required? |
|---|---|---|---|
| `config` | `RtspCameraConfig` | Valid `RtspCameraConfig` instance; `rtsp_url` must start with `rtsp://` | Yes |

### `_retry_read`

| Field | Type | Constraints | Required? |
|---|---|---|---|
| `open_cap` | `cv2.VideoCapture` | Already-opened handle | Yes |
| `reopen_fn` | `Callable[[], cv2.VideoCapture]` | Returns a fresh opened handle | Yes |
| `source` | `str` | Human-readable source identifier | Yes |
| `lock` | `threading.Lock` | Per-instance lock | Yes |

## Outputs

### `read()` / `_retry_read`

| Field | Type | Description |
|---|---|---|
| return | `Frame` | Frame with `.data` (copied BGR `ndarray`), `.timestamp` (POSIX float), `.source` (string) |

### Exceptions

| Exception | Condition | Raised by |
|---|---|---|
| `ValidationError` | `rtsp_url` does not start with `rtsp://` | `RtspCamera.__init__()` |
| `DeviceNotFoundError` | Device/URL unreachable at construction | `LocalCamera.__init__()`, `RtspCamera.__init__()` |
| `OperationError` | All 3 retry attempts exhausted during `read()` | `_retry_read()` |

## Invariants

- `CameraCapture` is never instantiated directly.
- `Frame.data` is always a `.copy()` of the OpenCV buffer — never a view.
- `Frame.timestamp` is captured immediately after a successful `cap.read()`, not before.
- `Frame.data` colour space is always BGR.
- `close()` is idempotent — multiple calls are safe.
- The per-instance lock protects individual `cap.read()`, `cap.release()`, and `reopen_fn()` calls — not the entire retry loop duration.
- Retry waits (`time.sleep`) occur outside the lock so `close()` from another thread is not blocked during sleep intervals (though `close()` will still block if the lock is held for a `cap` operation).
- Module-level constants: `_MAX_ATTEMPTS = 3`, `_RETRY_BASE_WAITS = (1.0, 2.0, 4.0)`.

## Edge Cases

- Condition: `cv2.VideoCapture.read()` returns `(False, None)` on all 3 attempts.
  Expected: `OperationError` raised after exhausting retries (including final 4s + jitter wait).

- Condition: `close()` called while `_retry_read` is sleeping between attempts.
  Expected: `close()` does not block during the sleep; it blocks only if the lock is held for a brief `cap` operation. The retry loop continues after waking and may attempt to use a released handle — the next `cap.read()` will simply fail and count as a failed attempt.

- Condition: `close()` called multiple times.
  Expected: Second and subsequent calls are no-ops (idempotent via `_is_closed` flag).

- Condition: `RtspCamera` constructed with `rtsps://` URL.
  Expected: `ValidationError` raised.

- Condition: `RtspCamera` constructed with `rtsp://` URL that is unreachable.
  Expected: `DeviceNotFoundError` raised (no retry at construction).

## Related

- [Frame](./entities/frame.md): output entity constructed by `_retry_read`.
- [CameraConfig](./entities/camera_config.md): input configuration entities.
- [exceptions](./exceptions.md): `DeviceNotFoundError`, `OperationError`, `ValidationError`.
- [ARCHITECTURE.md](../ARCHITECTURE.md): CameraCapture component role.
