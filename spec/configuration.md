# Configuration Specification for ModelLens

## Core Principle

ModelLens is configured through a **single TOML config file**.
Every key has a built-in default; the config file only needs to contain values that differ from defaults.
Environment variables can override any config-file value and take the highest precedence.

---

## Config File Format

The config file is TOML. The canonical template ships with every release and has **all value keys commented out** (section headers are left active).
Users uncomment and edit only the keys they need.

Template (`model_lens.toml.template`):

```toml
## ModelLens Configuration
##! All keys are optional. Uncomment a line to override its default value.
##! Keys not present in this file use the built-in default shown here.

###############################################################################
## Server
###############################################################################

[server]

##! Host address the HTTP server binds to.
# host = "0.0.0.0"

##! Port the HTTP server listens on.
# port = 8080

##! Logging level. One of: "debug", "info", "warning", "error", "critical".
# log_level = "info"

###############################################################################
## Camera (startup defaults; can be changed at runtime via the Config API)
###############################################################################

[camera]

##! Camera source type. One of: "local", "rtsp".
# source_type = "local"

##! Device index for local webcam (used when source_type = "local").
# device_index = 0

##! RTSP stream URL (used when source_type = "rtsp").
# rtsp_url = ""

###############################################################################
## Model
###############################################################################

[model]

##! Path to the bundled model file. Defaults to the package-data path.
# model_path = ""

##! Path to the label map file (plain text, one label per line). Defaults to the package-data path.
# labels_path = ""

##! Minimum confidence score for a detection to be reported (0.0 – 1.0).
# confidence_threshold = 0.5
```

---

## Configuration Loading Order

Configuration is resolved in the following priority order (higher number wins):

| Priority | Source | Description |
|:---:|---|---|
| 1 | Built-in defaults | Hard-coded in `src/model_lens/config.py`; always present |
| 2 | Config file | Values explicitly set in the TOML file override defaults |
| 3 | Environment variables | `ML_*` vars override both defaults and config-file values |

The config file path is the **only** value accepted from the command line:

```
model_lens --config=/path/to/model_lens.toml
```

If `--config` is omitted, ModelLens looks for `model_lens.toml` in the current working directory.
If neither is found, all built-in defaults apply.

---

## Environment Variable Convention

Every config key has a corresponding environment variable formed by:

```
ML_<SECTION>_<KEY>   (all uppercase, dots and hyphens replaced with underscores)
```

Examples:

| Config key (TOML) | Environment variable |
|---|---|
| `server.host` | `ML_SERVER_HOST` |
| `server.port` | `ML_SERVER_PORT` |
| `server.log_level` | `ML_SERVER_LOG_LEVEL` |
| `camera.source_type` | `ML_CAMERA_SOURCE_TYPE` |
| `camera.device_index` | `ML_CAMERA_DEVICE_INDEX` |
| `camera.rtsp_url` | `ML_CAMERA_RTSP_URL` |
| `model.model_path` | `ML_MODEL_MODEL_PATH` |
| `model.labels_path` | `ML_MODEL_LABELS_PATH` |
| `model.confidence_threshold` | `ML_MODEL_CONFIDENCE_THRESHOLD` |

Type coercion rules for env vars:

| TOML type | Accepted env var values |
|---|---|
| `str` | Any string value |
| `int` | Decimal integer string, e.g. `"0"` |
| `float` | Decimal float string, e.g. `"0.5"` |
| `bool` | Case-insensitive `"true"` / `"false"` / `"1"` / `"0"` |

---

## All Configuration Keys

### `[server]`

| Key | Type | Default | Validation |
|---|---|---|---|
| `host` | `str` | `"0.0.0.0"` | Non-empty string |
| `port` | `int` | `8080` | `1 – 65535` |
| `log_level` | `str` | `"info"` | One of `debug`, `info`, `warning`, `error`, `critical` |

### `[camera]`

Startup defaults for `CameraConfig`. These values seed the in-memory `RuntimeConfig` on first boot and can be changed at runtime via the Config API without restarting the server.

| Key | Type | Default | Validation |
|---|---|---|---|
| `source_type` | `str` | `"local"` | One of `local`, `rtsp` |
| `device_index` | `int` | `0` | `>= 0`; only used when `source_type = "local"` |
| `rtsp_url` | `str` | `""` | Non-empty when `source_type = "rtsp"` |

### `[model]`

Fixed at startup; cannot be changed at runtime.

| Key | Type | Default | Validation |
|---|---|---|---|
| `model_path` | `str` | `""` (resolves to package-data path) | Absolute path or empty string |
| `labels_path` | `str` | `""` (resolves to package-data path) | Absolute path or empty string |
| `confidence_threshold` | `float` | `0.5` | `0.0 < value <= 1.0` |

---

## Validation Rules

- Validation runs **once at startup**, after all sources are merged.
- Any validation failure raises `ConfigurationError` with a message that identifies the key, the
  invalid value, and the constraint that was violated.
- Example:

  ```
  ConfigurationError: model.confidence_threshold must satisfy 0.0 < value <= 1.0, got 1.5
  ```

- `camera.rtsp_url` is only validated (non-empty check) when `camera.source_type = "rtsp"`.
- `model.model_path` is only validated (path exists) when it is non-empty; an empty string causes
  the server to fall back to the bundled package-data model.
- `model.labels_path` is only validated (path exists) when it is non-empty; an empty string causes
  the server to fall back to the bundled package-data label map.

---

## Implementation Notes

- Config loading lives in `src/model_lens/config.py` (`ConfigLoader`, `AppConfig`).
- `AppConfig` is a frozen dataclass (`@dataclass(frozen=True)`) — configuration is immutable after startup.
- `tomllib` (stdlib, Python 3.11+) is used for TOML parsing; no additional dependency is required.
- `AppConfig` seeds the initial in-memory `RuntimeConfig` at server startup; from that point the
  Config API owns the runtime state and `AppConfig` is no longer consulted.
