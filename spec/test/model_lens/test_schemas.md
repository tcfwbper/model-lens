# Test Specification: `test/model_lens/test_schemas.md`

## Source File Under Test

`src/model_lens/schemas.py`

## Test File

`test/model_lens/test_schemas.py`

## Imports Required

```python
import pydantic
import pytest

from model_lens.schemas import (
    LocalCameraRequest,
    RtspCameraRequest,
    UpdateCameraRequest,
    UpdateLabelsRequest,
)
```

---

## 1. `LocalCameraRequest`

> These tests exercise the Pydantic models in `schemas.py` directly, without going through HTTP.

### 1.1 Happy Path — Default Construction

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_local_camera_request_default_device_index` | `unit` | Default `device_index` is `0` | `LocalCameraRequest(source_type="local")` | `instance.device_index == 0` |

### 1.2 Happy Path — Explicit Construction

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_local_camera_request_explicit_device_index` | `unit` | Explicit `device_index` is stored | `LocalCameraRequest(source_type="local", device_index=3)` | `instance.device_index == 3` |

### 1.3 Validation Failures — device_index

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_local_camera_request_negative_device_index_raises` | `unit` | Negative `device_index` raises `pydantic.ValidationError` | `LocalCameraRequest(source_type="local", device_index=-1)` | raises `pydantic.ValidationError` |

---

## 2. `RtspCameraRequest`

### 2.1 Happy Path — Construction

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_rtsp_camera_request_stores_url` | `unit` | Valid RTSP URL is stored | `RtspCameraRequest(source_type="rtsp", rtsp_url="rtsp://x")` | `instance.rtsp_url == "rtsp://x"` |

### 2.2 Validation Failures — rtsp_url

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_rtsp_camera_request_wrong_scheme_raises` | `unit` | URL not starting with `rtsp://` raises `pydantic.ValidationError` | `RtspCameraRequest(source_type="rtsp", rtsp_url="http://x")` | raises `pydantic.ValidationError` |
| `test_rtsp_camera_request_empty_url_raises` | `unit` | Empty `rtsp_url` raises `pydantic.ValidationError` | `RtspCameraRequest(source_type="rtsp", rtsp_url="")` | raises `pydantic.ValidationError` |

---

## 3. `UpdateCameraRequest`

### 3.1 Happy Path — Construction

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_update_camera_request_local_discriminated` | `unit` | `source_type="local"` produces `LocalCameraRequest` | `UpdateCameraRequest(camera={"source_type": "local", "device_index": 0})` | `isinstance(instance.camera, LocalCameraRequest)` |
| `test_update_camera_request_rtsp_discriminated` | `unit` | `source_type="rtsp"` produces `RtspCameraRequest` | `UpdateCameraRequest(camera={"source_type": "rtsp", "rtsp_url": "rtsp://x"})` | `isinstance(instance.camera, RtspCameraRequest)` |

### 3.2 Validation Failures — source_type

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_update_camera_request_unknown_source_type_raises` | `unit` | Unknown `source_type` raises `pydantic.ValidationError` | `UpdateCameraRequest(camera={"source_type": "usb"})` | raises `pydantic.ValidationError` |

---

## 4. `UpdateLabelsRequest`

### 4.1 Happy Path — Construction

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_update_labels_request_stores_labels` | `unit` | Labels list is stored | `UpdateLabelsRequest(target_labels=["cat", "dog"])` | `instance.target_labels == ["cat", "dog"]` |
| `test_update_labels_request_empty_list_valid` | `unit` | Empty list is valid | `UpdateLabelsRequest(target_labels=[])` | `instance.target_labels == []` |

### 4.2 Validation Failures

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_update_labels_request_missing_field_raises` | `unit` | Missing `target_labels` field raises `pydantic.ValidationError` | `UpdateLabelsRequest()` (no arguments) | raises `pydantic.ValidationError` |
| `test_update_labels_request_non_array_raises` | `unit` | `target_labels` not being a list raises `pydantic.ValidationError` | `UpdateLabelsRequest(target_labels="cat")` | raises `pydantic.ValidationError` |
| `test_update_labels_request_non_string_elements_raises` | `unit` | Non-string elements raise `pydantic.ValidationError` | `UpdateLabelsRequest(target_labels=[1, 2])` | raises `pydantic.ValidationError` |

---

## Summary Table

| Entity | Test Count (approx.) | unit | e2e | race | Key Concerns |
|---|---|---|---|---|---|
| `LocalCameraRequest` | 3 | 3 | 0 | 0 | default/explicit construction, negative device_index validation |
| `RtspCameraRequest` | 3 | 3 | 0 | 0 | construction, URL scheme/empty validation |
| `UpdateCameraRequest` | 3 | 3 | 0 | 0 | discriminated union construction, unknown source_type validation |
| `UpdateLabelsRequest` | 5 | 5 | 0 | 0 | construction, missing field, non-array type, non-string elements validation |
