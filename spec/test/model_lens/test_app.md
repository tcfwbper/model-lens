# Test Specification: `test/model_lens/test_app.md`

## Source File Under Test

`src/model_lens/app.py`, `src/model_lens/routers/config.py`, `src/model_lens/routers/stream.py`,
`src/model_lens/routers/health.py`, `src/model_lens/schemas.py`

## Test File

`test/model_lens/test_app.py`

## Imports Required

```python
import hashlib
import json
import sys
import time
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from model_lens.entities import (
    DetectionResult,
    Frame,
    LocalCameraConfig,
    RtspCameraConfig,
    RuntimeConfig,
)
from model_lens.exceptions import ConfigurationError, OperationError
```

---

## Test Fixtures

The following fixtures are shared across all test sections. They are defined once at the top of
the test file and reused by individual tests.

### `mock_pipeline`

A `MagicMock` that stands in for a `DetectionPipeline` instance. Pre-configured with a default
`RuntimeConfig` accessible via `mock_pipeline.get_config.return_value`.

```python
@pytest.fixture
def mock_pipeline():
    pipeline = MagicMock()
    pipeline.get_config.return_value = RuntimeConfig(
        camera=LocalCameraConfig(device_index=0),
        target_labels=[],
        confidence_threshold=0.5,
    )
    return pipeline
```

### `client`

A `TestClient` wrapping the FastAPI app, with `mock_pipeline` injected into `app.state` and the
lifespan bypassed. The `dist/` directory is provided as a temporary fake (see Static Assets
section for details).

```python
@pytest.fixture
def client(mock_pipeline, tmp_path):
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    index_html = dist_dir / "index.html"
    index_html.write_bytes(b"<html><body>ModelLens</body></html>")
    static_dir = dist_dir / "static"
    static_dir.mkdir()

    with patch("model_lens.app.resolve_dist_dir", return_value=dist_dir):
        from model_lens.app import create_app
        app = create_app()

    app.state.pipeline = mock_pipeline

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
```

> **Note:** `create_app()` is the app factory function. The lifespan is **not** invoked by
> `TestClient` when the pipeline is injected directly into `app.state` before the client starts.
> Lifespan tests (Section 8) use a separate fixture that does invoke the lifespan.

---

## 1. Health Check — `GET /healthz`

### 1.1 Happy Path

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_healthz_returns_200` | `GET /healthz` returns HTTP 200 | `GET /healthz` | `response.status_code == 200` |
| `test_healthz_returns_empty_body` | Response body is empty | `GET /healthz` | `response.content == b""` |

---

## 2. Config API — `GET /config`

### 2.1 Happy Path — Local Camera

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_get_config_returns_200` | `GET /config` returns HTTP 200 | `mock_pipeline.get_config()` returns default `RuntimeConfig` | `response.status_code == 200` |
| `test_get_config_local_source_type` | Response contains `source_type = "local"` | default `RuntimeConfig` with `LocalCameraConfig(device_index=0)` | `body["camera"]["source_type"] == "local"` |
| `test_get_config_local_device_index` | Response contains correct `device_index` | default `RuntimeConfig` with `LocalCameraConfig(device_index=0)` | `body["camera"]["device_index"] == 0` |
| `test_get_config_local_no_rtsp_url` | Response does not contain `rtsp_url` when source is local | default `RuntimeConfig` with `LocalCameraConfig` | `"rtsp_url" not in body["camera"]` |
| `test_get_config_confidence_threshold` | Response contains `confidence_threshold` | default `RuntimeConfig` with `confidence_threshold=0.5` | `body["confidence_threshold"] == 0.5` |
| `test_get_config_target_labels_empty` | Response contains empty `target_labels` | default `RuntimeConfig` with `target_labels=[]` | `body["target_labels"] == []` |
| `test_get_config_target_labels_non_empty` | Response contains non-empty `target_labels` | `RuntimeConfig(target_labels=["cat", "dog"], ...)` | `body["target_labels"] == ["cat", "dog"]` |

