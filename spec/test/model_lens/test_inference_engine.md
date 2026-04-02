# Test Specification: `test/model_lens/test_inference_engine.md`

## Source File Under Test

`src/model_lens/inference_engine.py`

## Test File

`test/model_lens/test_inference_engine.py`

## Imports Required

```python
import threading
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from model_lens.exceptions import ConfigurationError, OperationError
from model_lens.inference_engine import YOLOInferenceEngine
```

---

## Shared Fixture: `engine_with_mock_model`

A pytest fixture that constructs a ready-to-use `YOLOInferenceEngine` by patching
`ultralytics.YOLO` to return a mock YOLO model. The mock model's `names` attribute is set to a
small label map (e.g. `{0: "person", 1: "bicycle", 2: "car"}`), and its `__call__` is configured
to return empty results by default. Used across sections 4–7.

---

## 1. `YOLOInferenceEngine` — Constructor: `confidence_threshold` Validation

### 1.1 Validation Failures

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_confidence_threshold_zero_raises` | `unit` | `confidence_threshold=0.0` violates `0.0 < value` constraint | `confidence_threshold=0.0` | raises `ConfigurationError` |
| `test_confidence_threshold_negative_raises` | `unit` | Negative `confidence_threshold` raises `ConfigurationError` | `confidence_threshold=-0.1` | raises `ConfigurationError` |
| `test_confidence_threshold_above_one_raises` | `unit` | `confidence_threshold > 1.0` raises `ConfigurationError` | `confidence_threshold=1.001` | raises `ConfigurationError` |
| `test_confidence_threshold_at_upper_boundary` | `unit` | `confidence_threshold=1.0` is valid | `confidence_threshold=1.0` | No exception raised |
| `test_confidence_threshold_just_above_zero` | `unit` | `confidence_threshold` just above `0.0` is valid | `confidence_threshold=1e-9` | No exception raised |

---

## 2. `YOLOInferenceEngine` — Constructor: Model Loading

> All tests in this section patch `ultralytics.YOLO` to control model-load behaviour.

### 2.1 Happy Path

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_model_loads_successfully` | `unit` | A valid `model` string constructs without error | `model="yolov8n.pt"`; `YOLO` patched to return a mock with `names={0: "person"}` | No exception raised |

### 2.2 Validation Failures

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_model_load_failure` | `unit` | `YOLO()` raising an exception wraps as `OperationError` | `YOLO` patched to raise `Exception` | raises `OperationError` |

---

## 3. `YOLOInferenceEngine.detect()` — Happy Path

### 3.1 Happy Path — detect()

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_detect_returns_list` | `unit` | `detect()` always returns a list | Mock model returns empty output | `isinstance(result, list) is True` |
| `test_detect_empty_when_no_detections` | `unit` | No detections above threshold returns empty list | Mock model returns no raw detections | `result == []` |
| `test_detect_single_result_fields` | `unit` | A single detection above threshold produces one `DetectionResult` with correct fields | Mock model returns one detection: index `0`, confidence `0.9`, raw pixel box `[64.0, 96.0, 256.0, 288.0]`; frame is 640×480 | `result[0].label == "person"`, `result[0].confidence == 0.9`, `result[0].bounding_box == [0.1, 0.2, 0.4, 0.6]` (normalised) |
| `test_detect_bounding_box_is_normalised` | `unit` | `bounding_box` values in `DetectionResult` are normalised to `[0.0, 1.0]` by dividing xyxy pixel coords by frame width/height | Frame 400×200 (`w=400, h=200`); raw pixel box `[40.0, 20.0, 200.0, 100.0]` | `result[0].bounding_box == pytest.approx([0.1, 0.1, 0.5, 0.5])` |
| `test_detect_is_target_true` | `unit` | `is_target` is `True` when label is in `target_labels` | `target_labels=["person"]`; mock returns detection with label index `0` (`"person"`) | `result[0].is_target is True` |
| `test_detect_is_target_false` | `unit` | `is_target` is `False` when label is not in `target_labels` | `target_labels=[]`; mock returns detection with label index `0` (`"person"`) | `result[0].is_target is False` |
| `test_detect_does_not_mutate_frame` | `unit` | `detect()` does not modify the input frame array | Pass a `numpy.ndarray` frame; record a copy before the call; call `detect()`; compare after | `numpy.array_equal(frame_before, frame_after) is True` |
| `test_detect_does_not_mutate_target_labels` | `unit` | `detect()` does not modify the `target_labels` list | Pass a `list[str]` as `target_labels`; record a copy before the call; call `detect()`; compare after | `target_labels` equals its pre-call copy |

### 3.2 Boundary Values — `confidence_threshold`

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_detect_filters_below_threshold` | `unit` | Detection with confidence strictly below threshold is excluded | `confidence_threshold=0.5`; mock returns detection with confidence `0.49` | `result == []` |
| `test_detect_keeps_at_threshold` | `unit` | Detection with confidence exactly equal to threshold is kept | `confidence_threshold=0.5`; mock returns detection with confidence `0.5` | `len(result) == 1` |
| `test_detect_keeps_above_threshold` | `unit` | Detection with confidence above threshold is kept | `confidence_threshold=0.5`; mock returns detection with confidence `0.51` | `len(result) == 1` |

### 3.3 Ordering — Descending Confidence

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_detect_results_ordered_by_descending_confidence` | `unit` | Multiple detections are returned in descending confidence order | Mock returns three detections with confidences `0.6`, `0.9`, `0.75` (in that raw order) | `result[0].confidence == 0.9`, `result[1].confidence == 0.75`, `result[2].confidence == 0.6` |
| `test_detect_equal_confidence_both_present` | `unit` | Two detections with identical confidence are both present in the result (order not asserted) | Mock returns two detections both with confidence `0.8` | `len(result) == 2`; both confidences are `0.8` |

