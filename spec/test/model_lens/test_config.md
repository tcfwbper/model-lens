# Test Specification: `test/model_lens/test_config.md`

## Source File Under Test

`src/model_lens/config.py`

## Test File

`test/model_lens/test_config.py`

## Imports Required

```python
import os
import sys
import tomllib
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from model_lens.config import (
    AppConfig,
    CameraConfig,
    ModelConfig,
    ServerConfig,
    load,
    validate,
)
from model_lens.exceptions import ConfigurationError
```

---

## 1. `ServerConfig`

### 1.1 Happy Path — Default Construction

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_server_config_default_host` | Default host is `"0.0.0.0"` | `ServerConfig()` | `instance.host == "0.0.0.0"` |
| `test_server_config_default_port` | Default port is `8080` | `ServerConfig()` | `instance.port == 8080` |
| `test_server_config_default_log_level` | Default log level is `"info"` | `ServerConfig()` | `instance.log_level == "info"` |

### 1.2 Happy Path — Explicit Construction

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_server_config_explicit_host` | Custom host is stored | `ServerConfig(host="127.0.0.1", port=8080, log_level="info")` | `instance.host == "127.0.0.1"` |
| `test_server_config_explicit_port` | Custom port is stored | `ServerConfig(host="0.0.0.0", port=9090, log_level="info")` | `instance.port == 9090` |
| `test_server_config_explicit_log_level` | Custom log level is stored | `ServerConfig(host="0.0.0.0", port=8080, log_level="debug")` | `instance.log_level == "debug"` |

### 1.3 Immutability

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_server_config_host_is_immutable` | Assigning to `host` raises | `instance.host = "localhost"` on a constructed `ServerConfig()` | `raises FrozenInstanceError` |
| `test_server_config_port_is_immutable` | Assigning to `port` raises | `instance.port = 1234` on a constructed `ServerConfig()` | `raises FrozenInstanceError` |
| `test_server_config_log_level_is_immutable` | Assigning to `log_level` raises | `instance.log_level = "error"` on a constructed `ServerConfig()` | `raises FrozenInstanceError` |

---

## 2. `config.CameraConfig`

> **Note:** This is `model_lens.config.CameraConfig`, not `model_lens.entities.CameraConfig`.
> These are two distinct classes. The config-layer `CameraConfig` holds startup defaults and
> includes a `source_type` discriminator field; the entities-layer `CameraConfig` is an abstract
> base class for `LocalCameraConfig` / `RtspCameraConfig`.

### 2.1 Happy Path — Default Construction

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_config_camera_config_default_source_type` | Default source type is `"local"` | `CameraConfig()` | `instance.source_type == "local"` |
| `test_config_camera_config_default_device_index` | Default device index is `0` | `CameraConfig()` | `instance.device_index == 0` |
| `test_config_camera_config_default_rtsp_url` | Default RTSP URL is `""` | `CameraConfig()` | `instance.rtsp_url == ""` |

### 2.2 Happy Path — Explicit Construction

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_config_camera_config_explicit_source_type_rtsp` | RTSP source type is stored | `CameraConfig(source_type="rtsp", device_index=0, rtsp_url="rtsp://host/stream")` | `instance.source_type == "rtsp"` |
| `test_config_camera_config_explicit_device_index` | Custom device index is stored | `CameraConfig(source_type="local", device_index=2, rtsp_url="")` | `instance.device_index == 2` |
| `test_config_camera_config_explicit_rtsp_url` | Custom RTSP URL is stored | `CameraConfig(source_type="rtsp", device_index=0, rtsp_url="rtsp://192.168.1.1/live")` | `instance.rtsp_url == "rtsp://192.168.1.1/live"` |

### 2.3 Immutability

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_config_camera_config_source_type_is_immutable` | Assigning to `source_type` raises | `instance.source_type = "rtsp"` on a constructed `CameraConfig()` | `raises FrozenInstanceError` |
| `test_config_camera_config_device_index_is_immutable` | Assigning to `device_index` raises | `instance.device_index = 1` on a constructed `CameraConfig()` | `raises FrozenInstanceError` |
| `test_config_camera_config_rtsp_url_is_immutable` | Assigning to `rtsp_url` raises | `instance.rtsp_url = "rtsp://x"` on a constructed `CameraConfig()` | `raises FrozenInstanceError` |

