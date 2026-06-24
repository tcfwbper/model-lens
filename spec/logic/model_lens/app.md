# App

## Overview

FastAPI application entry point. Owns the server lifecycle, mounts all API routers and static assets, wires together the `DetectionPipeline`, `YOLOInferenceEngine`, and `RuntimeConfig` into a single running process. All HTTP concerns — routing, request validation, response serialization, and error handling — are defined here or in the routers it mounts. Does not perform inference, camera management, or frame processing.

## Boundaries

- Owns: FastAPI application construction (`create_app()`).
- Owns: lifespan management (startup/shutdown sequencing).
- Owns: mounting routers (`health`, `config`, `stream`) and static file serving.
- Owns: global exception handlers (`RequestValidationError` → 400 for JSON parse errors, unhandled `Exception` → 500).
- Owns: `dist/` directory resolution via `importlib.resources`.
- Owns: `get_pipeline` dependency function exposed for router use.
- Owns: `_StartupExit` exception class for clean exit propagation through anyio task groups.
- Delegates: configuration loading to `model_lens.config.load()`.
- Delegates: inference to `YOLOInferenceEngine`.
- Delegates: frame loop execution to `DetectionPipeline`.
- Delegates: HTTP endpoint behavior to individual router modules.
- Must not: perform inference or frame processing.
- Must not: manage camera hardware directly.
- Must not: persist state to disk.

## Dependencies

| Collaborator | Role | Allowed Interaction | Forbidden Interaction |
|---|---|---|---|
| `model_lens.config.load` | Configuration source | Call `load()` at startup | Must not call after startup |
| `model_lens.inference_engine.YOLOInferenceEngine` | Inference backend | Construct, store in `app.state.engine`, call `teardown()` at shutdown | Must not call `detect()` directly |
| `model_lens.detection_pipeline.DetectionPipeline` | Frame loop | Construct, call `start()`, `stop()`, store in `app.state.pipeline` | Must not call `_run()` or access internals |
| `model_lens.entities.RuntimeConfig` | Initial config | Construct initial instance from `AppConfig` | — |
| `model_lens.entities.LocalCameraConfig` | Initial camera | Construct for initial `RuntimeConfig` | — |
| `model_lens.exceptions.ConfigurationError` | Error signaling | Caught during startup → `_StartupExit` | — |
| `model_lens.exceptions.OperationError` | Error signaling | Caught during startup → `_StartupExit` | — |
| `model_lens.routers.config` | Config API | `include_router(config.router)` | — |
| `model_lens.routers.stream` | Stream API | `include_router(stream.router)` | — |
| `model_lens.routers.health` | Health API | `include_router(health.router)` | — |
| `fastapi.StaticFiles` | Asset serving | Mount at `/assets` | — |
| `importlib.resources` | Package data | Resolve `model_lens` package path | — |

Construction constraint: the application is created via `create_app()` factory function. No module-level `app` global.

## Behavior

### `_StartupExit`

1. Inherits from both `SystemExit` and `Exception`.
2. Ensures the exit propagates cleanly through anyio's task groups instead of being wrapped in a `BaseExceptionGroup`.

### `resolve_dist_dir() -> Path`

3. Uses `importlib.resources.files("model_lens")` to locate the package directory.
4. Returns `Path(str(pkg)) / "dist"`.

### `get_pipeline(request) -> DetectionPipeline`

5. Reads `request.app.state.pipeline` and returns it cast to `DetectionPipeline`.
6. Intended for use as a FastAPI `Depends()` injection.

### `_startup() -> tuple[YOLOInferenceEngine, DetectionPipeline]`

7. Calls `load()` to get `AppConfig`. On `ConfigurationError` or `FileNotFoundError`: raises `_StartupExit(1)`.
8. Calls `resolve_dist_dir()`. On `FileNotFoundError`: raises `_StartupExit(1)`.
9. Checks that `dist_dir / "index.html"` exists. If not: raises `_StartupExit(1)`.
10. Constructs `YOLOInferenceEngine(model=app_config.model.model, confidence_threshold=app_config.model.confidence_threshold)`. On `ConfigurationError` or `OperationError`: raises `_StartupExit(1)`.
11. Constructs initial `RuntimeConfig` with:
    - `camera=LocalCameraConfig(device_index=app_config.camera.device_index)`
    - `target_labels=list(engine.get_label_map().values())`
    - `confidence_threshold=app_config.model.confidence_threshold`
12. Constructs `DetectionPipeline(engine=engine, initial_config=initial_config)`.
13. Calls `pipeline.start()`. On any exception: calls `pipeline.stop()`, then raises `_StartupExit(1)`.
14. Returns `(engine, pipeline)`.

### `lifespan(app)` (async context manager)

15. If `app.state` already has a `pipeline` attribute (e.g., set by tests), yields immediately and returns — no startup or shutdown logic runs.
16. Otherwise, calls `_startup()` to get `(engine, pipeline)`.
17. Stores `pipeline` in `app.state.pipeline` and `engine` in `app.state.engine`.
18. Yields (application serves requests).
19. On shutdown (in `finally` block): calls `pipeline.stop()`, then `engine.teardown()`.