### 2.2 Happy Path — RTSP Camera

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_get_config_rtsp_source_type` | Response contains `source_type = "rtsp"` | `RuntimeConfig(camera=RtspCameraConfig(rtsp_url="rtsp://192.168.1.10/stream"), ...)` | `body["camera"]["source_type"] == "rtsp"` |
| `test_get_config_rtsp_url` | Response contains correct `rtsp_url` | same as above | `body["camera"]["rtsp_url"] == "rtsp://192.168.1.10/stream"` |
| `test_get_config_rtsp_no_device_index` | Response does not contain `device_index` when source is RTSP | same as above | `"device_index" not in body["camera"]` |

---

## 3. Config API — `PUT /config/camera`

### 3.1 Happy Path — Switch to Local Camera

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_put_camera_local_returns_200` | Valid local camera request returns HTTP 200 | `{"camera": {"source_type": "local", "device_index": 0}}` | `response.status_code == 200` |
| `test_put_camera_local_calls_update_config` | `DetectionPipeline.update_config` is called once | valid local camera request | `mock_pipeline.update_config.call_count == 1` |
| `test_put_camera_local_update_config_receives_runtime_config` | `update_config` receives a `RuntimeConfig` with the new `LocalCameraConfig` | `{"camera": {"source_type": "local", "device_index": 2}}` | the `RuntimeConfig` passed to `update_config` has `camera.device_index == 2` |
| `test_put_camera_local_response_reflects_new_camera` | Response body reflects the updated camera | `{"camera": {"source_type": "local", "device_index": 2}}` | `body["camera"]["device_index"] == 2` |
| `test_put_camera_local_preserves_target_labels` | `target_labels` in the updated `RuntimeConfig` is preserved from the current config | current config has `target_labels=["cat"]`; request updates camera only | the `RuntimeConfig` passed to `update_config` has `target_labels == ["cat"]` |
| `test_put_camera_local_preserves_confidence_threshold` | `confidence_threshold` in the updated `RuntimeConfig` is preserved | current config has `confidence_threshold=0.75` | the `RuntimeConfig` passed to `update_config` has `confidence_threshold == 0.75` |

### 3.2 Happy Path — Switch to RTSP Camera

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_put_camera_rtsp_returns_200` | Valid RTSP camera request returns HTTP 200 | `{"camera": {"source_type": "rtsp", "rtsp_url": "rtsp://192.168.1.10/stream"}}` | `response.status_code == 200` |
| `test_put_camera_rtsp_update_config_receives_runtime_config` | `update_config` receives a `RuntimeConfig` with the new `RtspCameraConfig` | same as above | the `RuntimeConfig` passed to `update_config` has `camera.rtsp_url == "rtsp://192.168.1.10/stream"` |
| `test_put_camera_rtsp_response_reflects_new_camera` | Response body reflects the updated RTSP camera | same as above | `body["camera"]["source_type"] == "rtsp"` and `body["camera"]["rtsp_url"] == "rtsp://192.168.1.10/stream"` |

### 3.3 Validation Failures

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_put_camera_invalid_source_type_returns_422` | Unknown `source_type` returns 422 | `{"camera": {"source_type": "usb"}}` | `response.status_code == 422` |
| `test_put_camera_local_negative_device_index_returns_422` | Negative `device_index` returns 422 | `{"camera": {"source_type": "local", "device_index": -1}}` | `response.status_code == 422` |
| `test_put_camera_rtsp_missing_url_returns_422` | Missing `rtsp_url` for RTSP source returns 422 | `{"camera": {"source_type": "rtsp"}}` | `response.status_code == 422` |
| `test_put_camera_rtsp_empty_url_returns_422` | Empty `rtsp_url` returns 422 | `{"camera": {"source_type": "rtsp", "rtsp_url": ""}}` | `response.status_code == 422` |
| `test_put_camera_rtsp_url_wrong_scheme_returns_422` | `rtsp_url` not starting with `rtsp://` returns 422 | `{"camera": {"source_type": "rtsp", "rtsp_url": "http://192.168.1.10/stream"}}` | `response.status_code == 422` |
| `test_put_camera_missing_camera_field_returns_422` | Request body missing `camera` field returns 422 | `{}` | `response.status_code == 422` |
| `test_put_camera_malformed_json_returns_400` | Non-JSON body returns 400 | raw bytes `b"not json"` with `Content-Type: application/json` | `response.status_code == 400` |
| `test_put_camera_confidence_threshold_in_body_is_ignored` | `confidence_threshold` in request body is silently ignored, not rejected | `{"camera": {"source_type": "local", "device_index": 0}, "confidence_threshold": 0.9}` | `response.status_code == 200` |

