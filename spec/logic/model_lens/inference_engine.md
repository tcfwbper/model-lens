# InferenceEngine Specification for ModelLens

## Core Principle

`InferenceEngine` is the abstract boundary between the Detection Pipeline and the underlying model
backend. It loads a model file and its label map once at startup, exposes a single `detect()` method
that accepts a raw BGR frame and returns a filtered, fully-resolved list of `DetectionResult` objects,
and is designed so that adding a new backend in the future requires only adding a new subclass —
no changes to the pipeline or any other component.

---

## Class Hierarchy

```
InferenceEngine          ← abstract base class
└── YOLOInferenceEngine  ← concrete MVP implementation (Ultralytics YOLO)
```

Future backends (e.g., ONNX, TFLite) are added as additional subclasses. The abstract base class
defines the full public contract; concrete subclasses implement it independently.

---

## Abstract Base Class: `InferenceEngine`

### Responsibility

- Define the public interface that all backends must satisfy.
- Own the label map: populated at construction time via the `_get_label_map()` hook implemented by
  each subclass, and exposed as an internal lookup table `_label_map`.
- Declare `detect()` as the sole public inference method.
- Declare `teardown()` as the public resource-release method.
- Declare `get_label_map()` as the public accessor for the label map.

### Abstract Method: `_get_label_map()`

```python
@abstractmethod
def _get_label_map(self) -> dict[int, str]:
    ...
```

Called once during `__init__` to populate `_label_map`. Each subclass implements this to retrieve
the label map from its specific model backend.

### Abstract Method: `get_label_map()`

```python
@abstractmethod
def get_label_map(self) -> dict[int, str]:
    ...
```

Public accessor that returns a copy of the current label map. Raises `OperationError` if called
after `teardown()`.

### Abstract Method: `detect()`

```python
@abstractmethod
def detect(
    self,
    frame: numpy.ndarray,
    target_labels: list[str],
) -> list[DetectionResult]:
    ...
```

#### Parameters

| Parameter | Type | Description |
|---|---|---|
| `frame` | `numpy.ndarray` | BGR image, shape `(H, W, 3)`, dtype `uint8` |
| `target_labels` | `list[str]` | Current target label strings from `RuntimeConfig`; passed per call so the engine always uses the latest value without requiring a state update |

#### Return Value

A `list[DetectionResult]`, possibly empty, containing only detections whose `confidence` is greater
than or equal to `confidence_threshold`. The list is ordered by descending confidence. Each
`DetectionResult` has:

- `label` — resolved human-readable string from the label map (never a raw integer index).
- `confidence` — float in `(0.0, 1.0]`.
- `bounding_box` — normalised `(x1, y1, x2, y2)` floats in `[0.0, 1.0]`, top-left origin.
- `is_target` — `True` if `label` is in `target_labels`.

#### Raises

| Exception | Condition |
|---|---|
| `OperationError` | The inference call fails unexpectedly at runtime |

#### Rules

- `detect()` must **not** mutate `frame` or any element of `target_labels`.
- `detect()` is **thread-safe**; concurrent callers are serialised internally via a per-instance
  lock acquired at the start of each call and released before returning.
- Sub-threshold detections (those with `confidence` strictly less than `confidence_threshold`) are
  filtered out inside `detect()` before the result list is constructed; they are never returned to
  the caller. Detections with `confidence` exactly equal to `confidence_threshold` are **kept**.
- `is_target` is computed inside `detect()` by checking `label in target_labels`.
- BGR→RGB conversion, if required by the backend, is performed inside the concrete subclass
  implementation and must not modify the input `frame` array.

### Abstract Method: `teardown()`

```python
@abstractmethod
def teardown(self) -> None:
    ...
```

Releases all resources held by the engine instance. After `teardown()` returns, the engine is
considered inert: any subsequent call to `detect()` must raise `OperationError`.

#### Rules

- `teardown()` is **idempotent**: calling it more than once must not raise and must not cause
  undefined behaviour (the second and subsequent calls silently do nothing).
- `teardown()` is **thread-safe**; it acquires the same per-instance lock used by `detect()` before
  clearing any internal state, ensuring no concurrent `detect()` call observes a partially torn-down
  state.
- `detect()` must raise `OperationError` (not expose an `AttributeError` or other language-level
  error) if called after `teardown()` has completed.

---

### `ENGINE_REGISTRY`

A module-level dict mapping backend name strings to `InferenceEngine` subclasses. Defined in the
same module as the abstract base class. Engines must be imported explicitly at startup; no dynamic
loading is performed.

```python
ENGINE_REGISTRY: dict[str, type[InferenceEngine]] = {
    "yolo": YOLOInferenceEngine,
}
```

This registry is the designated extension point for future backends. Adding a new backend requires:
1. Implementing a new `InferenceEngine` subclass.
2. Adding one entry to `ENGINE_REGISTRY`.
3. No changes to the Detection Pipeline or any other component.

---

## Concrete Subclass: `YOLOInferenceEngine`

### Responsibility

Load an Ultralytics YOLO model and run inference using it. This is the sole MVP backend.

### Constructor

```python
def __init__(
    self,
    model: str,
    confidence_threshold: float,
) -> None:
    ...
```

`YOLOInferenceEngine` defines its own constructor independently; the abstract base class imposes
no constructor signature.

