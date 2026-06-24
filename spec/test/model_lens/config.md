# Test Specification: `test_config.py`

## Source File Under Test
`src/model_lens/config.py`

## Test File
`tests/model_lens/test_config.py`

---

## `load`

### Happy Path — load

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_load_defaults_when_no_config_file` | `unit` | Returns AppConfig with all built-in defaults when no TOML file exists and no env vars are set. | Monkeypatch `sys.argv` to `["prog"]`; monkeypatch `Path.cwd()` to a tmp dir without `model_lens.toml`; clear all `ML_*` env vars. | — | Returns `AppConfig` with `server.host=="0.0.0.0"`, `server.port==8080`, `server.log_level=="info"`, `camera.source_type=="local"`, `camera.device_index==0`, `camera.rtsp_url==""`, `model.model=="yolov8n"`, `model.confidence_threshold==0.5` |
| `test_load_reads_toml_from_cli_config_flag` | `unit` | Reads and applies the TOML file specified by `--config`. | Create a tmp TOML file with `[server]\nport = 9090`; monkeypatch `sys.argv` to `["prog", "--config", "<tmp_path>"]`; clear all `ML_*` env vars. | — | Returns `AppConfig` with `server.port==9090`; other fields use defaults. |
| `test_load_reads_toml_from_cwd` | `unit` | Reads `model_lens.toml` from the current working directory when no `--config` flag is provided. | Create `model_lens.toml` with `[model]\nmodel = "yolov8s"` in a tmp dir; monkeypatch `Path.cwd()` to that tmp dir; monkeypatch `sys.argv` to `["prog"]`; clear all `ML_*` env vars. | — | Returns `AppConfig` with `model.model=="yolov8s"`. |
| `test_load_env_var_overrides_toml_value` | `unit` | Environment variable takes precedence over TOML file value. | Create a tmp TOML file with `[server]\nport = 9090`; monkeypatch `sys.argv` to `["prog", "--config", "<tmp_path>"]`; monkeypatch `os.environ` with `ML_SERVER_PORT="7070"`. | — | Returns `AppConfig` with `server.port==7070`. |
| `test_load_env_var_overrides_default` | `unit` | Environment variable overrides built-in default when no TOML file exists. | Monkeypatch `sys.argv` to `["prog"]`; monkeypatch `Path.cwd()` to a tmp dir without `model_lens.toml`; monkeypatch `os.environ` with `ML_MODEL_CONFIDENCE_THRESHOLD="0.8"`. | — | Returns `AppConfig` with `model.confidence_threshold==0.8`. |
| `test_load_ignores_unknown_toml_keys` | `unit` | Unknown keys in TOML file are silently ignored. | Create a tmp TOML file with `[server]\nport = 9090\nunknown_key = "value"`; monkeypatch `sys.argv` to `["prog", "--config", "<tmp_path>"]`; clear all `ML_*` env vars. | — | Returns `AppConfig` with `server.port==9090`; no error raised. |
| `test_load_empty_toml_uses_defaults` | `unit` | An empty but valid TOML file results in all defaults. | Create an empty tmp TOML file; monkeypatch `sys.argv` to `["prog", "--config", "<tmp_path>"]`; clear all `ML_*` env vars. | — | Returns `AppConfig` with all default values; no error raised. |
| `test_load_ignores_unrecognized_argv` | `unit` | Unrecognized CLI arguments are ignored via `parse_known_args()`. | Monkeypatch `sys.argv` to `["prog", "--unknown-flag", "value"]`; monkeypatch `Path.cwd()` to a tmp dir without `model_lens.toml`; clear all `ML_*` env vars. | — | Returns `AppConfig` with all defaults; no error raised. |

### Error Propagation

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_load_raises_on_nonexistent_config_file` | `unit` | Raises ConfigurationError when `--config` points to a non-existent file. | Monkeypatch `sys.argv` to `["prog", "--config", "/nonexistent/path.toml"]`; clear all `ML_*` env vars. | — | Raises `ConfigurationError` with message containing "Failed to parse config file". |
| `test_load_raises_on_invalid_toml_syntax` | `unit` | Raises ConfigurationError wrapping the TOML parse error. | Create a tmp file with invalid TOML content (e.g., `[server\n`); monkeypatch `sys.argv` to `["prog", "--config", "<tmp_path>"]`; clear all `ML_*` env vars. | — | Raises `ConfigurationError`; `__cause__` is the original `tomllib` exception. |
| `test_load_raises_on_env_var_coercion_failure` | `unit` | Raises ConfigurationError when an env var cannot be coerced to the target type. | Monkeypatch `sys.argv` to `["prog"]`; monkeypatch `Path.cwd()` to a tmp dir without `model_lens.toml`; monkeypatch `os.environ` with `ML_SERVER_PORT="abc"`. | — | Raises `ConfigurationError` with message containing `Cannot coerce ML_SERVER_PORT="abc" to int`. |