---

## 4. Config API — `PUT /config/labels`

### 4.1 Happy Path

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_put_labels_returns_200` | Valid labels list returns HTTP 200 | `{"target_labels": ["cat", "dog"]}` | `response.status_code == 200` |
| `test_put_labels_calls_update_config` | `DetectionPipeline.update_config` is called once | `{"target_labels": ["cat"]}` | `mock_pipeline.update_config.call_count == 1` |
| `test_put_labels_update_config_receives_runtime_config` | `update_config` receives a `RuntimeConfig` with the new labels | `{"target_labels": ["cat", "dog"]}` | the `RuntimeConfig` passed to `update_config` has `target_labels == ["cat", "dog"]` |
| `test_put_labels_empty_list_is_valid` | Empty `target_labels` list is accepted | `{"target_labels": []}` | `response.status_code == 200` |
| `test_put_labels_response_reflects_new_labels` | Response body reflects the updated labels | `{"target_labels": ["person"]}` | `body["target_labels"] == ["person"]` |
| `test_put_labels_preserves_camera` | `camera` in the updated `RuntimeConfig` is preserved from the current config | current config has `LocalCameraConfig(device_index=1)`; request updates labels only | the `RuntimeConfig` passed to `update_config` has `camera.device_index == 1` |
| `test_put_labels_preserves_confidence_threshold` | `confidence_threshold` in the updated `RuntimeConfig` is preserved | current config has `confidence_threshold=0.75` | the `RuntimeConfig` passed to `update_config` has `confidence_threshold == 0.75` |

### 4.2 Validation Failures

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_put_labels_missing_field_returns_422` | Request body missing `target_labels` field returns 422 | `{}` | `response.status_code == 422` |
| `test_put_labels_non_array_returns_422` | `target_labels` is not an array returns 422 | `{"target_labels": "cat"}` | `response.status_code == 422` |
| `test_put_labels_array_of_non_strings_returns_422` | `target_labels` contains non-string elements returns 422 | `{"target_labels": [1, 2, 3]}` | `response.status_code == 422` |
| `test_put_labels_malformed_json_returns_400` | Non-JSON body returns 400 | raw bytes `b"not json"` with `Content-Type: application/json` | `response.status_code == 400` |

---

## 5. Stream API — `GET /stream`

### Fixture: `pipeline_result_queue`

Tests in this section use a helper that injects a pre-populated `queue.SimpleQueue` into
`mock_pipeline.get_result_queue.return_value`. Each item in the queue is a `PipelineResult`-like
`MagicMock` with `jpeg_bytes`, `timestamp`, `source`, and `detections` attributes set.

```python
@pytest.fixture
def make_pipeline_result():
    def _make(label="cat", confidence=0.9, is_target=True):
        result = MagicMock()
        result.jpeg_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 16  # minimal fake JPEG bytes
        result.timestamp = 1748000400.123456
        result.source = "local:0"
        detection = DetectionResult(
            label=label,
            confidence=confidence,
            bounding_box=(0.1, 0.2, 0.4, 0.6),
            is_target=is_target,
        )
        result.detections = [detection]
        return result
    return _make
```