#### Parameters

| Parameter | Type | Source | Description |
|---|---|---|---|
| `model` | `str` | `AppConfig.model.model_name` | Model name or path passed to `YOLO()` (e.g. `"yolov8n.pt"`) |
| `confidence_threshold` | `float` | `AppConfig.model.confidence_threshold` | Minimum confidence (inclusive) for a detection to be included in results |

#### Initialisation Order

1. Validate `confidence_threshold`.
2. Initialise `_lock` and `_torn_down`.
3. Load the YOLO model via `_load_model(model)` → stored in `_model`.
4. Call `super().__init__()` which invokes `_get_label_map()` to populate `_label_map` from
   `self._model.names`.

#### Raises

| Exception | Condition |
|---|---|
| `ConfigurationError` | `confidence_threshold` does not satisfy `0.0 < value <= 1.0` |
| `OperationError` | The YOLO model fails to load (e.g., invalid name, file not found, incompatible format) |

### Label Map

The label map is populated from the loaded YOLO model's `names` attribute (`self._model.names`),
which maps integer class indices to human-readable label strings. No separate label file is used.

### `get_label_map()` Implementation Notes

- Acquires the per-instance lock before reading `_label_map`.
- Raises `OperationError` if called after `teardown()`.
- Returns a copy of `_label_map` so callers cannot mutate internal state.

### `detect()` Implementation Notes

- The method acquires the per-instance lock at entry and releases it before returning (including
  on exception paths), ensuring thread safety.
- At the start of each call (inside the lock), the method must check whether `teardown()` has
  already been called; if so, it must raise `OperationError` immediately.
- Also raises `OperationError` if `_model` is `None`.
- If the model requires RGB input, the subclass must convert the BGR `frame` to RGB internally
  using a copy; the original `frame` array must not be modified.
- Raw integer output indices from the model are translated to label strings via `_label_map`.
- Detections with `confidence` strictly less than `confidence_threshold` are discarded before
  constructing `DetectionResult` objects. Detections with `confidence` exactly equal to
  `confidence_threshold` are **kept**.
- `is_target` is set by evaluating `label in target_labels` for each surviving detection.
- The returned list is ordered by descending `confidence`.

### `teardown()` Implementation Notes

- The method acquires the per-instance lock before clearing any state, so it cannot interleave
  with an in-progress `detect()` call.
- Inside the lock, the method checks whether the engine is already torn down (idempotency guard);
  if so it returns immediately without logging or mutating state.
- On the first call, the method sets `_torn_down = True` and releases the reference to the loaded
  model (sets `_model` to `None`) so the garbage collector can reclaim GPU/CPU memory.
- `_label_map` is **not** cleared by `teardown()`.
- A log message at `INFO` level is emitted after the resources are released.

---

## Lifecycle

```
Server startup
    │
    ▼
YOLOInferenceEngine.__init__()
    ├── validate confidence_threshold  (raises ConfigurationError if invalid)
    ├── initialise per-instance threading.Lock and _torn_down flag
    ├── load YOLO model via YOLO(model)  (raises OperationError if load fails)
    └── populate _label_map from model.names
    │
    ▼
Detection Pipeline loop (may be called from multiple threads)
    │
    ├── frame = CameraCapture.read()
    ├── results = engine.detect(frame.data, runtime_config.target_labels)
    │       └── acquires lock → checks _torn_down → runs inference → releases lock
    └── publish (frame, results) → SSE queue
    │
    ▼
Server shutdown
    │
    └── engine.teardown()
            └── acquires lock → sets _torn_down → sets _model = None → releases lock
```

The engine instance is created once at startup and reused for the lifetime of the server process.
It is never recreated in response to runtime config changes (model and confidence threshold
are fixed at startup per `spec/configuration.md`).

---

## Error Handling Summary

| Situation | Exception | Raised by |
|---|---|---|
| Invalid `confidence_threshold` value | `ConfigurationError` | `YOLOInferenceEngine.__init__()` |
| YOLO model fails to load | `OperationError` | `YOLOInferenceEngine.__init__()` |
| PyTorch inference call fails at runtime | `OperationError` | `YOLOInferenceEngine.detect()` |
| `detect()` called when `_model` is `None` | `OperationError` | `YOLOInferenceEngine.detect()` |
| `detect()` called after `teardown()` | `OperationError` | `YOLOInferenceEngine.detect()` |
| `get_label_map()` called after `teardown()` | `OperationError` | `YOLOInferenceEngine.get_label_map()` |

All exceptions are subtypes of `ModelLensError` as defined in `spec/errors.md`.

---

## Constraints and Non-Goals

- The engine is **thread-safe** via a per-instance lock; concurrent calls to `detect()` are
  serialised automatically.
- The engine does **not** accept runtime changes to `model` or `confidence_threshold`. These are
  fixed at startup.
- The engine does **not** perform any frame annotation or rendering. Annotated output is the
  responsibility of the Detection Pipeline / Stream API.
- The engine does **not** manage camera lifecycle or frame acquisition.
- `ENGINE_REGISTRY` does not support dynamic plugin loading; all backends must be imported at
  startup.
- After `teardown()` is called, the engine cannot be re-used; there is no `reinitialise()` or
  equivalent. A new instance must be constructed if inference is needed again.
