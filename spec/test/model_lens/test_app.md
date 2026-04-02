# Test Specification: `test/model_lens/test_app.md`

## Source File Under Test

`src/model_lens/app.py`

## Test File

`test/model_lens/test_app.py`

## Imports Required

```python
import hashlib
import importlib.resources
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from model_lens.entities import (
    LocalCameraConfig,
    RuntimeConfig,
)
from model_lens.exceptions import ConfigurationError, OperationError
```

---

## Test Fixtures

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
> Lifespan tests (Section 3) use a separate fixture that does invoke the lifespan.

---

## 1. Static Assets

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

### 1.1 Happy Path — GET /

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_root_returns_200` | `unit` | `GET /` returns HTTP 200 | `GET /` | `response.status_code == 200` |
| `test_root_content_type_is_html` | `unit` | Response `Content-Type` is `text/html` | `GET /` | `"text/html" in response.headers["content-type"]` |
| `test_root_body_is_index_html` | `unit` | Response body matches the content of `index.html` | `GET /` | `response.content == index_content` |
| `test_root_etag_header_present` | `unit` | Response includes an `ETag` header | `GET /` | `"etag"` in `response.headers` |
| `test_root_etag_is_md5_of_content` | `unit` | `ETag` value is the MD5 hex digest of `index.html` bytes, quoted | `GET /` | `response.headers["etag"] == f'"{hashlib.md5(index_content).hexdigest()}"'` |
| `test_root_etag_is_quoted_string` | `unit` | `ETag` value is wrapped in double quotes per HTTP spec | `GET /` | `response.headers["etag"].startswith('"')` and `response.headers["etag"].endswith('"')` |
| `test_resolve_dist_dir_returns_package_dist_path` | `unit` | `resolve_dist_dir()` returns `importlib.resources.files("model_lens") / "dist"` | `resolve_dist_dir() == Path(str(importlib.resources.files("model_lens"))) / "dist"` |

### 1.2 Happy Path — GET /static/{path}

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_static_file_returns_200` | `unit` | `GET /static/app.js` returns HTTP 200 | `GET /static/app.js` | `response.status_code == 200` |
| `test_static_file_body_matches_content` | `unit` | Response body matches the file content | `GET /static/app.js` | `response.content == b"console.log('hello');"` |
| `test_static_file_not_found_returns_404` | `unit` | `GET /static/nonexistent.js` returns 404 | `GET /static/nonexistent.js` | `response.status_code == 404` |

### 1.3 Validation Failures

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_unknown_path_returns_404` | `unit` | An unrecognised path returns 404 | `GET /unknown` | `response.status_code == 404` |

---

## 2. Dependency Injection

### 2.1 Happy Path — get_pipeline

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_get_pipeline_returns_pipeline_from_app_state` | `unit` | `get_pipeline` returns the `DetectionPipeline` stored in `app.state` | `app.state.pipeline = mock_pipeline`; call `get_pipeline(request)` directly | return value is `mock_pipeline` |
| `test_get_pipeline_used_by_config_router` | `unit` | Config router uses `get_pipeline` dependency; the pipeline from `app.state` is the one whose `get_config` is called | `GET /config` with `mock_pipeline` in `app.state` | `mock_pipeline.get_config.call_count == 1` |

### 2.2 Happy Path — get_queue

