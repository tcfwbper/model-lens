# Test Specification: `test_schemas.py`

## Source File Under Test
`src/model_lens/schemas.py`

## Test File
`tests/model_lens/test_schemas.py`

---

## `LocalCameraRequest`

### Happy Path — Construction

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_local_camera_request_defaults` | `unit` | Constructs with default `device_index` of 0. | | `{"source_type": "local"}` | Instance has `source_type == "local"` and `device_index == 0` |
| `test_local_camera_request_explicit_device_index` | `unit` | Constructs with an explicit device index. | | `{"source_type": "local", "device_index": 2}` | Instance has `device_index == 2` |

### Boundary Values — device_index

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_local_camera_request_device_index_zero` | `unit` | Accepts the minimum valid device index. | | `{"source_type": "local", "device_index": 0}` | Instance has `device_index == 0` |

### Validation Failures — device_index

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_local_camera_request_negative_device_index` | `unit` | Rejects a negative device index. | | `{"source_type": "local", "device_index": -1}` | Raises `ValidationError` |

---

## `RtspCameraRequest`

### Happy Path — Construction

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_rtsp_camera_request_valid_url` | `unit` | Constructs with a valid RTSP URL. | | `{"source_type": "rtsp", "rtsp_url": "rtsp://192.168.1.1/stream"}` | Instance has `source_type == "rtsp"` and `rtsp_url == "rtsp://192.168.1.1/stream"` |

### Validation Failures — rtsp_url

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_rtsp_camera_request_invalid_url_scheme` | `unit` | Rejects a URL that does not start with `rtsp://`. | | `{"source_type": "rtsp", "rtsp_url": "http://example.com/stream"}` | Raises `ValidationError` |
| `test_rtsp_camera_request_empty_url` | `unit` | Rejects an empty string URL. | | `{"source_type": "rtsp", "rtsp_url": ""}` | Raises `ValidationError` |

---

## `UpdateCameraRequest`

### Happy Path — Construction

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_update_camera_request_local` | `unit` | Discriminates to `LocalCameraRequest` when `source_type` is `"local"`. | | `{"camera": {"source_type": "local", "device_index": 1}}` | `body.camera` is a `LocalCameraRequest` with `device_index == 1` |
| `test_update_camera_request_rtsp` | `unit` | Discriminates to `RtspCameraRequest` when `source_type` is `"rtsp"`. | | `{"camera": {"source_type": "rtsp", "rtsp_url": "rtsp://host/path"}}` | `body.camera` is a `RtspCameraRequest` with `rtsp_url == "rtsp://host/path"` |

### Validation Failures

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_update_camera_request_invalid_source_type` | `unit` | Rejects an unknown discriminator value. | | `{"camera": {"source_type": "usb", "device_index": 0}}` | Raises `ValidationError` |
| `test_update_camera_request_missing_camera` | `unit` | Rejects a body with no `camera` field. | | `{}` | Raises `ValidationError` |

---

## `UpdateLabelsRequest`

### Happy Path — Construction

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_update_labels_request_with_labels` | `unit` | Constructs with a non-empty label list. | | `{"target_labels": ["cat", "dog"]}` | Instance has `target_labels == ["cat", "dog"]` |
| `test_update_labels_request_empty_list` | `unit` | Accepts an empty list as valid input. | | `{"target_labels": []}` | Instance has `target_labels == []` |

### Validation Failures

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_update_labels_request_missing_field` | `unit` | Rejects a body with no `target_labels` field. | | `{}` | Raises `ValidationError` |
