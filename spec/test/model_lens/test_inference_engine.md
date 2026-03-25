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

### 1.1 Happy Path — Label Map Construction

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_label_map_single_label` | A file with one non-blank line produces a single-entry map | File: `"person\n"` | Internal label map is `{0: "person"}` |
| `test_label_map_multiple_labels` | Multiple non-blank lines are indexed sequentially from 0 | File: `"person\nbicycle\ncar\n"` | Internal label map is `{0: "person", 1: "bicycle", 2: "car"}` |
| `test_label_map_blank_line_consumes_index` | A blank line in the middle consumes an index slot and is stored as `""` | File: `"person\nbicycle\n\nmotorcycle\n"` | Internal label map is `{0: "person", 1: "bicycle", 2: "", 3: "motorcycle"}` |
| `test_label_map_leading_trailing_whitespace_stripped` | Leading and trailing whitespace on non-blank lines is stripped | File: `"  person  \n  bicycle\n"` | Internal label map is `{0: "person", 1: "bicycle"}` |
| `test_label_map_whitespace_only_line_stored_as_empty_string` | A whitespace-only line is stored as `""` | File: `"person\n   \ncar\n"` | Internal label map is `{0: "person", 1: "", 2: "car"}` |
| `test_label_map_no_trailing_newline` | A file without a trailing newline is parsed correctly | File: `"person\nbicycle"` (no trailing newline) | Internal label map is `{0: "person", 1: "bicycle"}` |

### 1.2 Validation Failures — Label Map

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_label_map_file_not_found` | A non-existent `labels_path` raises `ConfigurationError` | `labels_path="/nonexistent/labels.txt"` | raises `ConfigurationError` |
| `test_label_map_empty_file` | A completely empty file (zero bytes) raises `ParseError` | File: `""` (empty) | raises `ParseError` |
| `test_label_map_only_blank_lines` | A file containing only blank lines raises `ParseError` | File: `"\n\n\n"` | raises `ParseError` |

---

## 2. `TorchInferenceEngine` — Constructor: Model Loading

> All tests in this section write a real label map file to `tmp_path`. `torch.load` is patched
> unless the test specifically targets PyTorch load failure.

### 2.1 Happy Path — Model Loading

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_model_loads_successfully` | A valid `model_path` pointing to an existing file constructs without error | `model_path` points to a real file in `tmp_path`; `torch.load` patched to return a mock | No exception raised |

### 2.2 Validation Failures — Model Path

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_model_path_not_found` | A non-existent `model_path` raises `ConfigurationError` | `model_path="/nonexistent/model.pt"` | raises `ConfigurationError` |
| `test_model_load_failure` | An existing file that PyTorch cannot load raises `OperationError` | `model_path` points to a real file; `torch.load` patched to raise `Exception` | raises `OperationError` |

### 2.3 Validation Failures — `confidence_threshold`

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_confidence_threshold_zero_raises` | `confidence_threshold=0.0` violates `0.0 < value` constraint | `confidence_threshold=0.0` | raises `ConfigurationError` |
| `test_confidence_threshold_negative_raises` | Negative `confidence_threshold` raises `ConfigurationError` | `confidence_threshold=-0.1` | raises `ConfigurationError` |
| `test_confidence_threshold_above_one_raises` | `confidence_threshold > 1.0` raises `ConfigurationError` | `confidence_threshold=1.001` | raises `ConfigurationError` |
| `test_confidence_threshold_at_upper_boundary` | `confidence_threshold=1.0` is valid | `confidence_threshold=1.0` | No exception raised |
| `test_confidence_threshold_just_above_zero` | `confidence_threshold` just above `0.0` is valid | `confidence_threshold=1e-9` | No exception raised |

---

## 3. `TorchInferenceEngine` — Constructor: Package-Data Fallback

> All tests in this section patch `importlib.resources` (or the internal resolution helper) to
> simulate success and failure. No real package-data files are required.

### 3.1 Happy Path — Fallback Resolution

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_empty_model_path_uses_package_data` | `model_path=""` triggers package-data resolution; succeeds when resource is found | `model_path=""`; `importlib.resources` patched to return a valid path; `torch.load` patched | No exception raised |
| `test_empty_labels_path_uses_package_data` | `labels_path=""` triggers package-data resolution; succeeds when resource is found | `labels_path=""`; `importlib.resources` patched to return a valid path pointing to a real label map file in `tmp_path` | No exception raised |

