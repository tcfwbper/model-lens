# Test Specification: `test/model_lens/test_entities.md`

## Source File Under Test

`src/model_lens/entities.py`

## Test File

`test/model_lens/test_entities.py`

## Imports Required

```python
from model_lens.entities import (
    CameraConfig,
    DetectionResult,
    Frame,
    LocalCameraConfig,
    RtspCameraConfig,
    RuntimeConfig,
)
from model_lens.exceptions import ValidationError
import numpy as np
import time
```

---

## 1. `LocalCameraConfig`

### 1.1 Happy Path — Construction

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_local_camera_config_default_device_index` | Default `device_index` is `0` | `LocalCameraConfig()` | `instance.device_index == 0` |
| `test_local_camera_config_explicit_device_index` | Explicit positive `device_index` is stored | `LocalCameraConfig(device_index=2)` | `instance.device_index == 2` |
| `test_local_camera_config_zero_device_index` | `device_index=0` is the boundary minimum and is valid | `LocalCameraConfig(device_index=0)` | `instance.device_index == 0` |

### 1.2 Validation Failures

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_local_camera_config_negative_device_index` | Negative `device_index` raises `ValidationError` | `LocalCameraConfig(device_index=-1)` | raises `model_lens.exceptions.ValidationError` |

### 1.3 Immutability

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_local_camera_config_is_frozen` | Assigning to any field after construction raises `FrozenInstanceError` | `instance.device_index = 1` on a constructed instance | raises `dataclasses.FrozenInstanceError` (or `AttributeError`) |

### 1.4 Type Hierarchy

| Test ID | Description | Expected |
|---|---|---|
| `test_local_camera_config_is_camera_config` | `LocalCameraConfig` is a subclass of `CameraConfig` | `isinstance(LocalCameraConfig(), CameraConfig) is True` |

---

## 2. `RtspCameraConfig`

### 2.1 Happy Path — Construction

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_rtsp_camera_config_stores_url` | A valid RTSP URL is stored correctly | `RtspCameraConfig(rtsp_url="rtsp://192.168.1.10/stream")` | `instance.rtsp_url == "rtsp://192.168.1.10/stream"` |

### 2.2 Validation Failures

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_rtsp_camera_config_empty_url` | Empty string `rtsp_url` raises `ValidationError` | `RtspCameraConfig(rtsp_url="")` | raises `model_lens.exceptions.ValidationError` |

### 2.3 Immutability

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_rtsp_camera_config_is_frozen` | Assigning to any field after construction raises `FrozenInstanceError` | `instance.rtsp_url = "rtsp://other"` on a constructed instance | raises `dataclasses.FrozenInstanceError` (or `AttributeError`) |

### 2.4 Type Hierarchy

| Test ID | Description | Expected |
|---|---|---|
| `test_rtsp_camera_config_is_camera_config` | `RtspCameraConfig` is a subclass of `CameraConfig` | `isinstance(RtspCameraConfig(rtsp_url="rtsp://x"), CameraConfig) is True` |

---

## 3. `CameraConfig`

### 3.1 Abstract Base — Cannot Be Instantiated

| Test ID | Description | Expected |
|---|---|---|
| `test_camera_config_cannot_be_instantiated` | Directly instantiating `CameraConfig` raises `TypeError` | `CameraConfig()` raises `TypeError` |

---

## 4. `RuntimeConfig`

### 4.1 Happy Path — Default Construction

| Test ID | Description | Expected |
|---|---|---|
| `test_runtime_config_default_camera` | Default `camera` is `LocalCameraConfig(device_index=0)` | `isinstance(instance.camera, LocalCameraConfig)` and `instance.camera.device_index == 0` |
| `test_runtime_config_default_target_labels` | Default `target_labels` is an empty list | `instance.target_labels == []` |
| `test_runtime_config_default_confidence_threshold` | Default `confidence_threshold` is `0.5` | `instance.confidence_threshold == 0.5` |

### 4.2 Happy Path — Explicit Construction

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_runtime_config_explicit_local_camera` | Accepts a `LocalCameraConfig` | `RuntimeConfig(camera=LocalCameraConfig(device_index=1), ...)` | `instance.camera.device_index == 1` |
| `test_runtime_config_explicit_rtsp_camera` | Accepts an `RtspCameraConfig` | `RuntimeConfig(camera=RtspCameraConfig(rtsp_url="rtsp://x"), ...)` | `instance.camera.rtsp_url == "rtsp://x"` |
| `test_runtime_config_explicit_target_labels` | Stores a non-empty target labels list | `RuntimeConfig(target_labels=["cat", "dog"], ...)` | `instance.target_labels == ["cat", "dog"]` |
| `test_runtime_config_explicit_confidence_threshold` | Stores a custom confidence threshold | `RuntimeConfig(confidence_threshold=0.75, ...)` | `instance.confidence_threshold == 0.75` |

### 4.3 Immutability

| Test ID | Description | Expected |
|---|---|---|
| `test_runtime_config_is_frozen` | Assigning to any field after construction raises `FrozenInstanceError` | `instance.target_labels = ["x"]` raises `dataclasses.FrozenInstanceError` (or `AttributeError`) |

### 4.4 Atomic Replacement

| Test ID | Description | Expected |
|---|---|---|
| `test_runtime_config_replacement_produces_new_instance` | Replacing a `RuntimeConfig` by constructing a new one does not mutate the original | Construct `config_a`; construct `config_b` with different fields; assert `config_a.target_labels` is unchanged |

> **Note:** Thread-safety of the swap mechanism is the responsibility of the Detection Pipeline.
> Concurrency tests belong in `test/model_lens/test_detection_pipeline.py`.

---

## 5. `DetectionResult`

### 5.1 Happy Path — Construction

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_detection_result_stores_label` | Label string is stored | `DetectionResult(label="cat", confidence=0.9, bounding_box=(0.1, 0.2, 0.4, 0.6), is_target=True)` | `instance.label == "cat"` |
| `test_detection_result_stores_confidence` | Confidence float is stored | same as above | `instance.confidence == 0.9` |
| `test_detection_result_stores_bounding_box` | Bounding box tuple is stored | same as above | `instance.bounding_box == (0.1, 0.2, 0.4, 0.6)` |
| `test_detection_result_stores_is_target_true` | `is_target=True` is stored | `is_target=True` | `instance.is_target is True` |
| `test_detection_result_stores_is_target_false` | `is_target=False` is stored | `is_target=False` | `instance.is_target is False` |

