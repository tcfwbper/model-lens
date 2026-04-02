# ADR 0012: Package Data Resource Resolution and Fallback Strategy

**Date:** 2026-03-24
**Status:** Superseded

## Context

The model file (`.pt`) and label map file must be available at runtime. MVP ships these resources bundled with the package. The question is: should an explicit file path be required, or should empty strings trigger a fallback to package-bundled resources?

## Decision

`TorchInferenceEngine.__init__()` accepts `model_path` and `labels_path` as either:

1. **Non-empty string** — interpreted as an absolute filesystem path. The file must exist and be readable, or `ConfigurationError` is raised.
2. **Empty string** — triggers a fallback to the package-bundled resource (via `importlib.resources`). If the resource cannot be resolved or is missing from the distribution, `ConfigurationError` is raised.

## Rationale

- **MVP flexibility** — bundling resources simplifies deployment (`pip install model-lens` and run), but users may want to override the bundled model or labels in production. Empty string provides a simple, unambiguous signal for "use the default".
- **No magic strings** — requiring an explicit path for custom files avoids fragile heuristics like "if path contains `/usr`... or "if path ends with `.pt`...". Empty string is explicit: "I want the default".
- **Backward compatibility** — if a future version adds a config file, it can specify absolute paths for custom models and empty strings for defaults without changing the API.
- **Deterministic fallback** — `importlib.resources` is the standard library mechanism for package resources; it is portable, version-aware, and documented.

## Package Resource Loading

Resources are loaded using `importlib.resources.files()` (Python 3.9+):

```python
resource_path = importlib.resources.files("model_lens").joinpath("data/model.pt")
```

If the resource cannot be located (package not installed, data directory missing, or file missing from distribution), `ConfigurationError` is raised immediately with a message identifying which resource and why.

## Error Messages

Clear error messages distinguish the failure modes:

- **Custom path does not exist**: `ConfigurationError: model_path '/path/to/model.pt' does not exist`
- **Custom path not readable**: `ConfigurationError: model_path '/path/to/model.pt' is not readable`
- **Bundled resource missing**: `ConfigurationError: default model resource 'model_lens/data/model.pt' not found; check package installation`

## Validation at Startup

Path resolution and validation happen in `__init__()`, not lazily on first `detect()` call. This ensures:

- **Fail fast** — configuration errors are reported at server startup, not after the first frame arrives.
- **Clear error attribution** — a user is immediately told if their config is wrong, not mysteriously told `detect()` failed.

## Alternatives Considered

- **Always require absolute paths** — rejected because it forces users to specify paths even for the default MVP use case, adding friction.
- **Environment variables as fallback** — rejected because it adds a second config source (env vars + constructor args) and can lead to confusion ("Is my config set in the app or in the shell?").
- **Heuristic path resolution** (e.g., "if empty, look in ./models/")  — rejected as fragile and non-deterministic across different machines.
- **Embedded binary in source code** — rejected; models are too large (>100 MB) to embed as base64 strings.

## Custom Paths vs Bundled Resources

| Scenario | `model_path` | `labels_path` | Outcome |
|---|---|---|---|
| User uses MVP defaults | `""` | `""` | Load bundled resources via `importlib.resources` |
| User provides custom model | `"/path/to/custom.pt"` | `""` | Load custom model + bundled labels |
| User provides everything custom | `"/path/to/custom.pt"` | `"/path/to/custom.txt"` | Load both from filesystem |
| User provides wrong path | `"/nonexistent.pt"` | — | Raise `ConfigurationError` at `__init__()` time |

## Consequences

- MVP deployment is simple: one `pip install` and the model is ready to use.
- Power users who want to replace the model have a clear mechanism: pass absolute paths.
- Configuration errors are caught early, before the server starts running.
- The default fallback mechanism is documented in spec, not hidden; future maintainers understand the behaviour.
- If a distributable `.pt` file is unintentionally excluded from the package, the error is caught at startup, not mysteriously mid-inference.

## Future Extensibility

If a future release adds a persistent config file (JSON/TOML), it can populate `model_path` and `labels_path` fields with values from the file, or leave them empty to fall back to defaults. No changes to the engine are needed.

## Superseded By / Supersedes

- **Superseded By:** [ADR 0023](0023_model_registry_and_yolo_backend.md) — model and label map are retrieved from a model registry; file-path resolution and `importlib.resources` fallback no longer apply.
