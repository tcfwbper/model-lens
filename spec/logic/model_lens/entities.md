# Entities Specification for ModelLens

## Core Principle

Entities are the shared domain data structures passed between components of the Detection Pipeline,
Config API, and Stream API. They are defined once and imported wherever needed. All entities are
immutable after construction.

---

## Entity: `CameraConfig`

### Purpose

Identifies the active camera source. Exactly one source type is active at any time. Implemented
as a sealed abstract base class with two concrete subclasses to enforce mutual exclusivity at the
type level.

### Class Hierarchy

```
CameraConfig          ← abstract base (frozen dataclass)
├── LocalCameraConfig ← source_type = "local"
└── RtspCameraConfig  ← source_type = "rtsp"
```

### `LocalCameraConfig`

| Field | Type | Default | Validation |
|---|---|---|---|
| `device_index` | `int` | `0` | `>= 0` |

### `RtspCameraConfig`

| Field | Type | Default | Validation |
|---|---|---|---|
| `rtsp_url` | `str` | — | Non-empty string |

### Rules

- Both subclasses are **frozen dataclasses** (`@dataclass(frozen=True)`).
- `CameraConfig` is an abstract base class; it must never be instantiated directly.
- Equality comparison between two `CameraConfig` instances is **not meaningful** and must not be
  relied upon by any component. No component may use `==` on `CameraConfig` instances to decide
  whether to recreate the camera source; the Config API always triggers recreation on any update.
- Validation runs at construction time and raises `ValidationError` on failure.

### Example

```python
local = LocalCameraConfig(device_index=0)
rtsp  = RtspCameraConfig(rtsp_url="rtsp://192.168.1.10/stream")
```

---

## Entity: `RuntimeConfig`

### Purpose

The full mutable runtime state of the server. Holds the active camera configuration, the list of
target labels, and the model confidence threshold. Replaced atomically on each update; never
mutated in place.

### Fields

| Field | Type | Default | Mutable via API | Source |
|---|---|---|---|---|
| `camera` | `CameraConfig` | `LocalCameraConfig(device_index=0)` | ✅ | `AppConfig.camera` |
| `target_labels` | `list[str]` | `[]` | ✅ | Not in `AppConfig`; always starts empty |
| `confidence_threshold` | `float` | `0.5` | ❌ | `AppConfig.model.confidence_threshold` |

### Rules

- Implemented as a **frozen dataclass** (`@dataclass(frozen=True)`).
- The Config API replaces the entire `RuntimeConfig` instance atomically (swap the reference);
  it never mutates fields in place.
- `target_labels` is an empty list by default, meaning no objects are flagged as targets until
  the user configures labels via the Config API.
- `confidence_threshold` is copied from `AppConfig` at startup and is not modifiable at runtime
  through the Config API.
- `camera` is the only `AppConfig`-sourced field that the Config API may replace at runtime.

### Atomic Replacement Protocol

The component that owns the `RuntimeConfig` reference (the Detection Pipeline) must expose a
thread-safe swap mechanism (e.g., a lock-protected setter) so that the Config API can replace
the instance without a race condition.

---

## Entity: `DetectionResult`

### Purpose

Represents a single detected object produced by one inference pass. Contains the resolved
human-readable label, confidence score, normalised bounding box, and a flag indicating whether
the label is in the configured target list.

### Fields

| Field | Type | Constraints |
|---|---|---|
| `label` | `str` | Non-empty; resolved from the label map before construction |
| `confidence` | `float` | `0.0 < value <= 1.0` |
| `bounding_box` | `tuple[float, float, float, float]` | See bounding box format below |
| `is_target` | `bool` | `True` if `label` is in `RuntimeConfig.target_labels` |

### Bounding Box Format

```
(x1, y1, x2, y2)
```

| Component | Meaning |
|---|---|
| `x1`, `y1` | Top-left corner of the bounding box |
| `x2`, `y2` | Bottom-right corner of the bounding box |

- All four values are **normalised floats** in the range `[0.0, 1.0]`.
- The coordinate origin is the **top-left corner** of the frame.
- `x` increases left → right; `y` increases top → bottom.
- Values are not clamped automatically; `InferenceEngine` is responsible for producing valid
  normalised coordinates.

### Rules

- Implemented as a **frozen dataclass** (`@dataclass(frozen=True)`).
- `label` is always a resolved string from the label map. Raw integer indices must never appear
  in a `DetectionResult`; translation is the responsibility of `InferenceEngine`.
- `is_target` is computed at construction time by the caller (the Detection Pipeline) by checking
  `label` against the current `RuntimeConfig.target_labels`.
- The pipeline produces a `list[DetectionResult]` per frame — zero or more results.

### Example

```python
DetectionResult(
    label="cat",
    confidence=0.87,
    bounding_box=(0.1, 0.2, 0.4, 0.6),
    is_target=True,
)
```

---

## Entity: `Frame`

### Purpose

A single decoded image captured from a camera source, together with metadata identifying when
and where it was captured. Always a copy of the buffer returned by the camera driver; never a
view into a shared buffer.

### Fields

| Field | Type | Constraints |
|---|---|---|
| `data` | `numpy.ndarray` | Shape `(H, W, 3)`, dtype `uint8`, colour space **BGR** |
| `timestamp` | `float` | POSIX timestamp (seconds since 1970-01-01T00:00:00Z) at the moment of frame capture |
| `source` | `str` | Human-readable identifier for the camera source (e.g., `"local:0"` or `"rtsp://..."`) |

### Rules

- Implemented as a **dataclass** (`@dataclass`). Not frozen because `numpy.ndarray` is not
  hashable; however, `data` must be treated as read-only by all consumers.
- `data` is always a **copy** (`numpy.ndarray.copy()`) of the buffer returned by the camera
  driver. `CameraCapture` is responsible for making this copy before constructing the `Frame`.
- Colour space is **BGR** (OpenCV native). Conversion to RGB, if required by the inference
  backend, is the responsibility of `InferenceEngine` and must not modify the `Frame.data` array.
- `timestamp` is a POSIX timestamp (float, seconds since 1970-01-01T00:00:00 UTC). It must be
  captured immediately after a successful frame read and must have sub-second precision.
- `source` is set by `CameraCapture` at construction time and reflects the active source
  (e.g., `"local:0"` for `LocalCameraConfig(device_index=0)`, or the full RTSP URL for
  `RtspCameraConfig`).

### Example

```python
Frame(
    data=numpy_bgr_array,          # shape (480, 640, 3), dtype uint8
    timestamp=1748000400.123456,   # POSIX timestamp with sub-second precision
    source="local:0",
)
```

---

## Summary Table

| Entity | Dataclass Frozen | Mutable After Init | Owned By |
|---|---|---|---|
| `LocalCameraConfig` | ✅ | ❌ | Config API / `AppConfig` loader |
| `RtspCameraConfig` | ✅ | ❌ | Config API / `AppConfig` loader |
| `RuntimeConfig` | ✅ | ❌ (replaced atomically) | Detection Pipeline |
| `DetectionResult` | ✅ | ❌ | `InferenceEngine` / Detection Pipeline |
| `Frame` | ❌ | `data` treated as read-only | `CameraCapture` |
