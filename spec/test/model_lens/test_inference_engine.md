# Test Specification: `test/model_lens/test_inference_engine.md`

## Source File Under Test

`src/model_lens/inference_engine.py`

## Test File

`test/model_lens/test_inference_engine.py`

## Imports Required

```python
import os
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from model_lens.exceptions import ConfigurationError, OperationError, ParseError
from model_lens.inference_engine import TorchInferenceEngine
```

---

## 1. `TorchInferenceEngine` — Constructor: Label Map Loading

> All tests in this section write real label map files to `tmp_path` and call `os.chdir(tmp_path)`
> so that relative paths resolve correctly. `model_path` is stubbed to a valid dummy `.pt` file
> (created in `tmp_path`) and `torch.load` is patched to return a mock model, so that label map
> tests are not blocked by PyTorch.

### 1.1 Happy Path — Construction

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_label_map_single_label` | `unit` | A file with one non-blank line produces a single-entry map | File: `"person\n"` | Internal label map is `{0: "person"}` |
| `test_label_map_multiple_labels` | `unit` | Multiple non-blank lines are indexed sequentially from 0 | File: `"person\nbicycle\ncar\n"` | Internal label map is `{0: "person", 1: "bicycle", 2: "car"}` |
| `test_label_map_blank_line_consumes_index` | `unit` | A blank line in the middle consumes an index slot and is stored as `""` | File: `"person\nbicycle\n\nmotorcycle\n"` | Internal label map is `{0: "person", 1: "bicycle", 2: "", 3: "motorcycle"}` |
| `test_label_map_leading_trailing_whitespace_stripped` | `unit` | Leading and trailing whitespace on non-blank lines is stripped | File: `"  person  \n  bicycle\n"` | Internal label map is `{0: "person", 1: "bicycle"}` |
| `test_label_map_whitespace_only_line_stored_as_empty_string` | `unit` | A whitespace-only line is stored as `""` | File: `"person\n   \ncar\n"` | Internal label map is `{0: "person", 1: "", 2: "car"}` |
| `test_label_map_no_trailing_newline` | `unit` | A file without a trailing newline is parsed correctly | File: `"person\nbicycle"` (no trailing newline) | Internal label map is `{0: "person", 1: "bicycle"}` |

### 1.2 Validation Failures — `labels_path`

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_label_map_file_not_found` | `unit` | A non-existent `labels_path` raises `ConfigurationError` | `labels_path="/nonexistent/labels.txt"` | raises `ConfigurationError` |
| `test_label_map_empty_file` | `unit` | A completely empty file (zero bytes) raises `ParseError` | File: `""` (empty) | raises `ParseError` |
| `test_label_map_only_blank_lines` | `unit` | A file containing only blank lines raises `ParseError` | File: `"\n\n\n"` | raises `ParseError` |

### 1.3 Validation Failures — Label Map Loading

> These tests verify that the base class label map loader rejects a missing
> or unreadable file with the correct exception type.

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_inference_engine_label_map_file_not_found_raises_configuration_error` | `unit` | Raises `ConfigurationError` when the label map file does not exist | `labels_path` points to a non-existent file | raises `ConfigurationError` |
| `test_inference_engine_label_map_file_unreadable_raises_configuration_error` | `unit` | Raises `ConfigurationError` when the label map file exists but cannot be read | `labels_path` points to an unreadable file | raises `ConfigurationError` |

### 1.4 Error Propagation — Package-Data Fallback

> Verifies that a failure to resolve a package-data resource surfaces as
> `ConfigurationError` at the constructor call site.

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_torch_inference_engine_package_data_resolves_successfully` | `unit` | Constructor succeeds when `labels_path` is empty and package-data resource is present | `labels_path=""` with package data available | engine constructed without raising |
| `test_torch_inference_engine_package_data_unresolvable_raises_configuration_error` | `unit` | Raises `ConfigurationError` when the package-data resource cannot be located | `model_path=""` or `labels_path=""` with package data absent | raises `ConfigurationError` |

---

## 2. `TorchInferenceEngine` — Constructor: Model Loading

> All tests in this section write a real label map file to `tmp_path`. `torch.load` is patched
> unless the test specifically targets PyTorch load failure.

### 2.1 Happy Path — Construction

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_model_loads_successfully` | `unit` | A valid `model_path` pointing to an existing file constructs without error | `model_path` points to a real file in `tmp_path`; `torch.load` patched to return a mock | No exception raised |

### 2.2 Validation Failures — `model_path`

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_model_path_not_found` | `unit` | A non-existent `model_path` raises `ConfigurationError` | `model_path="/nonexistent/model.pt"` | raises `ConfigurationError` |
| `test_model_load_failure` | `unit` | An existing file that PyTorch cannot load raises `OperationError` | `model_path` points to a real file; `torch.load` patched to raise `Exception` | raises `OperationError` |