---

## 4. `YOLOInferenceEngine.detect()` — Validation Failures

### 4.1 Error Propagation

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_detect_inference_runtime_failure_raises_operation_error` | `unit` | An unexpected exception from the model's `__call__` raises `OperationError` | Mock model `__call__` raises `RuntimeError` | raises `OperationError` |
| `test_detect_inference_with_no_nn_module_raises_operation_error` | `unit` | Try inferencing while `_model` attribute is `None` | Set `engine._model = None` then call `detect()` | raises `OperationError` |

---

## 5. `YOLOInferenceEngine.detect()` — Thread Safety (Simulated)

> Thread safety is verified by simulating concurrent access using `unittest.mock` and
> `threading.Lock` introspection rather than spawning real threads. The goal is to confirm that
> the lock is acquired and released on every call path, including exception paths.

### 5.1 Concurrent Behaviour

| Test ID | Category | Description | Expected |
|---|---|---|---|
| `test_detect_acquires_lock_on_success` | `race` | The per-instance lock is acquired (and released) during a successful `detect()` call | Patch the engine's internal lock with a `MagicMock`; call `detect()`; assert `lock.__enter__` was called once |
| `test_detect_acquires_lock_on_exception` | `race` | The per-instance lock is acquired (and released) even when `detect()` raises | Patch the engine's internal lock with a `MagicMock`; configure mock model to raise; call `detect()` inside `pytest.raises`; assert `lock.__enter__` was called once |

---

## 6. `YOLOInferenceEngine.teardown()` — Resource Release

> All tests construct a `YOLOInferenceEngine` via the shared `engine_with_mock_model` fixture
> unless stated otherwise.

### 6.1 Happy Path

| Test ID | Category | Description | Expected |
|---|---|---|---|
| `test_teardown_sets_model_to_none` | `unit` | After `teardown()`, the internal `_model` attribute is `None` | `engine._model is None` |
| `test_teardown_is_idempotent` | `unit` | Calling `teardown()` twice does not raise | Second call completes without exception |

### 6.2 Error Propagation

| Test ID | Category | Description | Expected |
|---|---|---|---|
| `test_detect_after_teardown_raises_operation_error` | `unit` | `detect()` called after `teardown()` raises `OperationError` | raises `OperationError` |
| `test_get_label_map_after_teardown_raises_operation_error` | `unit` | `get_label_map()` called after `teardown()` raises `OperationError` | raises `OperationError` |

### 6.3 Concurrent Behaviour

| Test ID | Category | Description | Expected |
|---|---|---|---|
| `test_teardown_acquires_lock` | `race` | `teardown()` acquires (and releases) the per-instance lock | Patch the engine's `_lock` with a `MagicMock`; call `teardown()`; assert `lock.__enter__` was called once |

---

## 7. `YOLOInferenceEngine.get_label_map()` — Label Map Access

### 7.1 Happy Path

| Test ID | Category | Description | Expected |
|---|---|---|---|
| `test_get_label_map_returns_copy` | `unit` | `get_label_map()` returns a copy of the internal label map; mutating the return value does not affect the engine | Call `get_label_map()`, mutate the returned dict, call again — result is unchanged |
| `test_get_label_map_matches_model_names` | `unit` | Label map matches the mock model's `names` attribute | `engine.get_label_map() == mock_model.names` |

### 7.2 Error Propagation

| Test ID | Category | Description | Expected |
|---|---|---|---|
| `test_get_label_map_with_no_model_loaded` | `unit` | `get_label_map()` called while `_model` is `None` raises `OperationError` | raises `OperationError` |

---

## Summary Table

| Entity | Test Count (approx.) | unit | e2e | race | Key Concerns |
|---|---|---|---|---|---|
| `YOLOInferenceEngine.__init__` (confidence_threshold) | 5 | 5 | 0 | 0 | zero, negative, above one, upper boundary, just above zero |
| `YOLOInferenceEngine.__init__` (model loading) | 2 | 2 | 0 | 0 | successful load, load failure → OperationError |
| `YOLOInferenceEngine.detect()` (happy path) | 8 | 8 | 0 | 0 | return type, empty result, field correctness, bounding_box normalised, is_target true/false, frame not mutated, target_labels not mutated |
| `YOLOInferenceEngine.detect()` (threshold filtering) | 3 | 3 | 0 | 0 | below, at, above threshold |
| `YOLOInferenceEngine.detect()` (ordering) | 2 | 2 | 0 | 0 | descending order, equal confidence both present |
| `YOLOInferenceEngine.detect()` (error propagation) | 2 | 2 | 0 | 0 | runtime failure → OperationError, None model → OperationError |
| `YOLOInferenceEngine.detect()` (thread safety) | 2 | 0 | 0 | 2 | lock acquired on success, lock acquired on exception |
| `YOLOInferenceEngine.teardown()` | 4 | 3 | 0 | 1 | model cleared, idempotent, detect-after-teardown → OperationError, lock acquired |
| `YOLOInferenceEngine.get_label_map()` | 3 | 3 | 0 | 0 | returns copy, matches model names, raises after teardown |