### 5.2 Boundary Values — `confidence`

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_detection_result_confidence_at_upper_boundary` | `confidence=1.0` is valid | `confidence=1.0` | constructs without error; `instance.confidence == 1.0` |
| `test_detection_result_confidence_just_above_zero` | `confidence` just above `0.0` is valid | `confidence=1e-9` | constructs without error |
| `test_detection_result_confidence_zero` | `confidence=0.0` violates `0.0 < value` constraint | `confidence=0.0` | raises `model_lens.exceptions.ValidationError` |
| `test_detection_result_confidence_above_one` | `confidence > 1.0` violates `value <= 1.0` constraint | `confidence=1.001` | raises `model_lens.exceptions.ValidationError` |
| `test_detection_result_confidence_negative` | Negative `confidence` raises `ValidationError` | `confidence=-0.1` | raises `model_lens.exceptions.ValidationError` |

### 5.3 Validation Failures — `label`

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_detection_result_empty_label` | Empty `label` raises `ValidationError` | `label=""` | raises `model_lens.exceptions.ValidationError` |

### 5.4 Immutability

| Test ID | Description | Expected |
|---|---|---|
| `test_detection_result_is_frozen` | Assigning to any field after construction raises `FrozenInstanceError` | `instance.label = "dog"` raises `dataclasses.FrozenInstanceError` (or `AttributeError`) |

---

## 6. `Frame`

### 6.1 Happy Path — Construction

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_frame_stores_data` | `data` ndarray is stored | `Frame(data=np.zeros((480, 640, 3), dtype=np.uint8), timestamp=..., source="local:0")` | `instance.data.shape == (480, 640, 3)` and `instance.data.dtype == np.uint8` |
| `test_frame_stores_timestamp` | `timestamp` float is stored | `timestamp=1748000400.123456` | `instance.timestamp == 1748000400.123456` |
| `test_frame_stores_source_local` | `source` string for local camera is stored | `source="local:0"` | `instance.source == "local:0"` |
| `test_frame_stores_source_rtsp` | `source` string for RTSP camera is stored | `source="rtsp://192.168.1.10/stream"` | `instance.source == "rtsp://192.168.1.10/stream"` |

### 6.2 Data Independence (Copy Semantics)

| Test ID | Description | Expected |
|---|---|---|
| `test_frame_data_is_independent_of_original_array` | Mutating the original array after `Frame` construction does not affect `Frame.data` | Create `arr`; construct `Frame(data=arr.copy(), ...)`; mutate `arr`; assert `instance.data` is unchanged |
| `test_frame_init_stores_array_without_copying` | `Frame.__init__` stores the passed-in array reference directly — it does **not** call `.copy()` internally | Create `arr`; construct `Frame(data=arr, ...)`; assert `frame.data is arr` (identity, not just equality) |

> **Note:** `CameraCapture` is responsible for calling `.copy()` before constructing `Frame`.
> `test_frame_data_is_independent_of_original_array` passes a pre-copied array to confirm that
> once a copy has been made the data is independent.
> `test_frame_init_stores_array_without_copying` guards the inverse: `Frame.__init__` must not
> silently copy the array. Without this test, a change that adds `.copy()` inside `Frame.__init__`
> would pass all camera-capture tests while violating the architectural contract that copy
> responsibility belongs exclusively to `CameraCapture`.

### 6.3 Read-Only Convention

| Test ID | Description | Expected |
|---|---|---|
| `test_frame_data_mutation_does_not_raise` | Mutating `Frame.data` in place does **not** raise (mutation prevention is a convention, not enforced) | `instance.data[0, 0, 0] = 255` does not raise any exception |

### 6.4 Not Frozen

| Test ID | Description | Expected |
|---|---|---|
| `test_frame_is_not_frozen` | `Frame` is a regular (non-frozen) dataclass; field reassignment does not raise | `instance.source = "local:1"` does not raise `FrozenInstanceError` |

---

## Summary Table

| Entity | Test Count (approx.) | Key Concerns |
|---|---|---|
| `LocalCameraConfig` | 5 | defaults, boundary `device_index=0`, negative index, frozen, isinstance |
| `RtspCameraConfig` | 4 | URL stored, empty URL, frozen, isinstance |
| `CameraConfig` | 1 | cannot instantiate abstract base |
| `RuntimeConfig` | 8 | defaults, explicit fields, frozen, replacement immutability |
| `DetectionResult` | 10 | all fields, confidence boundaries, empty label, frozen |
| `Frame` | 6 | fields stored, copy independence, mutation convention, not frozen |