### 2.3 Validation Failures — `confidence_threshold`

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_confidence_threshold_zero_raises` | `unit` | `confidence_threshold=0.0` violates `0.0 < value` constraint | `confidence_threshold=0.0` | raises `ConfigurationError` |
| `test_confidence_threshold_negative_raises` | `unit` | Negative `confidence_threshold` raises `ConfigurationError` | `confidence_threshold=-0.1` | raises `ConfigurationError` |
| `test_confidence_threshold_above_one_raises` | `unit` | `confidence_threshold > 1.0` raises `ConfigurationError` | `confidence_threshold=1.001` | raises `ConfigurationError` |
| `test_confidence_threshold_at_upper_boundary` | `unit` | `confidence_threshold=1.0` is valid | `confidence_threshold=1.0` | No exception raised |
| `test_confidence_threshold_just_above_zero` | `unit` | `confidence_threshold` just above `0.0` is valid | `confidence_threshold=1e-9` | No exception raised |

---

## 3. `TorchInferenceEngine` — Constructor: Package-Data Fallback

> All tests in this section patch `importlib.resources` (or the internal resolution helper) to
> simulate success and failure. No real package-data files are required.

### 3.1 Happy Path — Construction

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_empty_model_path_uses_package_data` | `unit` | `model_path=""` triggers package-data resolution; succeeds when resource is found | `model_path=""`; `importlib.resources` patched to return a valid path; `torch.load` patched | No exception raised |
| `test_empty_labels_path_uses_package_data` | `unit` | `labels_path=""` triggers package-data resolution; succeeds when resource is found | `labels_path=""`; `importlib.resources` patched to return a valid path pointing to a real label map file in `tmp_path` | No exception raised |

### 3.2 Validation Failures

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_empty_model_path_package_data_missing` | `unit` | `model_path=""` and package-data resource cannot be resolved raises `ConfigurationError` | `model_path=""`; `importlib.resources` patched to raise | raises `ConfigurationError` |
| `test_empty_labels_path_package_data_missing` | `unit` | `labels_path=""` and package-data resource cannot be resolved raises `ConfigurationError` | `labels_path=""`; `importlib.resources` patched to raise | raises `ConfigurationError` |

---

## 4. `TorchInferenceEngine.detect()` — Happy Path

> All tests in this section construct a `TorchInferenceEngine` with a patched `torch.load` that
> returns a mock model. The mock model's `__call__` is configured to return controlled raw output
> so that `detect()` behaviour can be verified deterministically.
>
> A shared pytest fixture (`engine_with_mock_model`) is recommended to reduce boilerplate: it
> writes a label map to `tmp_path`, creates a dummy model file, patches `torch.load`, and returns
> a ready-to-use `TorchInferenceEngine` instance.

### 4.1 Happy Path — `detect()`

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_detect_returns_list` | `unit` | `detect()` always returns a list | Mock model returns empty output | `isinstance(result, list) is True` |
| `test_detect_empty_when_no_detections` | `unit` | No detections above threshold returns empty list | Mock model returns no raw detections | `result == []` |
| `test_detect_single_result_fields` | `unit` | A single detection above threshold produces one `DetectionResult` with correct fields | Mock model returns one detection: index `0`, confidence `0.9`, box `(0.1, 0.2, 0.4, 0.6)` | `result[0].label == "person"`, `result[0].confidence == 0.9`, `result[0].bounding_box == (0.1, 0.2, 0.4, 0.6)` |
| `test_detect_is_target_true` | `unit` | `is_target` is `True` when label is in `target_labels` | `target_labels=["person"]`; mock returns detection with label index `0` (`"person"`) | `result[0].is_target is True` |
| `test_detect_is_target_false` | `unit` | `is_target` is `False` when label is not in `target_labels` | `target_labels=[]`; mock returns detection with label index `0` (`"person"`) | `result[0].is_target is False` |
| `test_detect_does_not_mutate_frame` | `unit` | `detect()` does not modify the input frame array | Pass a `numpy.ndarray` frame; record a copy before the call; call `detect()`; compare after | `numpy.array_equal(frame_before, frame_after) is True` |
| `test_detect_does_not_mutate_target_labels` | `unit` | `detect()` does not modify the `target_labels` list | Pass a `list[str]` as `target_labels`; record a copy before the call; call `detect()`; compare after | `target_labels` equals its pre-call copy |

### 4.2 Boundary Values — `confidence_threshold`

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_detect_filters_below_threshold` | `unit` | Detection with confidence strictly below threshold is excluded | `confidence_threshold=0.5`; mock returns detection with confidence `0.49` | `result == []` |
| `test_detect_keeps_at_threshold` | `unit` | Detection with confidence exactly equal to threshold is kept | `confidence_threshold=0.5`; mock returns detection with confidence `0.5` | `len(result) == 1` |
| `test_detect_keeps_above_threshold` | `unit` | Detection with confidence above threshold is kept | `confidence_threshold=0.5`; mock returns detection with confidence `0.51` | `len(result) == 1` |

### 4.3 Ordering — Descending Confidence

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_detect_results_ordered_by_descending_confidence` | `unit` | Multiple detections are returned in descending confidence order | Mock returns three detections with confidences `0.6`, `0.9`, `0.75` (in that raw order) | `result[0].confidence == 0.9`, `result[1].confidence == 0.75`, `result[2].confidence == 0.6` |
| `test_detect_equal_confidence_both_present` | `unit` | Two detections with identical confidence are both present in the result (order not asserted) | Mock returns two detections both with confidence `0.8` | `len(result) == 2`; both confidences are `0.8` |