---

## 3. `ModelConfig`

### 3.1 Happy Path — Default Construction

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_model_config_default_model_path` | Default model path is `""` | `ModelConfig()` | `instance.model_path == ""` |
| `test_model_config_default_labels_path` | Default labels path is `""` | `ModelConfig()` | `instance.labels_path == ""` |
| `test_model_config_default_confidence_threshold` | Default confidence threshold is `0.5` | `ModelConfig()` | `instance.confidence_threshold == 0.5` |

### 3.2 Happy Path — Explicit Construction

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_model_config_explicit_model_path` | Custom model path is stored | `ModelConfig(model_path="/a/b/model.tflite", labels_path="/a/b/labels.txt", confidence_threshold=0.5)` | `instance.model_path == "/a/b/model.tflite"` |
| `test_model_config_explicit_labels_path` | Custom labels path is stored | `ModelConfig(model_path="/a/b/model.tflite", labels_path="/a/b/labels.txt", confidence_threshold=0.5)` | `instance.labels_path == "/a/b/labels.txt"` |
| `test_model_config_explicit_confidence_threshold` | Custom confidence threshold is stored | `ModelConfig(model_path="/a/b/model.tflite", labels_path="/a/b/labels.txt", confidence_threshold=0.9)` | `instance.confidence_threshold == 0.9` |

### 3.3 Immutability

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_model_config_model_path_is_immutable` | Assigning to `model_path` raises | `instance.model_path = "/new"` on a constructed `ModelConfig()` | `raises FrozenInstanceError` |
| `test_model_config_labels_path_is_immutable` | Assigning to `labels_path` raises | `instance.labels_path = "/new"` on a constructed `ModelConfig()` | `raises FrozenInstanceError` |
| `test_model_config_confidence_threshold_is_immutable` | Assigning to `confidence_threshold` raises | `instance.confidence_threshold = 0.9` on a constructed `ModelConfig()` | `raises FrozenInstanceError` |

---

## 4. `AppConfig`

### 4.1 Happy Path — Construction

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_app_config_stores_server` | `server` field is stored correctly | `AppConfig(server=ServerConfig(), camera=CameraConfig(), model=ModelConfig(model_path="/m", labels_path="/l", confidence_threshold=0.5))` with mocked path existence | `instance.server == ServerConfig()` |
| `test_app_config_stores_camera` | `camera` field is stored correctly | same as above | `instance.camera == CameraConfig()` |
| `test_app_config_stores_model` | `model` field is stored correctly | same as above | `instance.model.confidence_threshold == 0.5` |

### 4.2 Immutability

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_app_config_server_is_immutable` | Assigning to `server` raises | `instance.server = ServerConfig()` on a constructed `AppConfig` | `raises FrozenInstanceError` |
| `test_app_config_camera_is_immutable` | Assigning to `camera` raises | `instance.camera = CameraConfig()` on a constructed `AppConfig` | `raises FrozenInstanceError` |
| `test_app_config_model_is_immutable` | Assigning to `model` raises | `instance.model = ModelConfig()` on a constructed `AppConfig` | `raises FrozenInstanceError` |

---

## 5. `validate()`

> **Note:** `validate()` is imported directly as `from model_lens.config import validate`.
> It is also exercised indirectly through every `AppConfig` construction test.

### 5.1 Happy Path — Valid Config

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_validate_valid_config_returns_none` | `validate()` returns `None` for a fully valid config | A fully constructed valid `AppConfig` with mocked path existence | `returns None` |

