# Logic Specification: `config.py`

## Location

`src/model_lens/config.py`

---

## Purpose

Loads, merges, validates, and exposes the application configuration as an immutable `AppConfig`
object. Configuration is resolved from three sources in priority order (lowest to highest):

1. Built-in defaults (hard-coded in this module).
2. TOML config file (optional).
3. Environment variables (`ML_*`).

After `AppConfig` is constructed and validated, all paths are guaranteed to be resolvable and all
values are guaranteed to satisfy their constraints. Downstream components (`InferenceEngine`,
`DetectionPipeline`, etc.) may rely on this guarantee without re-validating.

---

## Public API

### `load(config_path: Path | None) -> AppConfig`

The single public entry point for configuration loading.

**Arguments:**

| Parameter | Type | Description |
|---|---|---|
| `config_path` | `Path \| None` | Absolute or relative path to a TOML config file, as parsed by the external entry point via `argparse`. `None` means no `--config` flag was supplied. |

**Behaviour:**

1. Resolve the effective config file path (see [Config File Resolution](#config-file-resolution)).
2. Load and parse the TOML file if one is found (see [TOML Parsing](#toml-parsing)).
3. Merge built-in defaults with TOML values (see [Merge Strategy](#merge-strategy)).
4. Apply environment variable overrides key-by-key (see [Environment Variable Overrides](#environment-variable-overrides)).
5. Resolve empty `model_path` and `labels_path` to their bundled package-data paths (see [Package-Data Path Resolution](#package-data-path-resolution)).
6. Construct and return `AppConfig`, which triggers `validate()` in `__post_init__`.

**Returns:** A fully validated, immutable `AppConfig` instance.

**Raises:**
- `ConfigurationError`: If any value fails validation (raised from `AppConfig.__post_init__` via `validate()`).
- `ConfigurationError`: If the TOML file exists but cannot be parsed.

---

## Data Classes

### `ServerConfig`

Frozen dataclass holding server-related settings.

| Field | Type | Default | Validation |
|---|---|---|---|
| `host` | `str` | `"0.0.0.0"` | Non-empty string |
| `port` | `int` | `8080` | `1 – 65535` |
| `log_level` | `str` | `"info"` | One of `"debug"`, `"info"`, `"warning"`, `"error"`, `"critical"` |

---

### `CameraConfig`

Frozen dataclass holding camera startup defaults.

| Field | Type | Default | Validation |
|---|---|---|---|
| `source_type` | `str` | `"local"` | One of `"local"`, `"rtsp"` |
| `device_index` | `int` | `0` | `>= 0` |
| `rtsp_url` | `str` | `""` | Non-empty when `source_type == "rtsp"` |

---

### `ModelConfig`

Frozen dataclass holding model-related settings.

| Field | Type | Default | Validation |
|---|---|---|---|
| `model_path` | `str` | `""` | Non-empty after package-data resolution; resolved path must exist |
| `labels_path` | `str` | `""` | Non-empty after package-data resolution; resolved path must exist |
| `confidence_threshold` | `float` | `0.5` | `0.0 < value <= 1.0` |

> **Note:** By the time `AppConfig` is constructed, `model_path` and `labels_path` are always
> non-empty absolute path strings. The empty-string default is only an intermediate state inside
> `ConfigLoader` before package-data resolution runs.

---

### `AppConfig`

Top-level frozen dataclass. Mirrors the TOML section structure.

| Field | Type | Description |
|---|---|---|
| `server` | `ServerConfig` | Server settings |
| `camera` | `CameraConfig` | Camera startup defaults |
| `model` | `ModelConfig` | Model settings (fixed at startup) |

`AppConfig` is decorated with `@dataclass(frozen=True)`.

`__post_init__` calls `validate(self)` immediately after construction. If validation fails,
`ConfigurationError` is raised before the object is returned to the caller.

---

## Internal Functions

### `validate(config: AppConfig) -> None`

Validates all fields across all nested config sections. Raises `ConfigurationError` on the first
violation found, with a message that identifies the key, the invalid value, and the constraint:

```
ConfigurationError: model.confidence_threshold must satisfy 0.0 < value <= 1.0, got 1.5
ConfigurationError: server.port must be between 1 and 65535, got 0
ConfigurationError: camera.rtsp_url must be non-empty when source_type is "rtsp"
```

Validation rules mirror the constraints defined in `spec/configuration.md`.

---

## Config File Resolution

When `load()` is called:

1. If `config_path` is not `None`, use it directly as the config file path.
2. If `config_path` is `None`, check for `model_lens.toml` in the **current working directory**
   (`Path.cwd() / "model_lens.toml"`).
3. If neither source yields a file:
   - Log a `WARNING`: `"No config file found; using built-in defaults."`
   - Continue with built-in defaults only.
4. If a config file is found (from either source):
   - Log an `INFO`: `"Loading config from {resolved_path}"`

---

## TOML Parsing

- Use `tomllib` (Python 3.11+ stdlib). No third-party TOML library is used.
- If the file exists but cannot be parsed (invalid TOML syntax), raise:
  ```
  ConfigurationError: Failed to parse config file at {path}: {tomllib error message}
  ```
- Only keys present in the TOML file override their corresponding defaults. Missing keys retain
  their built-in defaults.
- Unknown TOML keys (keys not in the schema) are **silently ignored**.

---

## Merge Strategy

Merging is performed **per key**, not per section. The algorithm is:

1. Start with a dict of all built-in defaults (all keys present).
2. For each key present in the parsed TOML dict, overwrite the corresponding default value.
3. Apply environment variable overrides (see next section).
4. Construct the nested dataclasses (`ServerConfig`, `CameraConfig`, `ModelConfig`) from the
   merged dict.
5. Construct `AppConfig` from the nested dataclasses.

---

## Environment Variable Overrides

After merging defaults and TOML values, each config key is checked against its corresponding
`ML_<SECTION>_<KEY>` environment variable. If the variable is set and non-empty, its value
overrides the merged value.

Type coercion is applied before the override is stored:

| Target type | Coercion rule |
|---|---|
| `str` | Use the env var value as-is |
| `int` | Parse with `int()` |
| `float` | Parse with `float()` |
| `bool` | `"true"` / `"1"` → `True`; `"false"` / `"0"` → `False` (case-insensitive) |

If coercion fails (e.g., `ML_SERVER_PORT=abc`), raise:
```
ConfigurationError: Environment variable ML_SERVER_PORT cannot be coerced to int, got "abc"
```

Full mapping of environment variables to config keys:

| Environment variable | Config key |
|---|---|
| `ML_SERVER_HOST` | `server.host` |
| `ML_SERVER_PORT` | `server.port` |
| `ML_SERVER_LOG_LEVEL` | `server.log_level` |
| `ML_CAMERA_SOURCE_TYPE` | `camera.source_type` |
| `ML_CAMERA_DEVICE_INDEX` | `camera.device_index` |
| `ML_CAMERA_RTSP_URL` | `camera.rtsp_url` |
| `ML_MODEL_MODEL_PATH` | `model.model_path` |
| `ML_MODEL_LABELS_PATH` | `model.labels_path` |
| `ML_MODEL_CONFIDENCE_THRESHOLD` | `model.confidence_threshold` |

---

## Package-Data Path Resolution

After env var overrides are applied and before `AppConfig` is constructed:

- If `model.model_path` is an empty string, resolve it to the bundled package-data model file
  using `importlib.resources`.
- If `model.labels_path` is an empty string, resolve it to the bundled package-data label map
  file using `importlib.resources`.

The resolved paths are absolute path strings. After this step, both fields are guaranteed to be
non-empty. The existence of the resolved paths is verified by `validate()`.

If `importlib.resources` cannot locate the bundled file, raise:
```
ConfigurationError: Bundled model file could not be resolved from package data
ConfigurationError: Bundled labels file could not be resolved from package data
```

---

## Logging

One module-level logger is used:

```python
logger = logging.getLogger(__name__)
```

| Event | Level | Message |
|---|---|---|
| No config file found | `WARNING` | `"No config file found; using built-in defaults."` |
| Config file found and loaded | `INFO` | `"Loading config from {resolved_path}"` |
| Env var override applied | `DEBUG` | `"Env override: {env_var}={value!r} → {section}.{key}"` |
| Package-data path resolved | `DEBUG` | `"Resolved bundled {field} to {resolved_path}"` |

---

## Error Handling

All errors raised by this module are `ConfigurationError` (from `model_lens.exceptions`).
No other exception type is raised publicly. Third-party exceptions (e.g., from `tomllib`) are
caught at the boundary and re-raised as `ConfigurationError`.

---

## Constraints and Assumptions

- `load()` is called **once** at server startup. The returned `AppConfig` is immutable and shared
  read-only across the application.
- `AppConfig` does **not** seed `RuntimeConfig` directly; that responsibility belongs to the
  server startup sequence (`app.py` lifespan).
- This module has **no dependency** on FastAPI, OpenCV, or any inference library.
- `tomllib` is the only stdlib module used for parsing; no third-party TOML library is permitted.
