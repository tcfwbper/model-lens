# CameraCapture Specification for ModelLens

## Core Principle

`CameraCapture` is the abstract boundary between the Detection Pipeline and the underlying camera
hardware or network stream. It owns an open connection to a camera source, vends `Frame` objects
on demand via a blocking `read()` call, and is recreated by the Detection Pipeline whenever the
camera configuration changes. Both source types use OpenCV (`cv2.VideoCapture`) as the unified
capture backend (ADR-0007).

---

## Class Hierarchy

```
CameraCapture     ← abstract base class
├── LocalCamera   ← source_type = "local"  (cv2.VideoCapture with device index)
└── RtspCamera    ← source_type = "rtsp"   (cv2.VideoCapture with RTSP URL)
```

Future source types are added as additional subclasses. The abstract base class defines the full
public contract; concrete subclasses implement it independently.

---

## Abstract Base Class: `CameraCapture`

### Responsibility

- Define the public interface that all camera backends must satisfy.
- Declare `read()` as the sole public frame-acquisition method.
- Declare `close()` as the public resource-release method.
- Support context manager protocol (`__enter__` / `__exit__`) for deterministic lifecycle management.
- Own the `frame_index` counter; increment it on every successful `read()` call.

### Constructor

`CameraCapture` is abstract and must never be instantiated directly. It defines no constructor
signature; each concrete subclass defines its own.

### Abstract Method: `read()`

```python
@abstractmethod
def read(self) -> Frame:
    ...
```

#### Behaviour

- Blocking call: does not return until a valid frame is available or all retries are exhausted.
- On success, returns a `Frame` constructed from a **copy** of the numpy array returned by
  `cv2.VideoCapture.read()`.
- Thread-safe: a per-instance lock is acquired at entry and released before returning (including
  on all exception paths).

#### Return Value

A `Frame` with:

| Field | Value |
|---|---|
| `data` | `numpy.ndarray`, shape `(H, W, 3)`, dtype `uint8`, colour space BGR; always a `.copy()` of the OpenCV buffer |
| `timestamp` | POSIX timestamp (float, seconds since 1970-01-01T00:00:00 UTC) with sub-second precision, captured immediately after a successful `cv2.VideoCapture.read()` |
| `frame_index` | Current value of the instance counter, then incremented by 1 |
| `source` | Human-readable source identifier set at construction time (see per-subclass rules below) |

#### Raises

| Exception | Condition |
|---|---|
| `OperationError` | All retry attempts are exhausted without obtaining a valid frame |

#### Retry Strategy (shared by both subclasses)

When `cv2.VideoCapture.read()` returns `(False, None)` or an otherwise invalid frame:

1. The existing `cv2.VideoCapture` handle is released.
2. A new `cv2.VideoCapture` handle is opened with the same source (device index or RTSP URL).
3. `read()` is retried on the new handle.
4. If the new handle also fails, the sequence repeats up to **3 attempts total** (the initial
   failure plus two retries — wait intervals: 1 s, 2 s, 4 s before each successive attempt).
5. Each wait interval has **uniform jitter** added: `wait = base_seconds + random.uniform(0.0, 1.0)`.
6. If all 3 attempts are exhausted, `OperationError` is raised.

| Attempt | Base wait before this attempt |
|---|---|
| 1 (initial) | 0 s (no wait) |
| 2 (retry 1) | 1 s + jitter |
| 3 (retry 2) | 2 s + jitter |
| — (give up) | 4 s + jitter elapsed, then raise `OperationError` |

`frame_index` is **not** reset during reconnection; it is only reset when a new `CameraCapture`
instance is constructed.

### Abstract Method: `close()`

```python
@abstractmethod
def close(self) -> None:
    ...
```

Releases the underlying `cv2.VideoCapture` handle and any other resources held by the instance.
Thread-safe: protected by the same per-instance lock as `read()`.
Calling `close()` more than once must be safe (idempotent).

### Context Manager Protocol

```python
def __enter__(self) -> "CameraCapture":
    return self

def __exit__(
    self,
    exc_type: type[BaseException] | None,
    exc_val: BaseException | None,
    exc_tb: TracebackType | None,
) -> None:
    self.close()
```

Both methods are implemented on the abstract base class and delegate to `close()`. Subclasses
must not override `__enter__` or `__exit__`.

### Lock and `close()` Interaction

The per-instance lock covers both `read()` and `close()`. If `close()` is called while `read()`
holds the lock (e.g., during a retry sleep), `close()` will block until `read()` releases the
lock. The retry loop inside `read()` checks for no cancellation signal; callers that need prompt
shutdown should arrange for the Detection Pipeline to stop calling `read()` before calling
`close()`.

---

## Concrete Subclass: `LocalCamera`

### Responsibility

Open a local webcam by device index using `cv2.VideoCapture(device_index)` and vend frames.

### Constructor

```python
def __init__(self, config: LocalCameraConfig) -> None:
    ...
```

#### Behaviour