### 5.1 Happy Path — Event Payload Format

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_stream_returns_200` | `GET /stream` returns HTTP 200 | one result in queue, then queue empty | `response.status_code == 200` |
| `test_stream_content_type_is_text_event_stream` | Response `Content-Type` is `text/event-stream` | one result in queue | `"text/event-stream" in response.headers["content-type"]` |
| `test_stream_event_contains_jpeg_b64` | SSE event payload contains `jpeg_b64` field | one result with known `jpeg_bytes` | `"jpeg_b64"` key present in parsed JSON; value is a non-empty string |
| `test_stream_event_jpeg_b64_is_valid_base64` | `jpeg_b64` value is valid base64 | one result with known `jpeg_bytes` | `base64.b64decode(body["jpeg_b64"])` does not raise |
| `test_stream_event_jpeg_b64_decodes_to_original_bytes` | Decoded `jpeg_b64` matches original `jpeg_bytes` | one result with known `jpeg_bytes` | `base64.b64decode(body["jpeg_b64"]) == result.jpeg_bytes` |
| `test_stream_event_contains_timestamp` | SSE event payload contains `timestamp` field | one result with `timestamp=1748000400.123456` | `body["timestamp"] == 1748000400.123456` |
| `test_stream_event_contains_source` | SSE event payload contains `source` field | one result with `source="local:0"` | `body["source"] == "local:0"` |
| `test_stream_event_contains_detections` | SSE event payload contains `detections` array | one result with one detection | `len(body["detections"]) == 1` |
| `test_stream_event_detection_label` | Detection object contains correct `label` | detection with `label="cat"` | `body["detections"][0]["label"] == "cat"` |
| `test_stream_event_detection_confidence` | Detection object contains correct `confidence` | detection with `confidence=0.9` | `body["detections"][0]["confidence"] == 0.9` |
| `test_stream_event_detection_bounding_box` | Detection object contains correct `bounding_box` | detection with `bounding_box=(0.1, 0.2, 0.4, 0.6)` | `body["detections"][0]["bounding_box"] == [0.1, 0.2, 0.4, 0.6]` |
| `test_stream_event_detection_is_target_true` | Detection object contains `is_target=True` | detection with `is_target=True` | `body["detections"][0]["is_target"] is True` |
| `test_stream_event_detection_is_target_false` | Detection object contains `is_target=False` | detection with `is_target=False` | `body["detections"][0]["is_target"] is False` |
| `test_stream_event_empty_detections` | `detections` array is empty when no objects detected | result with `detections=[]` | `body["detections"] == []` |
| `test_stream_event_line_format` | Each SSE event line starts with `data: ` | one result in queue | raw chunk starts with `b"data: "` |
| `test_stream_event_ends_with_double_newline` | Each SSE event ends with `\n\n` | one result in queue | raw chunk ends with `b"\n\n"` |

### 5.2 Keepalive

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_stream_keepalive_sent_when_queue_empty` | When the queue is empty for 1 second, a keepalive comment is sent | queue is empty; mock `time.monotonic` to advance by 1.0 s | a chunk matching `b": keepalive\n\n"` is received |
| `test_stream_keepalive_format` | Keepalive line is an SSE comment (starts with `: `) | same as above | raw chunk is exactly `b": keepalive\n\n"` |

### 5.3 Idle Timeout

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_stream_idle_timeout_closes_connection` | After 30 seconds of idle time the server closes the stream | queue is empty; mock `time.monotonic` to advance by 30.0 s without any frame dequeued | the response iterator ends (no more chunks); connection is closed cleanly |
| `test_stream_idle_timer_resets_on_frame` | Receiving a frame resets the idle timer | one frame dequeued at t=25 s; mock `time.monotonic` to advance to t=54 s (25 s after the frame) | connection remains open at t=54 s (only 29 s since last frame) |

### 5.4 Disconnect Handling

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_stream_client_disconnect_does_not_raise` | Closing the `TestClient` stream mid-flight does not raise a server-side exception | open stream with `stream=True`; close the response before all events are consumed | no exception is raised; `response.close()` completes cleanly |

---

## 6. Static Assets

### Fixture: `static_client`

