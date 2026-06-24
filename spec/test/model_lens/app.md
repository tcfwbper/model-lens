# Test Specification: `test_app.py`

## Source File Under Test
`src/model_lens/app.py`

## Test File
`tests/model_lens/test_app.py`

---

## `_StartupExit`

### Type Hierarchy

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_startup_exit_inherits_system_exit` | `unit` | `_StartupExit` is a subclass of `SystemExit`. | | | `issubclass(_StartupExit, SystemExit)` is `True` |
| `test_startup_exit_inherits_exception` | `unit` | `_StartupExit` is a subclass of `Exception`. | | | `issubclass(_StartupExit, Exception)` is `True` |

### Catch Behaviour

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_startup_exit_caught_by_exception_handler` | `unit` | Can be caught by a bare `except Exception` clause. | | Raise `_StartupExit(1)` | Caught by `except Exception` |

---

## `resolve_dist_dir`

### Happy Path — resolve_dist_dir

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_resolve_dist_dir_returns_path` | `unit` | Returns a `Path` ending with `dist`. | Patch `importlib.resources.files` to return a fake path string (e.g., `/fake/package`). | | Returns `Path("/fake/package/dist")` |

---

## `get_pipeline`

### Happy Path — get_pipeline

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_get_pipeline_returns_pipeline_from_state` | `unit` | Returns the pipeline stored in `request.app.state.pipeline`. | Create a mock `Request` object whose `app.state.pipeline` is a mock `DetectionPipeline`. | The mock request | Returns the same mock pipeline instance |

---

## `_startup`

### Happy Path — _startup

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_startup_success` | `unit` | Returns `(engine, pipeline)` when all steps succeed. | Patch `model_lens.config.load` to return a valid `AppConfig`. Patch `resolve_dist_dir` to return a tmp dir containing `index.html` (created programmatically in fixture). Patch `YOLOInferenceEngine` constructor to return a mock engine with `get_label_map()` returning `{0: "person"}`. Patch `DetectionPipeline` constructor to return a mock pipeline. Mock `pipeline.start()` to succeed. | | Returns a tuple `(engine, pipeline)` |

### Error Propagation

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_startup_config_load_configuration_error` | `unit` | Raises `_StartupExit(1)` when `load()` raises `ConfigurationError`. | Patch `model_lens.config.load` to raise `ConfigurationError`. | | Raises `_StartupExit` with code `1` |
| `test_startup_config_load_file_not_found` | `unit` | Raises `_StartupExit(1)` when `load()` raises `FileNotFoundError`. | Patch `model_lens.config.load` to raise `FileNotFoundError`. | | Raises `_StartupExit` with code `1` |
| `test_startup_dist_dir_not_found` | `unit` | Raises `_StartupExit(1)` when `resolve_dist_dir()` raises `FileNotFoundError`. | Patch `model_lens.config.load` to succeed. Patch `resolve_dist_dir` to raise `FileNotFoundError`. | | Raises `_StartupExit` with code `1` |
| `test_startup_index_html_missing` | `unit` | Raises `_StartupExit(1)` when `dist/index.html` does not exist. | Patch `model_lens.config.load` to succeed. Patch `resolve_dist_dir` to return a tmp dir (created in fixture) that does NOT contain `index.html`. | | Raises `_StartupExit` with code `1` |
| `test_startup_engine_configuration_error` | `unit` | Raises `_StartupExit(1)` when `YOLOInferenceEngine` raises `ConfigurationError`. | Patch `load` to succeed, `resolve_dist_dir` to return valid dir with `index.html`. Patch `YOLOInferenceEngine` to raise `ConfigurationError`. | | Raises `_StartupExit` with code `1` |
| `test_startup_engine_operation_error` | `unit` | Raises `_StartupExit(1)` when `YOLOInferenceEngine` raises `OperationError`. | Patch `load` to succeed, `resolve_dist_dir` to return valid dir with `index.html`. Patch `YOLOInferenceEngine` to raise `OperationError`. | | Raises `_StartupExit` with code `1` |
| `test_startup_pipeline_start_failure_calls_stop` | `unit` | Calls `pipeline.stop()` then raises `_StartupExit(1)` when `pipeline.start()` raises. | Patch all preceding steps to succeed. Patch `pipeline.start()` to raise `RuntimeError`. | | `pipeline.stop()` is called; raises `_StartupExit` with code `1` |

---

## `lifespan`