> **Note:** `DetectionPipeline.get_queue()` is the single canonical method name for obtaining
> the result queue. The stream router and the pipeline must agree on this name; a silent rename
> on either side breaks the SSE stream without a compile-time error.

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_stream_router_calls_get_queue` | `unit` | The stream router retrieves the result queue via `pipeline.get_queue()` and never calls `get_result_queue()` or any other variant | `GET /stream` with `mock_pipeline` in `app.state`; `mock_pipeline.get_queue.return_value` is a `queue.Queue` containing one result | `mock_pipeline.get_queue.call_count >= 1`; `mock_pipeline.get_result_queue.call_count == 0` |

---

## 3. Lifespan — Startup and Shutdown

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
    mock_config.model.model = "fake.pt"
    mock_config.model.confidence_threshold = 0.5
    mock_config.camera.source_type = "local"
    mock_config.camera.device_index = 0

    with (
        patch("model_lens.app.load", return_value=mock_config) as mock_load,
        patch("model_lens.app.YOLOInferenceEngine") as mock_engine_cls,
        patch("model_lens.app.DetectionPipeline") as mock_pipeline_cls,
        patch("model_lens.app.resolve_dist_dir", return_value=dist_dir),
    ):
        mock_engine = MagicMock()
        mock_engine_cls.return_value = mock_engine
        mock_pipeline = MagicMock()
        mock_pipeline_cls.return_value = mock_pipeline

        yield {
            "load": mock_load,
            "engine_cls": mock_engine_cls,
            "engine": mock_engine,
            "pipeline_cls": mock_pipeline_cls,
            "pipeline": mock_pipeline,
            "config": mock_config,
        }
```

### 3.1 Happy Path — Startup Sequence

| Test ID | Category | Description | Expected |
|---|---|---|---|
| `test_lifespan_inference_engine_constructed` | `unit` | `YOLOInferenceEngine` is constructed with values from `AppConfig` | `lifespan_mocks["engine_cls"]` called with `model` and `confidence_threshold` from `mock_config.model` |
| `test_lifespan_detection_pipeline_constructed` | `unit` | `DetectionPipeline` is constructed with the engine and initial `RuntimeConfig` | `lifespan_mocks["pipeline_cls"]` called once |
| `test_lifespan_initial_runtime_config_camera_from_app_config` | `unit` | The `RuntimeConfig` passed to `DetectionPipeline` has a `camera` whose attributes match `AppConfig.camera` (e.g. `device_index` equals `mock_config.camera.device_index`) | inspect the first positional or keyword argument passed to `lifespan_mocks["pipeline_cls"]`; the `RuntimeConfig`'s `camera.device_index == mock_config.camera.device_index` |
| `test_lifespan_initial_runtime_config_target_labels_from_engine` | `unit` | The initial `RuntimeConfig` has `target_labels` populated from `engine.get_label_map()` | inspect the `RuntimeConfig` passed to `lifespan_mocks["pipeline_cls"]`; `runtime_config.target_labels == list(lifespan_mocks["engine"].get_label_map.return_value.values())` |
| `test_lifespan_pipeline_start_called` | `unit` | `DetectionPipeline.start()` is called during startup | `lifespan_mocks["pipeline"].start.call_count == 1` |
| `test_lifespan_pipeline_stored_in_app_state` | `unit` | After startup, `app.state.pipeline` is the constructed `DetectionPipeline` | `app.state.pipeline is lifespan_mocks["pipeline"]` |

### 3.2 Happy Path — Shutdown Sequence

| Test ID | Category | Description | Expected |
|---|---|---|---|
| `test_lifespan_pipeline_stop_called_on_shutdown` | `unit` | `DetectionPipeline.stop()` is called during shutdown | `lifespan_mocks["pipeline"].stop.call_count == 1` |
| `test_lifespan_engine_teardown_called_on_shutdown` | `unit` | `YOLOInferenceEngine.teardown()` is called during shutdown | `lifespan_mocks["engine"].teardown.call_count == 1` |
| `test_lifespan_engine_teardown_after_pipeline_stop` | `unit` | `teardown()` is called after `stop()` (order enforced) | `lifespan_mocks["pipeline"].stop` was called before `lifespan_mocks["engine"].teardown` (use `Mock` call order or side-effect tracking) |

