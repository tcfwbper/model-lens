# Config

## Overview

Loads, merges, validates, and exposes the application configuration as an immutable `AppConfig` object. Configuration is resolved from three sources in priority order (lowest to highest): built-in defaults, optional TOML config file, and environment variables (`ML_*`). After `AppConfig` is constructed and validated, all values are guaranteed to satisfy their constraints. This module does not seed `RuntimeConfig` or manage any runtime state.

## Boundaries

- Owns: loading configuration from CLI args, TOML file, and environment variables; merging them; validating the final result; exposing `AppConfig` and its nested frozen dataclasses.
- Owns: type coercion of environment variable string values to the target field type.
- Owns: filtering TOML keys to only those matching dataclass fields (unknown keys silently ignored).
- Delegates: startup usage of `AppConfig` to the server lifespan (the caller of `load()`).
- Delegates: runtime configuration (camera source, target labels) to the Config API and `RuntimeConfig`.
- Must not: import or depend on FastAPI, OpenCV, or any inference library.
- Must not: perform any I/O beyond reading the TOML file and environment variables.
- Must not: persist configuration or manage runtime state.

## Dependencies

| Collaborator | Role | Allowed Interaction | Forbidden Interaction |
|---|---|---|---|
| `model_lens.exceptions.ConfigurationError` | Error signaling | Raised on validation failure, TOML parse error, or env var coercion failure | — |
| `tomllib` (stdlib) | TOML parsing | `tomllib.loads()` | No third-party TOML library permitted |
| `argparse` (stdlib) | CLI parsing | `parse_known_args()` for `--config` flag | — |
| `os` (stdlib) | Env var access | `os.environ.get()` | — |
| `pathlib.Path` (stdlib) | File path resolution | `Path.cwd()`, `Path.read_text()`, `Path.is_file()` | — |
| `dataclasses.fields` (stdlib) | Schema introspection | Used to enumerate valid keys per section dataclass | — |

Construction constraint: `AppConfig` and its nested configs are frozen dataclasses constructed via standard `**kwargs` instantiation. No factory or builder is required.

## Behavior

### `load() -> AppConfig`

1. Parses `sys.argv` via `argparse` with `add_help=False` to extract the optional `--config` argument. Uses `parse_known_args()` to ignore unrecognized arguments.
2. Resolves the config file path: if `--config` is provided, uses its value as-is; otherwise checks for `model_lens.toml` in the current working directory.
3. If a config file path is resolved, logs at `INFO` level and reads/parses it with `tomllib.loads()`. If parsing fails, raises `ConfigurationError` wrapping the original exception.
4. If no config file is found, logs at `WARNING` level and proceeds with built-in defaults only.
5. Merges TOML values onto defaults per-key: for each section (`server`, `camera`, `model`), iterates the TOML section dict and copies only keys that match `dataclasses.fields()` of the corresponding dataclass. Unknown TOML keys are silently ignored.
6. Applies environment variable overrides: for each entry in the env-var mapping, if `os.environ.get()` returns a non-`None` value, coerces it to the target type and stores it. Logs each applied override at `DEBUG` level.
7. Constructs `ServerConfig`, `CameraConfig`, `ModelConfig` from their respective merged dicts, then constructs `AppConfig` from those three.
8. Calls `validate(cfg)` and returns the validated `AppConfig`.

### `validate(config: AppConfig) -> None`

1. Checks `server.host` is non-empty.
2. Checks `server.port` is between 1 and 65535 inclusive.
3. Checks `server.log_level` is one of `"debug"`, `"info"`, `"warning"`, `"error"`, `"critical"`.
4. Checks `camera.source_type` is one of `"local"`, `"rtsp"`.
5. Checks `camera.device_index` is `>= 0`.
6. Checks `camera.rtsp_url` is non-empty when `source_type == "rtsp"`.
7. Checks `model.model` is non-empty.
8. Checks `model.confidence_threshold` satisfies `0.0 < value <= 1.0`.
9. Raises `ConfigurationError` on the first violation found, with a message identifying the key, invalid value, and constraint.

### `ConfigLoader`

