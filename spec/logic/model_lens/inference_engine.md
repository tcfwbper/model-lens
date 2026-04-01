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
└── TorchInferenceEngine ← concrete MVP implementation (.pt model via PyTorch)
```

Future backends (e.g., ONNX, TFLite) are added as additional subclasses. The abstract base class
defines the full public contract; concrete subclasses implement it independently.

---

## Abstract Base Class: `InferenceEngine`

### Responsibility

- Define the public interface that all backends must satisfy.
- Own the label map: load it from `labels_path` at construction time and expose it as an internal
  lookup table for use by subclasses.
- Declare `detect()` as the sole public inference method.
- Declare `teardown()` as the public resource-release method.

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
| `ParseError` | A raw model output index has no corresponding entry in the label map |
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
consider inert: any subsequent call to `detect()` must raise `OperationError`.

#### Rules

- `teardown()` is **idempotent**: calling it more than once must not raise and must not cause
  undefined behaviour (the second and subsequent calls silently do nothing).
- `teardown()` is **thread-safe**; it acquires the same per-instance lock used by `detect()` before
  clearing any internal state, ensuring no concurrent `detect()` call observes a partially torn-down
  state.
- `detect()` must raise `OperationError` (not expose an `AttributeError` or other language-level
  error) if called after `teardown()` has completed.

---

### Label Map Loading

The base class is responsible for loading and parsing the label map file so that all subclasses
share the same parsing behaviour.

#### Format

- Plain text, one label per line.
- Every line, including blank lines and whitespace-only lines, **consumes one index slot**.
- Leading and trailing whitespace on non-blank lines is stripped before storing the label string.
- Blank or whitespace-only lines are stored as empty strings (`""`) in the lookup table.
- Line 0 (the first line) maps to index `0`, line 1 to index `1`, and so on — regardless of
  whether any line is blank.

#### Example label map file

```
person
bicycle
car

motorcycle
```

Parsed result: `{0: "person", 1: "bicycle", 2: "car", 3: "", 4: "motorcycle"}` (blank line at
index 3 is stored as an empty string).

#### Raises

| Exception | Condition |
|---|---|
| `ConfigurationError` | `labels_path` is non-empty but the file does not exist or cannot be read |
| `ConfigurationError` | The package-data fallback path cannot be resolved (e.g., package not installed correctly) |
| `ParseError` | The file is empty (zero lines) or contains only blank/whitespace lines (no non-empty labels could be loaded) |

### `ENGINE_REGISTRY`

A module-level dict mapping backend name strings to `InferenceEngine` subclasses. Defined in the
same module as the abstract base class. Engines must be imported explicitly at startup; no dynamic
loading is performed.

```python
ENGINE_REGISTRY: dict[str, type[InferenceEngine]] = {
    "torch": TorchInferenceEngine,
}
```

This registry is the designated extension point for future backends. Adding a new backend requires:
1. Implementing a new `InferenceEngine` subclass.
2. Adding one entry to `ENGINE_REGISTRY`.
3. No changes to the Detection Pipeline or any other component.

---

## Concrete Subclass: `TorchInferenceEngine`

### Responsibility

Load a `.pt` PyTorch model file and run inference using PyTorch. This is the sole MVP backend.

### Constructor

```python
def __init__(
    self,
    model_path: str,
    confidence_threshold: float,
    labels_path: str,
) -> None:
    ...