### 5.2 Validation Failures — `server.host`

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_validate_server_host_empty_raises` | Empty host raises `ConfigurationError` | `AppConfig` with `ServerConfig(host="", ...)` | `raises ConfigurationError("server.host must be non-empty")` |

### 5.3 Validation Failures — `server.port`

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_validate_server_port_zero_raises` | Port `0` raises `ConfigurationError` | `AppConfig` with `ServerConfig(port=0, ...)` | `raises ConfigurationError("server.port must be between 1 and 65535, got 0")` |
| `test_validate_server_port_negative_raises` | Negative port raises `ConfigurationError` | `AppConfig` with `ServerConfig(port=-1, ...)` | `raises ConfigurationError("server.port must be between 1 and 65535, got -1")` |
| `test_validate_server_port_above_max_raises` | Port `65536` raises `ConfigurationError` | `AppConfig` with `ServerConfig(port=65536, ...)` | `raises ConfigurationError("server.port must be between 1 and 65535, got 65536")` |
| `test_validate_server_port_min_boundary_valid` | Port `1` is valid | `AppConfig` with `ServerConfig(port=1, ...)` | does not raise |
| `test_validate_server_port_max_boundary_valid` | Port `65535` is valid | `AppConfig` with `ServerConfig(port=65535, ...)` | does not raise |

### 5.4 Validation Failures — `server.log_level`

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_validate_server_log_level_invalid_raises` | Unknown log level raises `ConfigurationError` | `AppConfig` with `ServerConfig(log_level="verbose", ...)` | `raises ConfigurationError('server.log_level must be one of "debug", "info", "warning", "error", "critical", got "verbose"')` |
| `test_validate_server_log_level_debug_valid` | `"debug"` is valid | `AppConfig` with `ServerConfig(log_level="debug", ...)` | does not raise |
| `test_validate_server_log_level_warning_valid` | `"warning"` is valid | `AppConfig` with `ServerConfig(log_level="warning", ...)` | does not raise |
| `test_validate_server_log_level_error_valid` | `"error"` is valid | `AppConfig` with `ServerConfig(log_level="error", ...)` | does not raise |
| `test_validate_server_log_level_critical_valid` | `"critical"` is valid | `AppConfig` with `ServerConfig(log_level="critical", ...)` | does not raise |

### 5.5 Validation Failures — `camera.source_type`

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_validate_camera_source_type_invalid_raises` | Unknown source type raises `ConfigurationError` | `AppConfig` with `CameraConfig(source_type="usb", ...)` | `raises ConfigurationError('camera.source_type must be one of "local", "rtsp", got "usb"')` |

### 5.6 Validation Failures — `camera.device_index`

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_validate_camera_device_index_negative_raises` | Negative device index raises `ConfigurationError` | `AppConfig` with `CameraConfig(device_index=-1, ...)` | `raises ConfigurationError("camera.device_index must be >= 0, got -1")` |
| `test_validate_camera_device_index_zero_valid` | Device index `0` is valid | `AppConfig` with `CameraConfig(device_index=0, ...)` | does not raise |

### 5.7 Validation Failures — `camera.rtsp_url`

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_validate_camera_rtsp_url_empty_when_rtsp_raises` | Empty RTSP URL with `source_type="rtsp"` raises `ConfigurationError` | `AppConfig` with `CameraConfig(source_type="rtsp", rtsp_url="", ...)` | `raises ConfigurationError('camera.rtsp_url must be non-empty when source_type is "rtsp"')` |
| `test_validate_camera_rtsp_url_empty_when_local_valid` | Empty RTSP URL with `source_type="local"` is valid | `AppConfig` with `CameraConfig(source_type="local", rtsp_url="", ...)` | does not raise |