1. A thin class wrapper around `load()`.
2. Provides a single `load(self) -> AppConfig` method that delegates entirely to the module-level `load()` function.
3. Exists for dependency injection and subclassing contexts.

## Inputs

### `load()` inputs (implicit)

| Source | Description |
|---|---|
| `sys.argv` | Parsed for `--config <path>` |
| TOML file | Optional; path from CLI or `model_lens.toml` in cwd |
| Environment variables | `ML_<SECTION>_<KEY>` pattern |

### Data classes

#### `ServerConfig`

| Field | Type | Default | Constraints |
|---|---|---|---|
| `host` | `str` | `"0.0.0.0"` | Non-empty string |
| `port` | `int` | `8080` | 1–65535 |
| `log_level` | `str` | `"info"` | One of `"debug"`, `"info"`, `"warning"`, `"error"`, `"critical"` |

#### `CameraConfig`

| Field | Type | Default | Constraints |
|---|---|---|---|
| `source_type` | `str` | `"local"` | One of `"local"`, `"rtsp"` |
| `device_index` | `int` | `0` | `>= 0` |
| `rtsp_url` | `str` | `""` | Non-empty when `source_type == "rtsp"` |

#### `ModelConfig`

| Field | Type | Default | Constraints |
|---|---|---|---|
| `model` | `str` | `"yolov8n"` | Non-empty string |
| `confidence_threshold` | `float` | `0.5` | `0.0 < value <= 1.0` |

#### `AppConfig`

| Field | Type | Description |
|---|---|---|
| `server` | `ServerConfig` | Server settings |
| `camera` | `CameraConfig` | Camera startup defaults |
| `model` | `ModelConfig` | Model settings |

## Outputs

| Function | Success | Failure |
|---|---|---|
| `load()` | Fully validated, immutable `AppConfig` | `ConfigurationError` |
| `validate()` | `None` (returns normally) | `ConfigurationError` |

## Invariants

- All dataclasses are frozen (`@dataclass(frozen=True)`); no mutation after construction.
- `load()` is called once at server startup; the returned `AppConfig` is shared read-only.
- Only `ConfigurationError` is raised publicly; third-party exceptions (e.g., from `tomllib`) are caught and re-raised as `ConfigurationError`.
- Environment variable override triggers on any non-`None` value from `os.environ.get()` — including empty strings.
- `validate()` raises on the first constraint violation found (not all violations).
- The valid log levels and source types are stored as module-level `frozenset` constants.

## Edge Cases

- Condition: `--config` flag points to a non-existent file.
  Expected: `ConfigurationError` raised when `read_text()` fails (wrapped in "Failed to parse config file" message).

- Condition: TOML file contains unknown keys (keys not in the dataclass fields).
  Expected: Unknown keys are silently ignored; no error raised.

- Condition: Environment variable set to empty string (e.g., `ML_SERVER_HOST=""`).
  Expected: Override is applied with the empty string value. Validation may subsequently fail (e.g., `server.host must be non-empty`).

- Condition: Environment variable coercion fails (e.g., `ML_SERVER_PORT=abc`).
  Expected: `ConfigurationError` raised with message `Cannot coerce ML_SERVER_PORT="abc" to int`.

- Condition: No `--config` flag and no `model_lens.toml` in current working directory.
  Expected: Warning logged; all fields use built-in defaults; validation passes.

- Condition: TOML file has valid syntax but is completely empty.
  Expected: All fields use built-in defaults; validation passes.

- Condition: `--config` is provided but value is `None`-like (argparse parses no value).
  Expected: argparse defaults `--config` to `None`; falls through to cwd check.

## Related

- [Exceptions](./exceptions.md): `ConfigurationError` definition.
- [RuntimeConfig](./entities/runtime_config.md): runtime state seeded from `AppConfig` by the server lifespan — not by this module.
- [CONVENTIONS.md](../../CONVENTIONS.md): env var naming pattern `ML_<SECTION>_<KEY>`.
- [ARCHITECTURE.md](../../ARCHITECTURE.md): describes `AppConfig` as startup-only, immutable configuration.
