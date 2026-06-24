# Test Specification: `test_config.py`

## Source File Under Test
`src/model_lens/routers/config.py`

## Test File
`tests/model_lens/routers/test_config.py`

---

## `_serialize_config`

### Happy Path — _serialize_config

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_serialize_config_local_camera` | `unit` | Serializes a RuntimeConfig with LocalCameraConfig correctly. | | `RuntimeConfig` with `LocalCameraConfig(device_index=1)`, `confidence_threshold=0.6`, `target_labels=["cat"]` | Returns `{"camera": {"source_type": "local", "device_index": 1}, "confidence_threshold": 0.6, "target_labels": ["cat"]}` |
| `test_serialize_config_rtsp_camera` | `unit` | Serializes a RuntimeConfig with RtspCameraConfig correctly. | | `RuntimeConfig` with `RtspCameraConfig(rtsp_url="rtsp://host/path")`, `confidence_threshold=0.5`, `target_labels=[]` | Returns `{"camera": {"source_type": "rtsp", "rtsp_url": "rtsp://host/path"}, "confidence_threshold": 0.5, "target_labels": []}` |

---

## `_serialize_labels`

### Happy Path — _serialize_labels

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_serialize_labels` | `unit` | Returns valid_labels list from label map values. | | `{0: "person", 1: "car", 2: "dog"}` | Returns `{"valid_labels": ["person", "car", "dog"]}` |

---

## `GET /config`

### Happy Path — GET /config

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_get_config_returns_current_config` | `unit` | Returns serialized current RuntimeConfig. | Create a `TestClient` from a FastAPI app with `config.router`. Set `app.state.pipeline` to a mock whose `get_config()` returns a `RuntimeConfig` with `LocalCameraConfig(device_index=0)`, `confidence_threshold=0.5`, `target_labels=["person"]`. | `GET /config` | Response status `200`; JSON body is `{"camera": {"source_type": "local", "device_index": 0}, "confidence_threshold": 0.5, "target_labels": ["person"]}` |

---

## `PUT /config/camera`

### Happy Path — PUT /config/camera

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_put_camera_local` | `unit` | Updates camera to local and returns updated config. | Create a `TestClient`. Mock pipeline: `get_config()` returns a config; `update_config()` stores the new config; second `get_config()` returns the updated config with `LocalCameraConfig(device_index=2)`. | `PUT /config/camera` with body `{"camera": {"source_type": "local", "device_index": 2}}` | Response status `200`; JSON body contains `"camera": {"source_type": "local", "device_index": 2}` |
| `test_put_camera_rtsp` | `unit` | Updates camera to RTSP and returns updated config. | Create a `TestClient`. Mock pipeline similarly. | `PUT /config/camera` with body `{"camera": {"source_type": "rtsp", "rtsp_url": "rtsp://10.0.0.1/feed"}}` | Response status `200`; JSON body contains `"camera": {"source_type": "rtsp", "rtsp_url": "rtsp://10.0.0.1/feed"}` |

### Mock / Dependency Interaction

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_put_camera_calls_update_config` | `unit` | Calls `pipeline.update_config()` with a new RuntimeConfig containing the new camera. | Create a `TestClient`. Mock pipeline with `get_config()` returning existing config. | `PUT /config/camera` with body `{"camera": {"source_type": "local", "device_index": 3}}` | `pipeline.update_config` is called once; argument is a `RuntimeConfig` with `LocalCameraConfig(device_index=3)` |
| `test_put_camera_preserves_other_fields` | `unit` | Preserves `target_labels` and `confidence_threshold` from current config. | Mock pipeline `get_config()` returns config with `target_labels=["dog"]`, `confidence_threshold=0.7`. | `PUT /config/camera` with body `{"camera": {"source_type": "local", "device_index": 0}}` | The `RuntimeConfig` passed to `update_config` has `target_labels == ["dog"]` and `confidence_threshold == 0.7` |

---

## `GET /config/labels`

### Happy Path — GET /config/labels

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_get_labels_returns_valid_labels` | `unit` | Returns all labels from the engine's label map. | Create a `TestClient`. Set `app.state.engine` to a mock whose `get_label_map()` returns `{0: "person", 1: "bicycle", 2: "car"}`. | `GET /config/labels` | Response status `200`; JSON body is `{"valid_labels": ["person", "bicycle", "car"]}` |

---

## `PUT /config/labels`

### Happy Path — PUT /config/labels

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_put_labels_updates_target_labels` | `unit` | Updates target labels and returns updated config. | Create a `TestClient`. Mock pipeline: `get_config()` returns config; `update_config()` stores new config; second `get_config()` reflects updated `target_labels`. | `PUT /config/labels` with body `{"target_labels": ["cat", "dog"]}` | Response status `200`; JSON body `target_labels` is `["cat", "dog"]` |
| `test_put_labels_empty_list` | `unit` | Accepts an empty target labels list. | Create a `TestClient`. Mock pipeline similarly. | `PUT /config/labels` with body `{"target_labels": []}` | Response status `200`; JSON body `target_labels` is `[]` |

### Mock / Dependency Interaction

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_put_labels_calls_update_config` | `unit` | Calls `pipeline.update_config()` with new RuntimeConfig containing updated labels. | Create a `TestClient`. Mock pipeline with `get_config()` returning config with `camera=LocalCameraConfig(device_index=0)`, `confidence_threshold=0.5`. | `PUT /config/labels` with body `{"target_labels": ["person"]}` | `pipeline.update_config` is called once; argument is a `RuntimeConfig` with `target_labels == ["person"]` |
| `test_put_labels_preserves_camera_and_threshold` | `unit` | Preserves `camera` and `confidence_threshold` from current config. | Mock pipeline `get_config()` returns config with `RtspCameraConfig(rtsp_url="rtsp://x/y")`, `confidence_threshold=0.8`. | `PUT /config/labels` with body `{"target_labels": ["cat"]}` | The `RuntimeConfig` passed to `update_config` has the same `camera` and `confidence_threshold == 0.8` |