```

`TorchInferenceEngine` defines its own constructor independently; the abstract base class imposes
no constructor signature.

#### Parameters

| Parameter | Type | Source | Description |
|---|---|---|---|
| `model_path` | `str` | `AppConfig.model.model_path` | Absolute path to the `.pt` model file, or empty string to use the package-data default |
| `confidence_threshold` | `float` | `AppConfig.model.confidence_threshold` | Minimum confidence (inclusive) for a detection to be included in results |
| `labels_path` | `str` | `AppConfig.model.labels_path` | Absolute path to the label map file, or empty string to use the package-data default |

#### Path Resolution for Package-Data Fallback

When `model_path` or `labels_path` is an empty string, the constructor resolves the path using
`importlib.resources` (or equivalent). If the package-data resource cannot be located (e.g., the
package was not installed correctly or the data files are missing from the distribution),
`ConfigurationError` is raised immediately with a message identifying which resource could not be
found.

#### Raises

| Exception | Condition |
|---|---|
| `ConfigurationError` | `model_path` is non-empty but the file does not exist or cannot be read |
| `ConfigurationError` | `model_path` is empty and the package-data model file cannot be resolved |
| `ConfigurationError` | `labels_path` is empty and the package-data label map file cannot be resolved |
| `ConfigurationError` | `confidence_threshold` does not satisfy `0.0 < value <= 1.0` |
| `OperationError` | The model file exists but PyTorch fails to load it (e.g., corrupt file, incompatible format) |

### `detect()` Implementation Notes

- The method acquires the per-instance lock at entry and releases it before returning (including
  on exception paths), ensuring thread safety.
- At the start of each call (inside the lock), the method must check whether `teardown()` has
  already been called; if so, it must raise `OperationError` immediately.
- If the model requires RGB input, the subclass must convert the BGR `frame` to RGB internally
  using a copy (e.g., `frame[:, :, ::-1].copy()`); the original `frame` array must not be modified.
- Raw integer output indices from the model are translated to label strings via the label map
  loaded by the base class.
- If a raw index has no entry in the label map, `ParseError` is raised immediately.
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
- On the first call, the method sets an internal `_torn_down` flag, clears `_label_map`, and
  releases the reference to the loaded model (sets `_model` to `None`) so the garbage collector
  can reclaim GPU/CPU memory.
- A log message at `INFO` level is emitted after the resources are released.

---

## Lifecycle

```
Server startup
    │
    ▼
TorchInferenceEngine.__init__()
    ├── resolve model_path  (package-data fallback if empty; raises ConfigurationError if unresolvable)
    ├── resolve labels_path (package-data fallback if empty; raises ConfigurationError if unresolvable)
    ├── load label map      (base class, raises ConfigurationError / ParseError)
    ├── initialise per-instance threading.Lock and _torn_down flag
    └── load .pt model      (raises ConfigurationError / OperationError)
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
            └── acquires lock → sets _torn_down → clears _label_map → sets _model = None → releases lock
```

The engine instance is created once at startup and reused for the lifetime of the server process.
It is never recreated in response to runtime config changes (model path and confidence threshold
are fixed at startup per `spec/configuration.md`).

---

## Error Handling Summary

| Situation | Exception | Raised by |
|---|---|---|
| Label map file missing or unreadable | `ConfigurationError` | Base class label map loader |
| Package-data label map file cannot be resolved | `ConfigurationError` | `TorchInferenceEngine.__init__()` |
| Label map file has no non-blank lines | `ParseError` | Base class label map loader |
| Model file missing or unreadable | `ConfigurationError` | `TorchInferenceEngine.__init__()` |
| Package-data model file cannot be resolved | `ConfigurationError` | `TorchInferenceEngine.__init__()` |
| Model file corrupt / incompatible | `OperationError` | `TorchInferenceEngine.__init__()` |
| Raw output index not in label map | `ParseError` | `TorchInferenceEngine.detect()` |
| PyTorch inference call fails at runtime | `OperationError` | `TorchInferenceEngine.detect()` |
| `detect()` called after `teardown()` | `OperationError` | `TorchInferenceEngine.detect()` |
| Invalid `confidence_threshold` value | `ConfigurationError` | `TorchInferenceEngine.__init__()` |

All exceptions are subtypes of `ModelLensError` as defined in `spec/errors.md`.

---

## Constraints and Non-Goals

- The engine is **thread-safe** via a per-instance lock; concurrent calls to `detect()` are
  serialised automatically.
- The engine does **not** accept runtime changes to `model_path`, `labels_path`, or
  `confidence_threshold`. These are fixed at startup.
- The engine does **not** perform any frame annotation or rendering. Annotated output is the
  responsibility of the Detection Pipeline / Stream API.
- The engine does **not** manage camera lifecycle or frame acquisition.
- `ENGINE_REGISTRY` does not support dynamic plugin loading; all backends must be imported at
  startup.
- After `teardown()` is called, the engine cannot be re-used; there is no `reinitialise()` or
  equivalent. A new instance must be constructed if inference is needed again.