### 3.2 Validation Failures — Fallback Resolution

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_empty_model_path_package_data_missing` | `model_path=""` and package-data resource cannot be resolved raises `ConfigurationError` | `model_path=""`; `importlib.resources` patched to raise | raises `ConfigurationError` |
| `test_empty_labels_path_package_data_missing` | `labels_path=""` and package-data resource cannot be resolved raises `ConfigurationError` | `labels_path=""`; `importlib.resources` patched to raise | raises `ConfigurationError` |

---

## 4. `TorchInferenceEngine.detect()` — Happy Path

> All tests in this section construct a `TorchInferenceEngine` with a patched `torch.load` that
> returns a mock model. The mock model's `__call__` is configured to return controlled raw output
> so that `detect()` behaviour can be verified deterministically.
>
> A shared pytest fixture (`engine_with_mock_model`) is recommended to reduce boilerplate: it
> writes a label map to `tmp_path`, creates a dummy model file, patches `torch.load`, and returns
> a ready-to-use `TorchInferenceEngine` instance.

### 4.1 Happy Path — Basic Detection

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_detect_returns_list` | `detect()` always returns a list | Mock model returns empty output | `isinstance(result, list) is True` |
| `test_detect_empty_when_no_detections` | No detections above threshold returns empty list | Mock model returns no raw detections | `result == []` |
| `test_detect_single_result_fields` | A single detection above threshold produces one `DetectionResult` with correct fields | Mock model returns one detection: index `0`, confidence `0.9`, box `(0.1, 0.2, 0.4, 0.6)` | `result[0].label == "person"`, `result[0].confidence == 0.9`, `result[0].bounding_box == (0.1, 0.2, 0.4, 0.6)` |
| `test_detect_is_target_true` | `is_target` is `True` when label is in `target_labels` | `target_labels=["person"]`; mock returns detection with label index `0` (`"person"`) | `result[0].is_target is True` |
| `test_detect_is_target_false` | `is_target` is `False` when label is not in `target_labels` | `target_labels=[]`; mock returns detection with label index `0` (`"person"`) | `result[0].is_target is False` |

### 4.2 Boundary Values — `confidence_threshold` Filtering

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_detect_filters_below_threshold` | Detection with confidence strictly below threshold is excluded | `confidence_threshold=0.5`; mock returns detection with confidence `0.49` | `result == []` |
| `test_detect_keeps_at_threshold` | Detection with confidence exactly equal to threshold is kept | `confidence_threshold=0.5`; mock returns detection with confidence `0.5` | `len(result) == 1` |
| `test_detect_keeps_above_threshold` | Detection with confidence above threshold is kept | `confidence_threshold=0.5`; mock returns detection with confidence `0.51` | `len(result) == 1` |

### 4.3 Ordering — Descending Confidence

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_detect_results_ordered_by_descending_confidence` | Multiple detections are returned in descending confidence order | Mock returns three detections with confidences `0.6`, `0.9`, `0.75` (in that raw order) | `result[0].confidence == 0.9`, `result[1].confidence == 0.75`, `result[2].confidence == 0.6` |
| `test_detect_equal_confidence_both_present` | Two detections with identical confidence are both present in the result (order not asserted) | Mock returns two detections both with confidence `0.8` | `len(result) == 2`; both confidences are `0.8` |

---

## 5. `TorchInferenceEngine.detect()` — Validation Failures

### 5.1 Label Map Index Miss

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_detect_unknown_label_index_raises_parse_error` | A raw model output index with no entry in the label map raises `ParseError` | Mock returns detection with index `999`; label map has only indices `0`–`2` | raises `ParseError` |

### 5.2 Runtime Inference Failure

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_detect_inference_runtime_failure_raises_operation_error` | An unexpected exception from the model's `__call__` raises `OperationError` | Mock model `__call__` raises `RuntimeError` | raises `OperationError` |

---

## 6. `TorchInferenceEngine.detect()` — Thread Safety (Simulated)

> Thread safety is verified by simulating concurrent access using `unittest.mock` and
> `threading.Lock` introspection rather than spawning real threads. The goal is to confirm that
> the lock is acquired and released on every call path, including exception paths.

### 6.1 Lock Acquisition

| Test ID | Description | Expected |
|---|---|---|
| `test_detect_acquires_lock_on_success` | The per-instance lock is acquired (and released) during a successful `detect()` call | Patch the engine's internal lock with a `MagicMock`; call `detect()`; assert `lock.__enter__` was called once |
| `test_detect_acquires_lock_on_exception` | The per-instance lock is acquired (and released) even when `detect()` raises | Patch the engine's internal lock with a `MagicMock`; configure mock model to raise; call `detect()` inside `pytest.raises`; assert `lock.__enter__` was called once |

---

## Summary Table

| Entity | Test Count (approx.) | Key Concerns |
|---|---|---|
| `TorchInferenceEngine.__init__` (label map) | 9 | sequential indexing, blank line slot consumption, whitespace stripping, missing file, empty file, all-blank file |
| `TorchInferenceEngine.__init__` (model) | 3 | successful load, missing file, corrupt file |
| `TorchInferenceEngine.__init__` (confidence_threshold) | 5 | zero, negative, above one, upper boundary, just above zero |
| `TorchInferenceEngine.__init__` (package-data fallback) | 4 | empty model path success/failure, empty labels path success/failure |
| `TorchInferenceEngine.detect()` (happy path) | 5 | return type, empty result, field correctness, is_target true/false |
| `TorchInferenceEngine.detect()` (threshold filtering) | 3 | below, at, above threshold |
| `TorchInferenceEngine.detect()` (ordering) | 2 | descending order, equal confidence both present |
| `TorchInferenceEngine.detect()` (failures) | 2 | unknown index → ParseError, runtime failure → OperationError |
| `TorchInferenceEngine.detect()` (thread safety) | 2 | lock acquired on success, lock acquired on exception |