### 3.3 Error Propagation

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_lifespan_load_error_exits` | `unit` | `load()` raising `ConfigurationError` causes `sys.exit(1)` | `mock_load.side_effect = ConfigurationError("bad config")` | `pytest.raises(SystemExit)` with `exc_info.value.code == 1` |
| `test_lifespan_inference_engine_configuration_error_exits` | `unit` | `YOLOInferenceEngine()` raising `ConfigurationError` causes `sys.exit(1)` | `mock_engine_cls.side_effect = ConfigurationError("bad model")` | `pytest.raises(SystemExit)` with `exc_info.value.code == 1` |
| `test_lifespan_inference_engine_operation_error_exits` | `unit` | `YOLOInferenceEngine()` raising `OperationError` causes `sys.exit(1)` | `mock_engine_cls.side_effect = OperationError("load failed")` | `pytest.raises(SystemExit)` with `exc_info.value.code == 1` |
| `test_lifespan_missing_dist_dir_exits` | `unit` | Missing `dist/` directory causes `sys.exit(1)` | `resolve_dist_dir` raises `FileNotFoundError` | `pytest.raises(SystemExit)` with `exc_info.value.code == 1` |
| `test_lifespan_missing_index_html_exits` | `unit` | Missing `dist/index.html` causes `sys.exit(1)` | `dist/` exists but `index.html` is absent | `pytest.raises(SystemExit)` with `exc_info.value.code == 1` |
| `test_lifespan_pipeline_stop_called_even_after_startup_failure` | `unit` | `DetectionPipeline.stop()` is still called if startup fails after the pipeline is constructed | pipeline is constructed but `start()` raises `RuntimeError` | `lifespan_mocks["pipeline"].stop.call_count == 1` |

---

## 4. Error Handling — HTTP 500

> These tests verify that unhandled exceptions propagating out of a route handler produce a
> well-formed `500 Internal Server Error` response. FastAPI's default exception handler is
> relied upon; no custom handler should suppress or re-format these responses.

### Fixture: `client_with_broken_pipeline`

Uses the standard `client` fixture with `mock_pipeline.get_config` configured to raise an
unexpected `RuntimeError`, simulating an unhandled exception inside a route handler.

```python
@pytest.fixture
def client_with_broken_pipeline(mock_pipeline, tmp_path):
    mock_pipeline.get_config.side_effect = RuntimeError("unexpected failure")

    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_bytes(b"<html></html>")
    (dist_dir / "static").mkdir()

    with patch("model_lens.app.resolve_dist_dir", return_value=dist_dir):
        from model_lens.app import create_app
        app = create_app()

    app.state.pipeline = mock_pipeline

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
```

> **Note:** `raise_server_exceptions=False` is required so that `TestClient` returns the
> HTTP 500 response instead of re-raising the exception in the test process.

### 4.1 Error Propagation

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_unhandled_exception_returns_500` | `unit` | An unhandled `RuntimeError` in a route handler returns HTTP 500 | `GET /config` with `mock_pipeline.get_config` raising `RuntimeError` | `response.status_code == 500` |
| `test_unhandled_exception_response_is_json` | `unit` | The 500 response body is valid JSON | same as above | `response.headers["content-type"]` contains `"application/json"`; `response.json()` does not raise |
| `test_unhandled_exception_response_has_detail_key` | `unit` | The 500 response body contains a `"detail"` key per FastAPI's standard error shape | same as above | `"detail" in response.json()` |

---

## Summary Table

| Entity | Test Count (approx.) | unit | e2e | race | Key Concerns |
|---|---|---|---|---|---|
| Static assets | 10 | 10 | 0 | 0 | `index.html` body, ETag MD5, quoted ETag, static files, 404 |
| Dependency injection | 3 | 3 | 0 | 0 | `get_pipeline` returns correct instance, used by router, stream router calls `get_queue()` not `get_result_queue()` |
| Lifespan startup/shutdown | 15 | 15 | 0 | 0 | construction order, AppConfig→RuntimeConfig mapping, `start`/`stop`/`teardown` calls, error propagation |
| Error handling (HTTP 500) | 3 | 3 | 0 | 0 | unhandled exception → 500, JSON body, `detail` key present |