---

## 5. `TorchInferenceEngine.detect()` — Validation Failures

### 5.1 Error Propagation

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_detect_unknown_label_index_raises_parse_error` | `unit` | A raw model output index with no entry in the label map raises `ParseError` | Mock returns detection with index `999`; label map has only indices `0`–2 | raises `ParseError` |
| `test_detect_inference_runtime_failure_raises_operation_error` | `unit` | An unexpected exception from the model's `__call__` raises `OperationError` | Mock model `__call__` raises `RuntimeError` | raises `OperationError` |

---

## 6. `TorchInferenceEngine.detect()` — Thread Safety (Simulated)

> Thread safety is verified by simulating concurrent access using `unittest.mock` and
> `threading.Lock` introspection rather than spawning real threads. The goal is to confirm that
> the lock is acquired and released on every call path, including exception paths.

### 6.1 Concurrent Behaviour

| Test ID | Category | Description | Expected |
|---|---|---|---|
| `test_detect_acquires_lock_on_success` | `race` | The per-instance lock is acquired (and released) during a successful `detect()` call | Patch the engine's internal lock with a `MagicMock`; call `detect()`; assert `lock.__enter__` was called once |
| `test_detect_acquires_lock_on_exception` | `race` | The per-instance lock is acquired (and released) even when `detect()` raises | Patch the engine's internal lock with a `MagicMock`; configure mock model to raise; call `detect()` inside `pytest.raises`; assert `lock.__enter__` was called once |

---

---

## 7. `TorchInferenceEngine.teardown()` — Resource Release

> All tests construct a `TorchInferenceEngine` via the shared `engine_with_mock_model` fixture
> unless stated otherwise.

### 7.1 Happy Path

| Test ID | Category | Description | Expected |
|---|---|---|---|
| `test_teardown_sets_model_to_none` | `unit` | After `teardown()`, the internal `_model` attribute is `None` | `engine._model is None` |
| `test_teardown_clears_label_map` | `unit` | After `teardown()`, the internal `_label_map` is empty | `engine._label_map == {}` |
| `test_teardown_is_idempotent` | `unit` | Calling `teardown()` twice does not raise | Second call completes without exception |

### 7.2 Post-Teardown Behaviour

| Test ID | Category | Description | Expected |
|---|---|---|---|
| `test_detect_after_teardown_raises_operation_error` | `unit` | `detect()` called after `teardown()` raises `OperationError` | `raises OperationError` |

### 7.3 Thread Safety (Simulated)

| Test ID | Category | Description | Expected |
|---|---|---|---|
| `test_teardown_acquires_lock` | `race` | `teardown()` acquires (and releases) the per-instance lock | Patch the engine's `_lock` with a `MagicMock`; call `teardown()`; assert `lock.__enter__` was called once |

---

## Summary Table

| Entity | Test Count (approx.) | unit | e2e | race | Key Concerns |
|---|---|---|---|---|---|
| `TorchInferenceEngine.__init__` (label map) | 13 | 13 | 0 | 0 | sequential indexing, blank line slot consumption, whitespace stripping, missing file, empty file, all-blank file, unreadable file, package-data success, package-data unresolvable |
| `TorchInferenceEngine.__init__` (model) | 3 | 3 | 0 | 0 | successful load, missing file, corrupt file |
| `TorchInferenceEngine.__init__` (confidence_threshold) | 5 | 5 | 0 | 0 | zero, negative, above one, upper boundary, just above zero |
| `TorchInferenceEngine.__init__` (package-data fallback) | 4 | 4 | 0 | 0 | empty model path success/failure, empty labels path success/failure |
| `TorchInferenceEngine.detect()` (happy path) | 7 | 7 | 0 | 0 | return type, empty result, field correctness, is_target true/false, frame not mutated, target_labels not mutated |
| `TorchInferenceEngine.detect()` (threshold filtering) | 3 | 3 | 0 | 0 | below, at, above threshold |
| `TorchInferenceEngine.detect()` (ordering) | 2 | 2 | 0 | 0 | descending order, equal confidence both present |
| `TorchInferenceEngine.detect()` (error propagation) | 2 | 2 | 0 | 0 | unknown index → ParseError, runtime failure → OperationError |
| `TorchInferenceEngine.detect()` (thread safety) | 2 | 0 | 0 | 2 | lock acquired on success, lock acquired on exception |
| `TorchInferenceEngine.teardown()` | 5 | 4 | 0 | 1 | model cleared, label map cleared, idempotent, detect-after-teardown → OperationError, lock acquired |