### 5.8 Validation Failures — `model.model_path`

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_validate_model_path_empty_raises` | Empty model path raises `ConfigurationError` | `AppConfig` with `ModelConfig(model_path="", ...)` | `raises ConfigurationError("model.model_path must be non-empty")` |
| `test_validate_model_path_not_exist_raises` | Non-existent model path raises `ConfigurationError` | `AppConfig` with `ModelConfig(model_path="/nonexistent/model.tflite", ...)` | `raises ConfigurationError('model.model_path does not exist: "/nonexistent/model.tflite"')` |

### 5.9 Validation Failures — `model.labels_path`

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_validate_labels_path_empty_raises` | Empty labels path raises `ConfigurationError` | `AppConfig` with `ModelConfig(labels_path="", ...)` | `raises ConfigurationError("model.labels_path must be non-empty")` |
| `test_validate_labels_path_not_exist_raises` | Non-existent labels path raises `ConfigurationError` | `AppConfig` with `ModelConfig(labels_path="/nonexistent/labels.txt", ...)` | `raises ConfigurationError('model.labels_path does not exist: "/nonexistent/labels.txt"')` |

### 5.10 Validation Failures — `model.confidence_threshold`

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_validate_confidence_threshold_zero_raises` | Threshold `0.0` raises `ConfigurationError` | `AppConfig` with `ModelConfig(confidence_threshold=0.0, ...)` | `raises ConfigurationError("model.confidence_threshold must satisfy 0.0 < value <= 1.0, got 0.0")` |
| `test_validate_confidence_threshold_negative_raises` | Negative threshold raises `ConfigurationError` | `AppConfig` with `ModelConfig(confidence_threshold=-0.1, ...)` | `raises ConfigurationError("model.confidence_threshold must satisfy 0.0 < value <= 1.0, got -0.1")` |
| `test_validate_confidence_threshold_above_one_raises` | Threshold `1.5` raises `ConfigurationError` | `AppConfig` with `ModelConfig(confidence_threshold=1.5, ...)` | `raises ConfigurationError("model.confidence_threshold must satisfy 0.0 < value <= 1.0, got 1.5")` |
| `test_validate_confidence_threshold_min_boundary_valid` | Threshold just above `0.0` (`0.01`) is valid | `AppConfig` with `ModelConfig(confidence_threshold=0.01, ...)` | does not raise |
| `test_validate_confidence_threshold_max_boundary_valid` | Threshold exactly `1.0` is valid | `AppConfig` with `ModelConfig(confidence_threshold=1.0, ...)` | does not raise |

---

## 6. `load()` — Config File Resolution

> All `load()` tests patch `sys.argv` to control CLI arguments, use `tmp_path` + `os.chdir()` to
> control the working directory, and mock `importlib.resources` to avoid real filesystem
> dependency for bundled package-data files. File existence checks for user-supplied paths are
> satisfied by creating real files inside `tmp_path`.

### 6.1 Happy Path — No Config File

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_load_no_config_file_uses_defaults` | When no `--config` flag and no `model_lens.toml` in cwd, built-in defaults are used | `sys.argv = ["prog"]`; cwd has no `model_lens.toml`; bundled paths mocked | returned `AppConfig.server.port == 8080` |
| `test_load_no_config_file_logs_warning` | Warning is logged when no config file is found | same as above | `logger.warning` called with `"No config file found; using built-in defaults."` |

### 6.2 Happy Path — Default Config File Discovery

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_load_default_config_file_discovered` | `model_lens.toml` in cwd is loaded automatically | `sys.argv = ["prog"]`; `model_lens.toml` written to `tmp_path`; `os.chdir(tmp_path)` | returned `AppConfig` reflects values from the TOML file |
| `test_load_default_config_file_logs_info` | Info is logged when config file is found | same as above | `logger.info` called with `f"Loading config from {tmp_path / 'model_lens.toml'}"` |

### 6.3 Happy Path — Explicit `--config` Flag

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_load_explicit_config_flag_loads_file` | `--config` path is loaded | `sys.argv = ["prog", "--config", str(config_file)]`; file written to `tmp_path` | returned `AppConfig` reflects values from the specified file |
| `test_load_explicit_config_flag_logs_info` | Info is logged for explicit config path | same as above | `logger.info` called with `f"Loading config from {config_file}"` |

