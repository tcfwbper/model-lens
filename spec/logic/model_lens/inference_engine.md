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

A `list[DetectionResult]`, possibly empty, containing only detections whose `confidence` exceeds
`confidence_threshold`. The list is ordered by descending confidence. Each `DetectionResult` has:

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
- `detect()` is **not thread-safe**; callers must ensure it is invoked from a single thread only.
- Sub-threshold detections are filtered out inside `detect()` before the result list is constructed;
  they are never returned to the caller.
- `is_target` is computed inside `detect()` by checking `label in target_labels`.
- BGR→RGB conversion, if required by the backend, is performed inside the concrete subclass
  implementation and must not modify the input `frame` array.

### Label Map Loading

The base class is responsible for loading and parsing the label map file so that all subclasses
share the same parsing behaviour.

#### Format

- Plain text, one label per line.
- Blank lines and whitespace-only lines are **skipped** and do not consume an index slot.
- Leading and trailing whitespace on non-blank lines is stripped.
- The first non-blank line maps to index `0`, the second to index `1`, and so on.

#### Example label map file

```
person
bicycle
car

motorcycle
```

Parsed result: `{0: "person", 1: "bicycle", 2: "car", 3: "motorcycle"}` (blank line skipped).

#### Raises

| Exception | Condition |
|---|---|
| `ConfigurationError` | `labels_path` is non-empty but the file does not exist or cannot be read |
| `ParseError` | The file is empty after skipping blank lines (no labels could be loaded) |

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
| `confidence_threshold` | `float` | `AppConfig.model.confidence_threshold` | Minimum confidence for a detection to be included in results |
| `labels_path` | `str` | `AppConfig.model.labels_path` | Absolute path to the label map file, or empty string to use the package-data default |

#### Raises

| Exception | Condition |
|---|---|
| `ConfigurationError` | `model_path` is non-empty but the file does not exist or cannot be read |
| `ConfigurationError` | `confidence_threshold` does not satisfy `0.0 < value <= 1.0` |
| `OperationError` | The model file exists but PyTorch fails to load it (e.g., corrupt file, incompatible format) |

### `detect()` Implementation Notes

- If the model requires RGB input, the subclass must convert the BGR `frame` to RGB internally
  using a copy (e.g., `frame[:, :, ::-1].copy()`); the original `frame` array must not be modified.
- Raw integer output indices from the model are translated to label strings via the label map
  loaded by the base class.
- If a raw index has no entry in the label map, `ParseError` is raised immediately.
- Detections with `confidence <= confidence_threshold` are discarded before constructing
  `DetectionResult` objects.
- `is_target` is set by evaluating `label in target_labels` for each surviving detection.
- The returned list is ordered by descending `confidence`.

---

## Lifecycle

```
Server startup
    │
    ▼
TorchInferenceEngine.__init__()
    ├── resolve model_path  (package-data fallback if empty)
    ├── resolve labels_path (package-data fallback if empty)
    ├── load label map      (base class, raises ConfigurationError / ParseError)
    └── load .pt model      (raises ConfigurationError / OperationError)
    │
    ▼
Detection Pipeline loop (single thread)
    │
    ├── frame = CameraCapture.read()
    ├── results = engine.detect(frame.data, runtime_config.target_labels)
    └── publish (frame, results) → SSE queue
```

The engine instance is created once at startup and reused for the lifetime of the server process.
It is never recreated in response to runtime config changes (model path and confidence threshold
are fixed at startup per `spec/configuration.md`).

---

## Error Handling Summary

| Situation | Exception | Raised by |
|---|---|---|
| Label map file missing or unreadable | `ConfigurationError` | Base class label map loader |
| Label map file has no non-blank lines | `ParseError` | Base class label map loader |
| Model file missing or unreadable | `ConfigurationError` | `TorchInferenceEngine.__init__()` |
| Model file corrupt / incompatible | `OperationError` | `TorchInferenceEngine.__init__()` |
| Raw output index not in label map | `ParseError` | `TorchInferenceEngine.detect()` |
| PyTorch inference call fails at runtime | `OperationError` | `TorchInferenceEngine.detect()` |
| Invalid `confidence_threshold` value | `ConfigurationError` | `TorchInferenceEngine.__init__()` |

All exceptions are subtypes of `ModelLensError` as defined in `spec/errors.md`.

---

## Constraints and Non-Goals

- The engine is **not thread-safe**. The Detection Pipeline must call `detect()` from a single
  thread only.
- The engine does **not** accept runtime changes to `model_path`, `labels_path`, or
  `confidence_threshold`. These are fixed at startup.
- The engine does **not** perform any frame annotation or rendering. Annotated output is the
  responsibility of the Detection Pipeline / Stream API.
- The engine does **not** manage camera lifecycle or frame acquisition.
- `ENGINE_REGISTRY` does not support dynamic plugin loading; all backends must be imported at
  startup.