A dedicated `TestClient` fixture that sets up a temporary `dist/` directory with a known
`index.html` and a static asset file, then yields the client. Used only in this section.

```python
@pytest.fixture
def static_client(mock_pipeline, tmp_path):
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    index_content = b"<html><body>ModelLens</body></html>"
    (dist_dir / "index.html").write_bytes(index_content)
    static_dir = dist_dir / "static"
    static_dir.mkdir()
    (static_dir / "app.js").write_bytes(b"console.log('hello');")

    with patch("model_lens.app.resolve_dist_dir", return_value=dist_dir):
        from model_lens.app import create_app
        app = create_app()

    app.state.pipeline = mock_pipeline

    with TestClient(app) as c:
        yield c, index_content
```

### 6.1 `GET /` — Serves `index.html`

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_root_returns_200` | `GET /` returns HTTP 200 | `GET /` | `response.status_code == 200` |
| `test_root_content_type_is_html` | Response `Content-Type` is `text/html` | `GET /` | `"text/html" in response.headers["content-type"]` |
| `test_root_body_is_index_html` | Response body matches the content of `index.html` | `GET /` | `response.content == index_content` |
| `test_root_etag_header_present` | Response includes an `ETag` header | `GET /` | `"etag"` in `response.headers` |
| `test_root_etag_is_md5_of_content` | `ETag` value is the MD5 hex digest of `index.html` bytes, quoted | `GET /` | `response.headers["etag"] == f'"{hashlib.md5(index_content).hexdigest()}"'` |
| `test_root_etag_is_quoted_string` | `ETag` value is wrapped in double quotes per HTTP spec | `GET /` | `response.headers["etag"].startswith('"')` and `response.headers["etag"].endswith('"')` |

### 6.2 `GET /static/{path}` — Serves Static Files

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_static_file_returns_200` | `GET /static/app.js` returns HTTP 200 | `GET /static/app.js` | `response.status_code == 200` |
| `test_static_file_body_matches_content` | Response body matches the file content | `GET /static/app.js` | `response.content == b"console.log('hello');"` |
| `test_static_file_not_found_returns_404` | `GET /static/nonexistent.js` returns 404 | `GET /static/nonexistent.js` | `response.status_code == 404` |

### 6.3 Unknown Paths

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_unknown_path_returns_404` | An unrecognised path returns 404 | `GET /unknown` | `response.status_code == 404` |

---

## 7. Dependency Injection

### 7.1 `get_pipeline`

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_get_pipeline_returns_pipeline_from_app_state` | `get_pipeline` returns the `DetectionPipeline` stored in `app.state` | `app.state.pipeline = mock_pipeline`; call `get_pipeline(request)` directly | return value is `mock_pipeline` |
| `test_get_pipeline_used_by_config_router` | Config router uses `get_pipeline` dependency; the pipeline from `app.state` is the one whose `get_config` is called | `GET /config` with `mock_pipeline` in `app.state` | `mock_pipeline.get_config.call_count == 1` |

---

## 8. Lifespan — Startup and Shutdown

### Fixture: `lifespan_mocks`

Tests in this section patch all external dependencies so the lifespan can run without real
hardware or files:

```python
@pytest.fixture
def lifespan_mocks(tmp_path):
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_bytes(b"<html></html>")
    (dist_dir / "static").mkdir()

    mock_config = MagicMock()
    mock_config.model.model_path = "fake.pt"
    mock_config.model.confidence_threshold = 0.5
    mock_config.model.labels_path = "fake_labels.txt"
    mock_config.camera.source_type = "local"
    mock_config.camera.device_index = 0

    with (
        patch("model_lens.app.ConfigLoader") as mock_loader_cls,
        patch("model_lens.app.TorchInferenceEngine") as mock_engine_cls,
        patch("model_lens.app.DetectionPipeline") as mock_pipeline_cls,
        patch("model_lens.app.resolve_dist_dir", return_value=dist_dir),
    ):
        mock_loader_cls.return_value.load.return_value = mock_config
        mock_engine = MagicMock()
        mock_engine_cls.return_value = mock_engine
        mock_pipeline = MagicMock()
        mock_pipeline_cls.return_value = mock_pipeline

        yield {
            "loader_cls": mock_loader_cls,
            "engine_cls": mock_engine_cls,
            "engine": mock_engine,
            "pipeline_cls": mock_pipeline_cls,
            "pipeline": mock_pipeline,
            "config": mock_config,
        }
```

