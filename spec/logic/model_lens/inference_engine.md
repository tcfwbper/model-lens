# InferenceEngine

## Overview

Abstracts over model inference backends. Contains the `InferenceEngine` abstract base class, the `YOLOInferenceEngine` concrete subclass (MVP backend using Ultralytics YOLO), and the module-level `ENGINE_REGISTRY`. Loads a model and its label map once at construction, then produces filtered `DetectionResult` lists for each frame. Does not perform frame annotation, camera lifecycle management, or rendering.

## Boundaries

- Owns: model loading, label map population, inference execution, confidence filtering, `is_target` computation, bounding box normalisation, and result ordering.
- Owns: thread-safe access to the model via a per-instance lock.
- Owns: teardown (releasing model resources) and post-teardown guard.
- Delegates: frame acquisition to `CameraCapture`.
- Delegates: frame annotation and rendering to Detection Pipeline / Stream API.
- Delegates: camera lifecycle management to Detection Pipeline.
- Must not: mutate the input `frame` array or the `target_labels` list.
- Must not: accept runtime changes to `model` or `confidence_threshold`.
- Must not: perform frame annotation or rendering.
- Must not: manage camera lifecycle or frame acquisition.
- Must not: support dynamic plugin loading in `ENGINE_REGISTRY`.

## Dependencies

| Collaborator | Role | Allowed Interaction | Forbidden Interaction |
|---|---|---|---|
| `ultralytics.YOLO` | Model backend | `YOLO(model)`, `model(frame)`, `.names` | — |
| `model_lens.entities.DetectionResult` | Output entity | Construct via `DetectionResult(label=..., confidence=..., bounding_box=..., is_target=...)` | — |
| `model_lens.exceptions.ConfigurationError` | Error signaling | Raised when `confidence_threshold` is invalid | — |
| `model_lens.exceptions.OperationError` | Error signaling | Raised on model load failure, inference failure, or post-teardown access | — |
| `model_lens.exceptions.ParseError` | Error signaling | Abstract contract: may be raised by `detect()` if label map index lookup fails | — |
| `threading.Lock` | Concurrency | Per-instance lock serialising `detect()`, `get_label_map()`, and `teardown()` | — |
| `numpy` | Array type | `NDArray[np.uint8]` for frame input | Must not mutate the input array |

Construction constraint: `InferenceEngine` is abstract. `YOLOInferenceEngine` is constructed directly via `__init__(model, confidence_threshold)`. The abstract base class defines `__init__` which calls `self._get_label_map()` to populate `self._label_map`.

## Behavior

### Abstract Base Class: `InferenceEngine`

1. `__init__` is abstract; its body calls `self._get_label_map()` and stores the result in `self._label_map`.
2. Declares `_get_label_map()` as abstract — subclasses return their backend-specific label map.
3. Declares `get_label_map()` as abstract — public accessor returning a copy of the label map.
4. Declares `detect(frame, target_labels)` as abstract — runs inference and returns filtered results.
5. Declares `teardown()` as abstract — releases all resources.

### Concrete Subclass: `YOLOInferenceEngine`

#### Construction (Initialisation Order)

6. Validates `confidence_threshold` satisfies `0.0 < value <= 1.0`; raises `ConfigurationError` if not.
7. Stores `_confidence_threshold`.
8. Initialises `_lock` (`threading.Lock`) and `_torn_down = False`.
9. Loads the YOLO model via `_load_model(model)` — a static method that calls `YOLO(model)` and returns the result; raises `OperationError` if loading fails.
10. Stores loaded model in `_model`.
11. Calls `super().__init__()` which invokes `_get_label_map()` to populate `_label_map` from `self._model.names`.

#### `_get_label_map()`

12. Raises `OperationError` if `self._model` is `None`.
13. Returns `self._model.names` (a `dict[int, str]`).

#### `get_label_map()`

14. Acquires per-instance lock.
15. Raises `OperationError` if `_torn_down` is `True`.
16. Returns `self._label_map.copy()`.

#### `detect(frame, target_labels)`

17. Acquires per-instance lock (held for the entire method body).
18. Raises `OperationError` if `_torn_down` is `True`.
19. Raises `OperationError` if `_model` is `None`.
20. Calls `self._model(frame)` to run inference; wraps any exception in `OperationError`.
21. Iterates over boxes in the first result (`raw_results[0].boxes`).
22. For each detection box:
    - Resolves label from `self._label_map[int(boxes.cls[i].item())]`.
    - Extracts confidence as `float(boxes.conf[i].item())`.
    - Computes normalised bounding box: divides pixel coordinates by frame dimensions `(w, h)`.
    - Skips (does not include) detections with `confidence < self._confidence_threshold`.
    - Constructs `DetectionResult` with `is_target = (label in target_labels)`.
23. Sorts results by descending `confidence`.
24. Returns the sorted list (may be empty).

#### `teardown()`

