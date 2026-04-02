# Test Specification: `test/model_lens/routers/test_config.md`

## Source File Under Test

`src/model_lens/routers/config.py`

## Test File

`test/model_lens/routers/test_config.py`

## Imports Required

```python
import pytest
from fastapi.testclient import TestClient

from model_lens.entities import (
    LocalCameraConfig,
    RtspCameraConfig,
    RuntimeConfig,
)
```

## Fixtures

Uses the shared `client` and `mock_pipeline` fixtures from `conftest.py`. Tests for
`GET /config/labels` also require a `mock_engine` on `app.state.engine` (see section 2).

---

## 1. Config API — `GET /config`

### 1.1 Happy Path — Local Camera

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_get_config_returns_200` | `unit` | `GET /config` returns HTTP 200 | `mock_pipeline.get_config()` returns default `RuntimeConfig` | `response.status_code == 200` |
| `test_get_config_local_source_type` | `unit` | Response contains `source_type = "local"` | default `RuntimeConfig` with `LocalCameraConfig(device_index=0)` | `body["camera"]["source_type"] == "local"` |
| `test_get_config_local_device_index` | `unit` | Response contains correct `device_index` | default `RuntimeConfig` with `LocalCameraConfig(device_index=0)` | `body["camera"]["device_index"] == 0` |
| `test_get_config_local_no_rtsp_url` | `unit` | Response does not contain `rtsp_url` when source is local | default `RuntimeConfig` with `LocalCameraConfig` | `"rtsp_url" not in body["camera"]` |
| `test_get_config_confidence_threshold` | `unit` | Response contains `confidence_threshold` | default `RuntimeConfig` with `confidence_threshold=0.5` | `body["confidence_threshold"] == 0.5` |
| `test_get_config_target_labels_empty` | `unit` | Response contains empty `target_labels` | default `RuntimeConfig` with `target_labels=[]` | `body["target_labels"] == []` |
| `test_get_config_target_labels_non_empty` | `unit` | Response contains non-empty `target_labels` | `RuntimeConfig(target_labels=["cat", "dog"], ...)` | `body["target_labels"] == ["cat", "dog"]` |

### 1.2 Happy Path — RTSP Camera

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_get_config_rtsp_source_type` | `unit` | Response contains `source_type = "rtsp"` | `RuntimeConfig(camera=RtspCameraConfig(rtsp_url="rtsp://192.168.1.10/stream"), ...)` | `body["camera"]["source_type"] == "rtsp"` |
| `test_get_config_rtsp_url` | `unit` | Response contains correct `rtsp_url` | same as above | `body["camera"]["rtsp_url"] == "rtsp://192.168.1.10/stream"` |
| `test_get_config_rtsp_no_device_index` | `unit` | Response does not contain `device_index` when source is RTSP | same as above | `"device_index" not in body["camera"]` |

---

## 2. Config API — `GET /config/labels`

### Fixture: `client_with_engine`

A dedicated client fixture that injects both `mock_pipeline` and a `mock_engine` into
`app.state`, so that the `GET /config/labels` handler can call `engine.get_label_map()`.

```python
@pytest.fixture
def client_with_engine(client, mock_pipeline):
    mock_engine = MagicMock()
    mock_engine.get_label_map.return_value = {0: "person", 1: "bicycle", 2: "car"}
    client.app.state.engine = mock_engine
    return client, mock_engine
```

### 2.1 Happy Path — GET /config/labels