### Mock / Dependency Interaction

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_load_logs_info_when_config_file_found` | `unit` | Logs at INFO level when a config file is successfully located. | Create a valid tmp TOML file; monkeypatch `sys.argv` to `["prog", "--config", "<tmp_path>"]`; capture log output at INFO level; clear all `ML_*` env vars. | — | INFO log message emitted referencing the config file path. |
| `test_load_logs_warning_when_no_config_file` | `unit` | Logs at WARNING level when no config file is found. | Monkeypatch `sys.argv` to `["prog"]`; monkeypatch `Path.cwd()` to a tmp dir without `model_lens.toml`; capture log output at WARNING level; clear all `ML_*` env vars. | — | WARNING log message emitted. |
| `test_load_logs_debug_for_each_env_override` | `unit` | Logs at DEBUG level for each applied environment variable override. | Monkeypatch `sys.argv` to `["prog"]`; monkeypatch `Path.cwd()` to a tmp dir without `model_lens.toml`; monkeypatch `os.environ` with `ML_SERVER_PORT="9090"` and `ML_MODEL_MODEL="yolov8s"`; capture log output at DEBUG level. | — | Two DEBUG log messages emitted, one per override. |

---

## `validate`

### Happy Path — validate

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_validate_accepts_valid_config` | `unit` | Returns None for a fully valid AppConfig. | — | `AppConfig` with all default values. | Returns `None`; no exception raised. |
| `test_validate_accepts_rtsp_with_non_empty_url` | `unit` | Passes when source_type is "rtsp" and rtsp_url is non-empty. | — | `AppConfig` with `camera.source_type="rtsp"`, `camera.rtsp_url="rtsp://host/stream"`. | Returns `None`; no exception raised. |

### Validation Failures — server.host

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_validate_rejects_empty_host` | `unit` | Raises ConfigurationError when server.host is empty. | — | `AppConfig` with `server.host=""`. | Raises `ConfigurationError` identifying `server.host` and the empty value. |

### Validation Failures — server.port

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_validate_rejects_port_zero` | `unit` | Raises ConfigurationError when server.port is 0. | — | `AppConfig` with `server.port=0`. | Raises `ConfigurationError` identifying `server.port`, value `0`, and constraint 1–65535. |
| `test_validate_rejects_port_above_65535` | `unit` | Raises ConfigurationError when server.port exceeds 65535. | — | `AppConfig` with `server.port=65536`. | Raises `ConfigurationError` identifying `server.port`, value `65536`, and constraint 1–65535. |

### Validation Failures — server.log_level

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_validate_rejects_invalid_log_level` | `unit` | Raises ConfigurationError for an unrecognized log level. | — | `AppConfig` with `server.log_level="verbose"`. | Raises `ConfigurationError` identifying `server.log_level` and the invalid value. |

### Validation Failures — camera.source_type

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_validate_rejects_invalid_source_type` | `unit` | Raises ConfigurationError for an unrecognized source type. | — | `AppConfig` with `camera.source_type="usb"`. | Raises `ConfigurationError` identifying `camera.source_type` and the invalid value. |

### Validation Failures — camera.device_index

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_validate_rejects_negative_device_index` | `unit` | Raises ConfigurationError when device_index is negative. | — | `AppConfig` with `camera.device_index=-1`. | Raises `ConfigurationError` identifying `camera.device_index` and the negative value. |

### Validation Failures — camera.rtsp_url

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_validate_rejects_empty_rtsp_url_when_rtsp` | `unit` | Raises ConfigurationError when source_type is "rtsp" but rtsp_url is empty. | — | `AppConfig` with `camera.source_type="rtsp"`, `camera.rtsp_url=""`. | Raises `ConfigurationError` identifying `camera.rtsp_url`. |