### Happy Path — lifespan

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_lifespan_sets_state_and_yields` | `unit` | Sets `app.state.pipeline` and `app.state.engine` then yields. | Patch `_startup` to return `(mock_engine, mock_pipeline)`. Create a FastAPI app with no pre-set state. | | After entering lifespan context, `app.state.pipeline` is `mock_pipeline` and `app.state.engine` is `mock_engine` |

### State Transitions

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_lifespan_skips_when_pipeline_preset` | `unit` | Yields immediately without running startup or shutdown when `app.state.pipeline` is already set. | Create a FastAPI app and pre-set `app.state.pipeline` to a mock. Patch `_startup` to track calls. | | `_startup` is never called; lifespan context completes without error |

### Resource Cleanup

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_lifespan_shutdown_calls_stop_then_teardown` | `unit` | On shutdown, calls `pipeline.stop()` then `engine.teardown()` in order. | Patch `_startup` to return `(mock_engine, mock_pipeline)`. Use a call recorder (e.g., `Mock` with ordered assertions). | | `pipeline.stop()` is called before `engine.teardown()` |

---

## `create_app`

### Happy Path — create_app

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_create_app_includes_health_router` | `unit` | The app contains the `/healthz` route. | Patch `resolve_dist_dir` to return a tmp dir (created in fixture) containing an `assets/` subdirectory and `favicon.svg` and `index.html`. | | A route matching `GET /healthz` exists in `app.routes` |
| `test_create_app_includes_config_router` | `unit` | The app contains the `/config` route. | Same as above. | | A route matching `GET /config` exists in `app.routes` |
| `test_create_app_includes_stream_router` | `unit` | The app contains the `/stream` route. | Same as above. | | A route matching `GET /stream` exists in `app.routes` |

### Happy Path — GET /

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_get_index_returns_html_with_etag` | `unit` | Returns `index.html` content with correct Content-Type and ETag header. | Patch `resolve_dist_dir` to return a tmp dir with `index.html` containing known bytes (e.g., `b"<html></html>"`). Create `TestClient` with `app.state.pipeline` set to bypass lifespan. | `GET /` | Response status `200`; `Content-Type` is `text/html`; `etag` header equals `'"' + md5(b"<html></html>").hexdigest() + '"'` |

### Happy Path — GET /favicon.svg

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_get_favicon_returns_svg` | `unit` | Returns favicon with SVG media type. | Patch `resolve_dist_dir` to return a tmp dir containing `favicon.svg` with known content. Create `TestClient` with lifespan bypassed. | `GET /favicon.svg` | Response status `200`; `Content-Type` contains `image/svg+xml` |

### Happy Path — Static Assets

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_create_app_mounts_static_assets` | `unit` | Mounts `/assets` when `dist/assets/` directory exists. | Patch `resolve_dist_dir` to return a tmp dir containing an `assets/` subdirectory with a file inside. Create `TestClient` with lifespan bypassed. | `GET /assets/<filename>` | Response status `200`; file content is served |

### Error Propagation

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_create_app_no_static_when_dist_missing` | `unit` | Skips static route mounting when `resolve_dist_dir()` raises `FileNotFoundError`. | Patch `resolve_dist_dir` to raise `FileNotFoundError`. | | `create_app()` succeeds; no `/assets` route mounted; API routes still present |
| `test_create_app_no_assets_mount_when_assets_dir_missing` | `unit` | Skips `/assets` mount when `dist/assets/` does not exist. | Patch `resolve_dist_dir` to return a tmp dir that does NOT contain an `assets/` subdirectory (but does contain `index.html` and `favicon.svg`). | | `create_app()` succeeds; no `/assets` route mounted |

### Happy Path — Exception Handlers

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_json_parse_error_returns_400` | `unit` | Returns 400 with empty body for malformed JSON in request body. | Create `TestClient` with lifespan bypassed. | `PUT /config/camera` with body `"not json{"` (invalid JSON, `Content-Type: application/json`) | Response status `400`; body is empty |
| `test_unhandled_exception_returns_500` | `unit` | Returns 500 with generic error JSON for unhandled exceptions. | Create `TestClient` with lifespan bypassed. Add a test route that raises an unhandled `RuntimeError`. | `GET /test-error` (the injected test route) | Response status `500`; JSON body is `{"detail": "Internal Server Error"}` |
| `test_validation_error_non_json_returns_422` | `unit` | Returns 422 for Pydantic validation errors that are not JSON parse errors. | Create `TestClient` with lifespan bypassed. | `PUT /config/camera` with body `{"camera": {"source_type": "invalid"}}` | Response status `422` |