### 8.1 Happy Path — Startup Sequence

| Test ID | Description | Expected |
|---|---|---|
| `test_lifespan_config_loader_called` | `ConfigLoader.load()` is called during startup | `lifespan_mocks["loader_cls"].return_value.load.call_count == 1` |
| `test_lifespan_inference_engine_constructed` | `TorchInferenceEngine` is constructed with values from `AppConfig` | `lifespan_mocks["engine_cls"]` called with `model_path`, `confidence_threshold`, `labels_path` from `mock_config.model` |
| `test_lifespan_detection_pipeline_constructed` | `DetectionPipeline` is constructed with the engine and initial `RuntimeConfig` | `lifespan_mocks["pipeline_cls"]` called once |
| `test_lifespan_pipeline_start_called` | `DetectionPipeline.start()` is called during startup | `lifespan_mocks["pipeline"].start.call_count == 1` |
| `test_lifespan_pipeline_stored_in_app_state` | After startup, `app.state.pipeline` is the constructed `DetectionPipeline` | `app.state.pipeline is lifespan_mocks["pipeline"]` |

### 8.2 Happy Path — Shutdown Sequence

| Test ID | Description | Expected |
|---|---|---|
| `test_lifespan_pipeline_stop_called_on_shutdown` | `DetectionPipeline.stop()` is called during shutdown | `lifespan_mocks["pipeline"].stop.call_count == 1` |
| `test_lifespan_engine_teardown_called_on_shutdown` | `TorchInferenceEngine.teardown()` is called during shutdown | `lifespan_mocks["engine"].teardown.call_count == 1` |
| `test_lifespan_engine_teardown_after_pipeline_stop` | `teardown()` is called after `stop()` (order enforced) | `lifespan_mocks["pipeline"].stop` was called before `lifespan_mocks["engine"].teardown` (use `Mock` call order or side-effect tracking) |

### 8.3 Startup Failures — `sys.exit(1)`

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_lifespan_config_loader_error_exits` | `ConfigLoader.load()` raising `ConfigurationError` causes `sys.exit(1)` | `mock_loader.load.side_effect = ConfigurationError("bad config")` | `pytest.raises(SystemExit)` with `exc_info.value.code == 1` |
| `test_lifespan_inference_engine_configuration_error_exits` | `TorchInferenceEngine()` raising `ConfigurationError` causes `sys.exit(1)` | `mock_engine_cls.side_effect = ConfigurationError("bad model")` | `pytest.raises(SystemExit)` with `exc_info.value.code == 1` |
| `test_lifespan_inference_engine_operation_error_exits` | `TorchInferenceEngine()` raising `OperationError` causes `sys.exit(1)` | `mock_engine_cls.side_effect = OperationError("load failed")` | `pytest.raises(SystemExit)` with `exc_info.value.code == 1` |
| `test_lifespan_missing_dist_dir_exits` | Missing `dist/` directory causes `sys.exit(1)` | `resolve_dist_dir` raises `FileNotFoundError` | `pytest.raises(SystemExit)` with `exc_info.value.code == 1` |
| `test_lifespan_missing_index_html_exits` | Missing `dist/index.html` causes `sys.exit(1)` | `dist/` exists but `index.html` is absent | `pytest.raises(SystemExit)` with `exc_info.value.code == 1` |
| `test_lifespan_pipeline_stop_called_even_after_startup_failure` | `DetectionPipeline.stop()` is still called if startup fails after the pipeline is constructed | pipeline is constructed but `start()` raises `RuntimeError` | `lifespan_mocks["pipeline"].stop.call_count == 1` |

---

## 9. Schemas — Pydantic Request Model Validation

> These tests exercise the Pydantic models in `schemas.py` directly, without going through HTTP.

### 9.1 `LocalCameraRequest`

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_local_camera_request_default_device_index` | Default `device_index` is `0` | `LocalCameraRequest(source_type="local")` | `instance.device_index == 0` |
| `test_local_camera_request_explicit_device_index` | Explicit `device_index` is stored | `LocalCameraRequest(source_type="local", device_index=3)` | `instance.device_index == 3` |
| `test_local_camera_request_negative_device_index_raises` | Negative `device_index` raises `pydantic.ValidationError` | `LocalCameraRequest(source_type="local", device_index=-1)` | raises `pydantic.ValidationError` |