### 6.4 Happy Path — TOML Partial Override

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_load_toml_overrides_server_port` | TOML `[server] port = 9090` overrides default | TOML file with `[server]\nport = 9090`; bundled paths mocked | `AppConfig.server.port == 9090` |
| `test_load_toml_overrides_camera_source_type` | TOML `[camera] source_type = "rtsp"` overrides default | TOML file with `[camera]\nsource_type = "rtsp"\nrtsp_url = "rtsp://host/s"`; bundled paths mocked | `AppConfig.camera.source_type == "rtsp"` |
| `test_load_toml_overrides_confidence_threshold` | TOML `[model] confidence_threshold = 0.8` overrides default | TOML file with `[model]\nconfidence_threshold = 0.8`; bundled paths mocked | `AppConfig.model.confidence_threshold == 0.8` |
| `test_load_toml_unknown_keys_ignored` | Unknown TOML keys do not raise | TOML file containing `[server]\nunknown_key = "x"`; bundled paths mocked | does not raise |
| `test_load_toml_missing_keys_retain_defaults` | Keys absent from TOML retain built-in defaults | TOML file with only `[server]\nport = 9090`; bundled paths mocked | `AppConfig.server.host == "0.0.0.0"` |

### 6.5 TOML Parse Error

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_load_invalid_toml_raises` | Malformed TOML raises `ConfigurationError` | Config file containing `not valid toml :::` | `raises ConfigurationError` with message starting `"Failed to parse config file at "` |

---

## 7. `load()` — Environment Variable Overrides

> Each test patches the relevant `ML_*` environment variable via `monkeypatch.setenv` and mocks
> bundled paths. A minimal valid TOML (or no TOML) is used as the base.

### 7.1 Happy Path — Env Var Overrides

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_load_env_override_server_host` | `ML_SERVER_HOST` overrides host | `ML_SERVER_HOST="192.168.0.1"` | `AppConfig.server.host == "192.168.0.1"` |
| `test_load_env_override_server_port` | `ML_SERVER_PORT` overrides port | `ML_SERVER_PORT="9999"` | `AppConfig.server.port == 9999` |
| `test_load_env_override_server_log_level` | `ML_SERVER_LOG_LEVEL` overrides log level | `ML_SERVER_LOG_LEVEL="debug"` | `AppConfig.server.log_level == "debug"` |
| `test_load_env_override_camera_source_type` | `ML_CAMERA_SOURCE_TYPE` overrides source type | `ML_CAMERA_SOURCE_TYPE="rtsp"` and `ML_CAMERA_RTSP_URL="rtsp://h/s"` | `AppConfig.camera.source_type == "rtsp"` |
| `test_load_env_override_camera_device_index` | `ML_CAMERA_DEVICE_INDEX` overrides device index | `ML_CAMERA_DEVICE_INDEX="2"` | `AppConfig.camera.device_index == 2` |
| `test_load_env_override_camera_rtsp_url` | `ML_CAMERA_RTSP_URL` overrides RTSP URL | `ML_CAMERA_SOURCE_TYPE="rtsp"` and `ML_CAMERA_RTSP_URL="rtsp://cam/live"` | `AppConfig.camera.rtsp_url == "rtsp://cam/live"` |
| `test_load_env_override_model_model_path` | `ML_MODEL_MODEL_PATH` overrides model path | `ML_MODEL_MODEL_PATH=str(existing_file)` | `AppConfig.model.model_path == str(existing_file)` |
| `test_load_env_override_model_labels_path` | `ML_MODEL_LABELS_PATH` overrides labels path | `ML_MODEL_LABELS_PATH=str(existing_file)` | `AppConfig.model.labels_path == str(existing_file)` |
| `test_load_env_override_model_confidence_threshold` | `ML_MODEL_CONFIDENCE_THRESHOLD` overrides threshold | `ML_MODEL_CONFIDENCE_THRESHOLD="0.75"` | `AppConfig.model.confidence_threshold == 0.75` |
| `test_load_env_override_logs_debug` | Debug log is emitted for each env override applied | `ML_SERVER_PORT="9999"` | `logger.debug` called with `'Env override: ML_SERVER_PORT="9999" → server.port'` |

### 7.2 Env Var Coercion Failures

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_load_env_coercion_int_failure_raises` | Non-integer value for an `int` field raises `ConfigurationError` | `ML_SERVER_PORT="abc"` | `raises ConfigurationError` with message containing `"ML_SERVER_PORT"`, `"int"`, and `"abc"` |
| `test_load_env_coercion_float_failure_raises` | Non-float value for a `float` field raises `ConfigurationError` | `ML_MODEL_CONFIDENCE_THRESHOLD="xyz"` | `raises ConfigurationError` with message containing `"ML_MODEL_CONFIDENCE_THRESHOLD"`, `"float"`, and `"xyz"` |
| `test_load_env_coercion_str_no_failure` | String env var is always accepted as-is | `ML_SERVER_HOST="any-string"` | does not raise; `AppConfig.server.host == "any-string"` |