| Test ID | Category | Description | Input | Expected |
|---|---|---|---| ---|
| `test_get_labels_returns_200` | `unit` | `GET /config/labels` returns HTTP 200 | `mock_engine.get_label_map()` returns a non-empty label map | `response.status_code == 200` |
| `test_get_labels_response_shape` | `unit` | Response body has a `valid_labels` key containing a list | same as above | `"valid_labels" in body` and `isinstance(body["valid_labels"], list)` |
| `test_get_labels_values_match_engine_label_map` | `unit` | `valid_labels` list contains all values from `engine.get_label_map()` | `get_label_map()` returns `{0: "person", 1: "bicycle", 2: "car"}` | `body["valid_labels"] == ["person", "bicycle", "car"]` |
| `test_get_labels_calls_get_label_map` | `unit` | `engine.get_label_map()` is called exactly once | `GET /config/labels` | `mock_engine.get_label_map.call_count == 1` |
| `test_get_labels_empty_label_map` | `unit` | Empty label map returns empty `valid_labels` list | `get_label_map()` returns `{}` | `body["valid_labels"] == []` |

---

## 3. Config API — `PUT /config/camera`

### 3.1 Happy Path — Switch to Local Camera

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_put_camera_local_returns_200` | `unit` | Valid local camera request returns HTTP 200 | `{"camera": {"source_type": "local", "device_index": 0}}` | `response.status_code == 200` |
| `test_put_camera_local_calls_update_config` | `unit` | `DetectionPipeline.update_config` is called once | valid local camera request | `mock_pipeline.update_config.call_count == 1` |
| `test_put_camera_local_update_config_receives_runtime_config` | `unit` | `update_config` receives a `RuntimeConfig` with the new `LocalCameraConfig` | `{"camera": {"source_type": "local", "device_index": 2}}` | the `RuntimeConfig` passed to `update_config` has `camera.device_index == 2` |
| `test_put_camera_local_response_reflects_new_camera` | `unit` | Response body reflects the updated camera | `{"camera": {"source_type": "local", "device_index": 2}}` | `body["camera"]["device_index"] == 2` |
| `test_put_camera_local_preserves_target_labels` | `unit` | `target_labels` in the updated `RuntimeConfig` is preserved from the current config | current config has `target_labels=["cat"]`; request updates camera only | the `RuntimeConfig` passed to `update_config` has `target_labels == ["cat"]` |
| `test_put_camera_local_preserves_confidence_threshold` | `unit` | `confidence_threshold` in the updated `RuntimeConfig` is preserved | current config has `confidence_threshold=0.75` | the `RuntimeConfig` passed to `update_config` has `confidence_threshold == 0.75` |

### 3.2 Happy Path — Switch to RTSP Camera

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_put_camera_rtsp_returns_200` | `unit` | Valid RTSP camera request returns HTTP 200 | `{"camera": {"source_type": "rtsp", "rtsp_url": "rtsp://192.168.1.10/stream"}}` | `response.status_code == 200` |
| `test_put_camera_rtsp_update_config_receives_runtime_config` | `unit` | `update_config` receives a `RuntimeConfig` with the new `RtspCameraConfig` | same as above | the `RuntimeConfig` passed to `update_config` has `camera.rtsp_url == "rtsp://192.168.1.10/stream"` |
| `test_put_camera_rtsp_response_reflects_new_camera` | `unit` | Response body reflects the updated RTSP camera | same as above | `body["camera"]["source_type"] == "rtsp"` and `body["camera"]["rtsp_url"] == "rtsp://192.168.1.10/stream"` |