### 9.2 `RtspCameraRequest`

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_rtsp_camera_request_stores_url` | Valid RTSP URL is stored | `RtspCameraRequest(source_type="rtsp", rtsp_url="rtsp://x")` | `instance.rtsp_url == "rtsp://x"` |
| `test_rtsp_camera_request_wrong_scheme_raises` | URL not starting with `rtsp://` raises `pydantic.ValidationError` | `RtspCameraRequest(source_type="rtsp", rtsp_url="http://x")` | raises `pydantic.ValidationError` |
| `test_rtsp_camera_request_empty_url_raises` | Empty `rtsp_url` raises `pydantic.ValidationError` | `RtspCameraRequest(source_type="rtsp", rtsp_url="")` | raises `pydantic.ValidationError` |

### 9.3 `UpdateCameraRequest` — Discriminated Union

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_update_camera_request_local_discriminated` | `source_type="local"` produces `LocalCameraRequest` | `UpdateCameraRequest(camera={"source_type": "local", "device_index": 0})` | `isinstance(instance.camera, LocalCameraRequest)` |
| `test_update_camera_request_rtsp_discriminated` | `source_type="rtsp"` produces `RtspCameraRequest` | `UpdateCameraRequest(camera={"source_type": "rtsp", "rtsp_url": "rtsp://x"})` | `isinstance(instance.camera, RtspCameraRequest)` |
| `test_update_camera_request_unknown_source_type_raises` | Unknown `source_type` raises `pydantic.ValidationError` | `UpdateCameraRequest(camera={"source_type": "usb"})` | raises `pydantic.ValidationError` |

### 9.4 `UpdateLabelsRequest`

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_update_labels_request_stores_labels` | Labels list is stored | `UpdateLabelsRequest(target_labels=["cat", "dog"])` | `instance.target_labels == ["cat", "dog"]` |
| `test_update_labels_request_empty_list_valid` | Empty list is valid | `UpdateLabelsRequest(target_labels=[])` | `instance.target_labels == []` |
| `test_update_labels_request_non_string_elements_raises` | Non-string elements raise `pydantic.ValidationError` | `UpdateLabelsRequest(target_labels=[1, 2])` | raises `pydantic.ValidationError` |

---

## Summary Table

| Area | Test Count (approx.) | Key Concerns |
|---|---|---|
| `GET /healthz` | 2 | 200 status, empty body |
| `GET /config` | 10 | local/RTSP shape, field presence/absence, labels, confidence |
| `PUT /config/camera` | 14 | local/RTSP update, `update_config` called, field preservation, validation failures, ignored fields |
| `PUT /config/labels` | 11 | labels update, `update_config` called, field preservation, validation failures |
| `GET /stream` | 20 | event format, base64, keepalive, idle timeout, disconnect |
| Static assets | 9 | `index.html` body, ETag MD5, quoted ETag, static files, 404 |
| Dependency injection | 2 | `get_pipeline` returns correct instance, used by router |
| Lifespan startup/shutdown | 14 | construction order, `start`/`stop`/`teardown` calls, `sys.exit(1)` on failures |
| Schemas | 13 | Pydantic model validation, discriminated union, boundary values |