25. Acquires per-instance lock.
26. If `_torn_down` is already `True`, returns immediately (idempotent).
27. Sets `_torn_down = True`.
28. Sets `_model = None` (releases model for garbage collection).
29. Does NOT clear `_label_map`.
30. Releases lock, then logs at `INFO` level.

### Module-Level: `ENGINE_REGISTRY`

31. A `dict[str, type[InferenceEngine]]` mapping backend name strings to subclasses.
32. Contains `{"yolo": YOLOInferenceEngine}` at module definition time.
33. No dynamic loading — all backends are imported explicitly at startup.

## Inputs

### `YOLOInferenceEngine.__init__`

| Field | Type | Constraints | Required? |
|---|---|---|---|
| `model` | `str` | Model name or path passed to `YOLO()` (e.g. `"yolov8n.pt"`) | Yes |
| `confidence_threshold` | `float` | `0.0 < value <= 1.0` | Yes |

### `detect()`

| Field | Type | Constraints | Required? |
|---|---|---|---|
| `frame` | `NDArray[np.uint8]` | BGR image, shape `(H, W, 3)`, dtype `uint8` | Yes |
| `target_labels` | `list[str]` | Current target label strings | Yes |

## Outputs

### `detect()`

| Field | Type | Description |
|---|---|---|
| return | `list[DetectionResult]` | Filtered, sorted (descending confidence) list; may be empty |

### `get_label_map()`

| Field | Type | Description |
|---|---|---|
| return | `dict[int, str]` | Copy of label map (class index → label string) |

### Exceptions

| Exception | Condition | Raised by |
|---|---|---|
| `ConfigurationError` | `confidence_threshold` not in `(0.0, 1.0]` | `YOLOInferenceEngine.__init__()` |
| `OperationError` | YOLO model fails to load | `YOLOInferenceEngine.__init__()` (via `_load_model`) |
| `OperationError` | Inference call fails at runtime | `YOLOInferenceEngine.detect()` |
| `OperationError` | `_model` is `None` when `detect()` called | `YOLOInferenceEngine.detect()` |
| `OperationError` | `detect()` called after `teardown()` | `YOLOInferenceEngine.detect()` |
| `OperationError` | `get_label_map()` called after `teardown()` | `YOLOInferenceEngine.get_label_map()` |
| `ParseError` | Label map index lookup fails (model output references an index absent from the label map) | `InferenceEngine.detect()` (abstract contract — future backends may raise; current YOLO backend does not) |

## Invariants

- `InferenceEngine` is never instantiated directly.
- `confidence_threshold` is immutable after construction.
- `model` is immutable after construction (no hot-swap).
- `detect()` never mutates `frame` or `target_labels`.
- `detect()` and `teardown()` and `get_label_map()` are thread-safe via the same per-instance lock.
- After `teardown()`, any call to `detect()` or `get_label_map()` raises `OperationError` — never exposes `AttributeError` or other language-level errors.
- `teardown()` is idempotent — second and subsequent calls are silent no-ops.
- `_label_map` is NOT cleared by `teardown()`.
- `is_target` is computed inside `detect()` by `label in target_labels` — not delegated to the caller.
- Sub-threshold detections (confidence strictly less than threshold) are filtered out inside `detect()` before constructing `DetectionResult` objects. Detections with confidence exactly equal to threshold are kept.
- The returned list is ordered by descending confidence.
- `ENGINE_REGISTRY` does not support dynamic plugin loading.

## Edge Cases

- Condition: `confidence_threshold` is `0.0`.
  Expected: `ConfigurationError` raised (range is exclusive of zero).

- Condition: `confidence_threshold` is `1.0`.
  Expected: Valid construction (range is inclusive of 1.0).

- Condition: Model produces no detections (no boxes).
  Expected: Returns empty list `[]`.

- Condition: All detections are below `confidence_threshold`.
  Expected: Returns empty list `[]`.

- Condition: `detect()` called after `teardown()`.
  Expected: `OperationError` raised immediately (before any inference attempt).

- Condition: `teardown()` called multiple times.
  Expected: Second and subsequent calls are silent no-ops; no log emitted, no exception raised.

- Condition: `detect()` called concurrently from multiple threads.
  Expected: Serialised by lock — only one inference runs at a time.

- Condition: `boxes` is falsy (e.g. empty or `None`-like) in raw results.
  Expected: Returns empty list (the `if boxes:` guard skips iteration).

## Related

- [DetectionResult](./entities/detection_result.md): output entity constructed by `detect()`.
- [Frame](./entities/frame.md): input `frame.data` passed to `detect()`.
- [RuntimeConfig](./entities/runtime_config.md): provides `target_labels` passed per call.
- [exceptions](./exceptions.md): `ConfigurationError`, `OperationError`, `ParseError`.
- [ARCHITECTURE.md](../ARCHITECTURE.md): InferenceEngine component role.