> **Note:** The current config schema contains no `bool`-typed fields, so coercion tests for bool types are not applicable.

---

## 8. `load()` — Package-Data Path Resolution

> All tests in this section mock `importlib.resources` to avoid real filesystem dependency.

### 8.1 Happy Path — Bundled Path Resolution

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_load_resolves_bundled_model_path_when_empty` | Empty `model_path` is resolved to bundled path | `model_path` not set in TOML or env; `importlib.resources` mocked to return `"/bundled/model.tflite"` | `AppConfig.model.model_path == "/bundled/model.tflite"` |
| `test_load_resolves_bundled_labels_path_when_empty` | Empty `labels_path` is resolved to bundled path | `labels_path` not set in TOML or env; `importlib.resources` mocked to return `"/bundled/labels.txt"` | `AppConfig.model.labels_path == "/bundled/labels.txt"` |
| `test_load_skips_bundled_resolution_when_model_path_set` | Non-empty `model_path` skips bundled resolution | `ML_MODEL_MODEL_PATH=str(existing_file)`; `importlib.resources` mock not called for model | `importlib.resources` not called for model path resolution |
| `test_load_skips_bundled_resolution_when_labels_path_set` | Non-empty `labels_path` skips bundled resolution | `ML_MODEL_LABELS_PATH=str(existing_file)`; `importlib.resources` mock not called for labels | `importlib.resources` not called for labels path resolution |
| `test_load_bundled_resolution_logs_debug` | Debug log is emitted when bundled path is resolved | bundled model path resolved | `logger.debug` called with `f"Resolved bundled model_path to /bundled/model.tflite"` |

### 8.2 Bundled Path Resolution Failures

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_load_bundled_model_path_not_found_raises` | `importlib.resources` failure for model raises `ConfigurationError` | `importlib.resources` raises for model file | `raises ConfigurationError("Bundled model file could not be resolved from package data")` |
| `test_load_bundled_labels_path_not_found_raises` | `importlib.resources` failure for labels raises `ConfigurationError` | `importlib.resources` raises for labels file | `raises ConfigurationError("Bundled labels file could not be resolved from package data")` |

---

## Summary Table

| Entity | Test Count (approx.) | Key Concerns |
|---|---|---|
| `ServerConfig` | 9 | default values, explicit construction, frozen immutability |
| `config.CameraConfig` | 9 | default values, explicit construction, frozen immutability |
| `ModelConfig` | 9 | default values, explicit construction, frozen immutability |
| `AppConfig` | 6 | field storage, frozen immutability, `validate()` called on construction |
| `validate()` | 24 | all field constraints, boundary values, exact error messages |
| `load()` — file resolution | 10 | no file, cwd discovery, explicit `--config`, TOML parse error |
| `load()` — TOML merging | 5 | partial override, unknown keys ignored, missing keys retain defaults |
| `load()` — env var overrides | 10 | all 9 env vars, coercion for int/float/str, debug logging |
| `load()` — package-data resolution | 7 | bundled path resolved, skipped when set, failure cases, debug logging |