1. Initialises `frame_index` to `0`.
2. Sets `source` to `f"local:{config.device_index}"`.
3. Opens `cv2.VideoCapture(config.device_index)` immediately.
4. If the handle is not opened successfully (`cap.isOpened()` returns `False`), raises
   `DeviceNotFoundError` immediately — **no retry at construction time**.
5. Initialises the per-instance `threading.Lock`.

#### Raises

| Exception | Condition |
|---|---|
| `DeviceNotFoundError` | `cv2.VideoCapture` cannot open the device index on the first attempt |

### `read()` Implementation Notes

- Acquires the per-instance lock.
- Calls `cap.read()` on the existing handle.
- On failure, applies the shared retry strategy (re-opens handle, waits with jitter).
- On success, copies the frame buffer, constructs and returns a `Frame`, increments `frame_index`.
- Releases the lock before returning or raising.

### `close()` Implementation Notes

- Acquires the per-instance lock.
- Calls `cap.release()` on the handle if it is open.
- Marks the handle as released to ensure idempotency.
- Releases the lock.

---

## Concrete Subclass: `RtspCamera`

### Responsibility

Open an RTSP stream by URL using `cv2.VideoCapture(rtsp_url)` and vend frames, with reconnect
logic for network interruptions.

### Constructor

```python
def __init__(self, config: RtspCameraConfig) -> None:
    ...
```

#### Input Validation

`rtsp_url` must be a non-empty string beginning with `rtsp://`. The remainder may be:
- A domain name (e.g., `rtsp://example.com/stream`)
- An IP address with port (e.g., `rtsp://192.168.1.10:554/stream`)
- An IP address with port and route (e.g., `rtsp://192.168.1.10:554/live/channel1`)

`rtsps://` (TLS) is **not** supported in this version and must be rejected with
`ValidationError` if supplied.

#### Behaviour

1. Validates `rtsp_url` format; raises `ValidationError` if invalid.
2. Initialises `frame_index` to `0`.
3. Sets `source` to the full RTSP URL string.
4. Opens `cv2.VideoCapture(config.rtsp_url)` immediately.
5. If the handle is not opened successfully (`cap.isOpened()` returns `False`), raises
   `DeviceNotFoundError` immediately — **no retry at construction time**.
6. Initialises the per-instance `threading.Lock`.

#### Raises

| Exception | Condition |
|---|---|
| `ValidationError` | `rtsp_url` does not start with `rtsp://` |
| `DeviceNotFoundError` | `cv2.VideoCapture` cannot open the RTSP URL on the first attempt |

### `read()` Implementation Notes

- Identical retry strategy to `LocalCamera` (shared base behaviour).
- On network interruption (`cap.read()` returns `(False, None)`), re-opens the handle with the
  same RTSP URL and retries.
- Acquires and releases the per-instance lock identically to `LocalCamera`.

### `close()` Implementation Notes

- Identical to `LocalCamera.close()`.

---

## Lifecycle

```
Detection Pipeline
    │
    ▼
LocalCamera.__init__(config) / RtspCamera.__init__(config)
    ├── validate input (RtspCamera only)
    ├── set source string
    ├── open cv2.VideoCapture handle  → DeviceNotFoundError if fails immediately
    └── initialise threading.Lock, frame_index = 0
    │
    ▼
with camera:                          ← __enter__ returns self
    │
    ├── loop:
    │     frame = camera.read()       ← blocking; retries up to 3 attempts on failure
    │     pass frame to InferenceEngine
    │
    ▼
__exit__ → close()                    ← releases cv2.VideoCapture handle
```

When the Detection Pipeline receives a camera config change:
1. The existing `CameraCapture` instance is closed (via `close()` or context manager exit).
2. A new `CameraCapture` subclass instance is constructed from the new `CameraConfig`.
3. `frame_index` resets to `0` on the new instance.

---

## Error Handling Summary

| Situation | Exception | Raised by |
|---|---|---|
| `rtsp_url` does not start with `rtsp://` | `ValidationError` | `RtspCamera.__init__()` |
| Device index unreachable at startup | `DeviceNotFoundError` | `LocalCamera.__init__()` |
| RTSP URL unreachable at startup | `DeviceNotFoundError` | `RtspCamera.__init__()` |
| All retry attempts exhausted during `read()` | `OperationError` | `read()` (both subclasses) |

All exceptions are subtypes of `ModelLensError` as defined in `spec/errors.md`.

---

## Constraints and Non-Goals

- `CameraCapture` does **not** perform any frame annotation, inference, or format conversion.
  BGR colour space is preserved as-is; RGB conversion is the responsibility of `InferenceEngine`.
- `CameraCapture` does **not** manage `RuntimeConfig` or react to label changes.
- `rtsps://` (TLS-secured RTSP) is out of scope for this version.
- A single `CameraCapture` instance is used by a single Detection Pipeline; no multi-consumer
  fan-out is provided at this layer.
- `frame_index` immutability is not enforced in code; consumers must treat `Frame.data` as
  read-only by convention.