### Validation Failures — model.model

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_validate_rejects_empty_model_name` | `unit` | Raises ConfigurationError when model.model is empty. | — | `AppConfig` with `model.model=""`. | Raises `ConfigurationError` identifying `model.model` and the empty value. |

### Validation Failures — model.confidence_threshold

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_validate_rejects_threshold_zero` | `unit` | Raises ConfigurationError when confidence_threshold is 0.0. | — | `AppConfig` with `model.confidence_threshold=0.0`. | Raises `ConfigurationError` identifying `model.confidence_threshold` and constraint `0.0 < value <= 1.0`. |
| `test_validate_rejects_threshold_above_one` | `unit` | Raises ConfigurationError when confidence_threshold exceeds 1.0. | — | `AppConfig` with `model.confidence_threshold=1.1`. | Raises `ConfigurationError` identifying `model.confidence_threshold` and constraint `0.0 < value <= 1.0`. |
| `test_validate_rejects_negative_threshold` | `unit` | Raises ConfigurationError when confidence_threshold is negative. | — | `AppConfig` with `model.confidence_threshold=-0.1`. | Raises `ConfigurationError` identifying `model.confidence_threshold` and constraint `0.0 < value <= 1.0`. |

### Boundary Values — model.confidence_threshold

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_validate_accepts_threshold_at_one` | `unit` | Passes when confidence_threshold is exactly 1.0. | — | `AppConfig` with `model.confidence_threshold=1.0`. | Returns `None`; no exception raised. |
| `test_validate_accepts_threshold_just_above_zero` | `unit` | Passes when confidence_threshold is just above 0.0. | — | `AppConfig` with `model.confidence_threshold=0.001`. | Returns `None`; no exception raised. |

### Boundary Values — server.port

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_validate_accepts_port_one` | `unit` | Passes when server.port is exactly 1. | — | `AppConfig` with `server.port=1`. | Returns `None`; no exception raised. |
| `test_validate_accepts_port_65535` | `unit` | Passes when server.port is exactly 65535. | — | `AppConfig` with `server.port=65535`. | Returns `None`; no exception raised. |

---

## `ConfigLoader`

### Happy Path — load

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_config_loader_delegates_to_module_load` | `unit` | ConfigLoader.load() delegates to the module-level load() function. | Monkeypatch module-level `load()` to return a mock `AppConfig`. | `ConfigLoader().load()` | Returns the same mock `AppConfig` returned by the module-level `load()`. |

---

## `AppConfig`

### Immutability

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_app_config_is_frozen` | `unit` | Assignment to an AppConfig field raises FrozenInstanceError. | Construct a valid `AppConfig` with defaults. | Attempt `config.server = new_server_config`. | Raises `FrozenInstanceError` (or `dataclasses.FrozenInstanceError`). |
| `test_server_config_is_frozen` | `unit` | Assignment to a ServerConfig field raises FrozenInstanceError. | Construct a valid `ServerConfig` with defaults. | Attempt `server_config.port = 9090`. | Raises `FrozenInstanceError`. |
| `test_camera_config_is_frozen` | `unit` | Assignment to a CameraConfig field raises FrozenInstanceError. | Construct a valid `CameraConfig` with defaults. | Attempt `camera_config.device_index = 1`. | Raises `FrozenInstanceError`. |
| `test_model_config_is_frozen` | `unit` | Assignment to a ModelConfig field raises FrozenInstanceError. | Construct a valid `ModelConfig` with defaults. | Attempt `model_config.model = "other"`. | Raises `FrozenInstanceError`. |

---

## `load` — Environment Variable Coercion

### Happy Path — load

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_load_coerces_env_int` | `unit` | Coerces string env var to int for integer fields. | Monkeypatch `sys.argv` to `["prog"]`; monkeypatch `Path.cwd()` to a tmp dir without `model_lens.toml`; monkeypatch `os.environ` with `ML_CAMERA_DEVICE_INDEX="2"`. | — | Returns `AppConfig` with `camera.device_index==2`. |
| `test_load_coerces_env_float` | `unit` | Coerces string env var to float for float fields. | Monkeypatch `sys.argv` to `["prog"]`; monkeypatch `Path.cwd()` to a tmp dir without `model_lens.toml`; monkeypatch `os.environ` with `ML_MODEL_CONFIDENCE_THRESHOLD="0.75"`. | — | Returns `AppConfig` with `model.confidence_threshold==0.75`. |
| `test_load_applies_empty_string_env_var` | `unit` | Empty string env var is applied as override (triggers validation failure downstream). | Monkeypatch `sys.argv` to `["prog"]`; monkeypatch `Path.cwd()` to a tmp dir without `model_lens.toml`; monkeypatch `os.environ` with `ML_SERVER_HOST=""`. | — | Raises `ConfigurationError` because `server.host` is empty after env var override. |