### `create_app() -> FastAPI`

20. Constructs `FastAPI(lifespan=lifespan)`.
21. Registers a `RequestValidationError` exception handler:
    - Iterates `exc.errors()` looking for `"type" == "json_invalid"`.
    - If found: returns `Response(status_code=400)` (empty body).
    - Otherwise: delegates to FastAPI's default `request_validation_exception_handler`.
22. Registers a generic `Exception` handler:
    - Returns `JSONResponse(status_code=500, content={"detail": "Internal Server Error"})`.
23. Includes routers: `health.router`, `config.router`, `stream.router`.
24. Attempts `resolve_dist_dir()`. On `FileNotFoundError`: returns app without static routes.
25. If `dist_dir / "assets"` exists: mounts `StaticFiles` at `/assets`.
26. Defines `GET /favicon.svg` → `FileResponse(dist_dir / "favicon.svg", media_type="image/svg+xml")`.
27. Defines `GET /` → reads `index.html` bytes, computes MD5 hex digest ETag (quoted string), returns `Response` with `text/html` content type and `etag` header.

## Inputs

### `_startup()` (implicit)

| Source | Description |
|---|---|
| `sys.argv` | Passed through to `config.load()` |
| Config file / env vars | Passed through to `config.load()` |
| Package `dist/` directory | Must contain `index.html` |

### `lifespan(app)`

| Field | Type | Constraints | Required? |
|---|---|---|---|
| `app` | `FastAPI` | FastAPI application instance | Yes |

## Outputs

### `create_app()`

| Field | Type | Description |
|---|---|---|
| return | `FastAPI` | Fully configured FastAPI application instance |

### `get_pipeline()`

| Field | Type | Description |
|---|---|---|
| return | `DetectionPipeline` | The pipeline instance from `app.state` |

### Exceptions

| Exception | Condition | Raised by |
|---|---|---|
| `_StartupExit(1)` | Any startup step fails | `_startup()` |

## Invariants

- `create_app()` is the sole application factory — no module-level `app` instance.
- Startup runs sequentially: config → dist check → engine → initial config → pipeline → start.
- Any failure during startup raises `_StartupExit(1)` — never leaves a partially initialized app serving.
- The `lifespan` skips all startup/shutdown logic if `app.state.pipeline` is already set (test injection).
- `pipeline.stop()` is always called in the `finally` block during shutdown.
- `engine.teardown()` is always called after `pipeline.stop()`.
- The pipeline may trigger process shutdown by sending `SIGINT` to itself on unrecoverable errors (e.g., `ParseError`). This activates uvicorn's signal handler, which cancels the lifespan scope and runs the `finally` block normally.
- The initial `target_labels` is populated from all labels in the engine's label map (all labels active by default).
- JSON parse errors in request bodies produce `400 Bad Request` (not `422`).
- Unhandled exceptions produce `500 Internal Server Error` with `{"detail": "Internal Server Error"}`.
- The `GET /` route computes the ETag as `'"' + md5(content).hexdigest() + '"'`.
- Static asset mounting is conditional: skipped silently if `dist/assets/` does not exist.
- `GET /favicon.svg` and `GET /` are excluded from the OpenAPI schema (`include_in_schema=False`).

## Edge Cases

- Condition: `dist/` directory does not exist at startup (in `_startup()`).
  Expected: `_StartupExit(1)` raised — server does not start.

- Condition: `dist/` directory does not exist at `create_app()` time (after startup bypass).
  Expected: Static routes are not mounted; API routes still function.

- Condition: `dist/index.html` does not exist.
  Expected: `_StartupExit(1)` raised — server does not start.

- Condition: `pipeline.start()` raises an exception.
  Expected: `pipeline.stop()` is called for cleanup, then `_StartupExit(1)` raised.

- Condition: Test sets `app.state.pipeline` before lifespan.
  Expected: Lifespan yields immediately — no startup or shutdown logic executes.

- Condition: Client sends malformed JSON in request body.
  Expected: `RequestValidationError` with `json_invalid` type → `400` response with empty body.

- Condition: Unhandled exception during request processing.
  Expected: Generic exception handler returns `500` with `{"detail": "Internal Server Error"}`.

- Condition: Pipeline sends `SIGINT` to own process due to unrecoverable `ParseError`.
  Expected: Uvicorn's signal handler triggers lifespan teardown; `finally` block calls `pipeline.stop()` then `engine.teardown()`. Process exits cleanly.

## Related

- [Config](./config.md): `load()` called during startup.
- [DetectionPipeline](./detection_pipeline.md): constructed and managed by lifespan.
- [InferenceEngine](./inference_engine.md): constructed and torn down by lifespan.
- [RuntimeConfig](./entities/runtime_config.md): initial instance constructed during startup.
- [Config Router](./routers/config.md): mounted on the app.
- [Stream Router](./routers/stream.md): mounted on the app.
- [Health Router](./routers/health.md): mounted on the app.
- [Schemas](./schemas.md): request validation models.