### 3.3 Validation Failures

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_put_camera_invalid_source_type_returns_422` | `unit` | Unknown `source_type` returns 422 | `{"camera": {"source_type": "usb"}}` | `response.status_code == 422` |
| `test_put_camera_local_negative_device_index_returns_422` | `unit` | Negative `device_index` returns 422 | `{"camera": {"source_type": "local", "device_index": -1}}` | `response.status_code == 422` |
| `test_put_camera_rtsp_missing_url_returns_422` | `unit` | Missing `rtsp_url` for RTSP source returns 422 | `{"camera": {"source_type": "rtsp"}}` | `response.status_code == 422` |
| `test_put_camera_rtsp_empty_url_returns_422` | `unit` | Empty `rtsp_url` returns 422 | `{"camera": {"source_type": "rtsp", "rtsp_url": ""}}` | `response.status_code == 422` |
| `test_put_camera_rtsp_url_wrong_scheme_returns_422` | `unit` | `rtsp_url` not starting with `rtsp://` returns 422 | `{"camera": {"source_type": "rtsp", "rtsp_url": "http://192.168.1.10/stream"}}` | `response.status_code == 422` |
| `test_put_camera_missing_camera_field_returns_422` | `unit` | Request body missing `camera` field returns 422 | `{}` | `response.status_code == 422` |
| `test_put_camera_malformed_json_returns_400` | `unit` | Non-JSON body returns 400 | raw bytes `b"not json"` with `Content-Type: application/json` | `response.status_code == 400` |
| `test_put_camera_confidence_threshold_in_body_is_ignored` | `unit` | `confidence_threshold` in request body is silently ignored, not rejected | `{"camera": {"source_type": "local", "device_index": 0}, "confidence_threshold": 0.9}` | `response.status_code == 200` |

---

## 4. Config API — `PUT /config/labels`

### 4.1 Happy Path — PUT /config/labels

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_put_labels_returns_200` | `unit` | Valid labels list returns HTTP 200 | `{"target_labels": ["cat", "dog"]}` | `response.status_code == 200` |
| `test_put_labels_calls_update_config` | `unit` | `DetectionPipeline.update_config` is called once | `{"target_labels": ["cat"]}` | `mock_pipeline.update_config.call_count == 1` |
| `test_put_labels_update_config_receives_runtime_config` | `unit` | `update_config` receives a `RuntimeConfig` with the new labels | `{"target_labels": ["cat", "dog"]}` | the `RuntimeConfig` passed to `update_config` has `target_labels == ["cat", "dog"]` |
| `test_put_labels_empty_list_is_valid` | `unit` | Empty `target_labels` list is accepted | `{"target_labels": []}` | `response.status_code == 200` |
| `test_put_labels_response_reflects_new_labels` | `unit` | Response body reflects the updated labels | `{"target_labels": ["person"]}` | `body["target_labels"] == ["person"]` |
| `test_put_labels_preserves_camera` | `unit` | `camera` in the updated `RuntimeConfig` is preserved from the current config | current config has `LocalCameraConfig(device_index=1)`; request updates labels only | the `RuntimeConfig` passed to `update_config` has `camera.device_index == 1` |
| `test_put_labels_preserves_confidence_threshold` | `unit` | `confidence_threshold` in the updated `RuntimeConfig` is preserved | current config has `confidence_threshold=0.75` | the `RuntimeConfig` passed to `update_config` has `confidence_threshold == 0.75` |

### 4.2 Validation Failures

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_put_labels_missing_field_returns_422` | `unit` | Request body missing `target_labels` field returns 422 | `{}` | `response.status_code == 422` |
| `test_put_labels_non_array_returns_422` | `unit` | `target_labels` is not an array returns 422 | `{"target_labels": "cat"}` | `response.status_code == 422` |
| `test_put_labels_array_of_non_strings_returns_422` | `unit` | `target_labels` contains non-string elements returns 422 | `{"target_labels": [1, 2, 3]}` | `response.status_code == 422` |
| `test_put_labels_malformed_json_returns_400` | `unit` | Non-JSON body returns 400 | raw bytes `b"not json"` with `Content-Type: application/json` | `response.status_code == 400` |

---

## Summary Table

| Entity | Test Count (approx.) | unit | e2e | race | Key Concerns |
|---|---|---|---|---|---|
| `GET /config` | 10 | 10 | 0 | 0 | local/RTSP shape, field presence/absence, labels, confidence |
| `GET /config/labels` | 5 | 5 | 0 | 0 | `valid_labels` shape, values from engine label map, empty map |
| `PUT /config/camera` | 17 | 17 | 0 | 0 | local/RTSP update, `update_config` called, field preservation, validation failures, ignored fields |
| `PUT /config/labels` | 11 | 11 | 0 | 0 | labels update, `update_config` called, field preservation, validation failures |
