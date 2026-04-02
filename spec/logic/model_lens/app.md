# App Specification for ModelLens

## Core Principle

`app.py` is the FastAPI application entry point. It owns the server lifecycle, mounts all API
routers and static assets, and wires together the `DetectionPipeline`, `InferenceEngine`, and
`RuntimeConfig` into a single running process. All HTTP concerns — routing, request validation,
response serialisation, and error handling — are defined here or in the routers it mounts.

---

## Module Location

`src/model_lens/app.py`

---

## Application Lifecycle

The FastAPI application uses a `lifespan` context manager (the modern FastAPI/Starlette
lifecycle hook) to manage startup and shutdown in the correct order.

### Startup Sequence

```
lifespan() enters
    │
    ▼
1. Load AppConfig (ConfigLoader)
    └── ConfigurationError → log CRITICAL, sys.exit(1)
    │
    ▼
2. Construct YOLOInferenceEngine(
       model=app_config.model.model,
       confidence_threshold=app_config.model.confidence_threshold,
   )
    └── ConfigurationError / OperationError → log CRITICAL, sys.exit(1)
    │
    ▼
3. Construct initial RuntimeConfig from AppConfig
    │
    ▼
4. Construct DetectionPipeline(engine, initial_config)
    │
    ▼
5. DetectionPipeline.start()
    └── RuntimeError (double-start) → log CRITICAL, sys.exit(1)
    │
    ▼
6. yield  ← application serves requests
    │
    ▼
(shutdown signal received)
```

### Shutdown Sequence

```
lifespan() resumes after yield
    │
    ▼
1. DetectionPipeline.stop()   ← blocks until background thread exits
    │
    ▼
2. YOLOInferenceEngine.teardown()
    │
    ▼
lifespan() exits
```

### Rules

- All startup steps run sequentially in the `lifespan` coroutine before `yield`.
- Any unhandled exception during startup logs at `CRITICAL` and calls `sys.exit(1)`.
- `DetectionPipeline.stop()` is always called during shutdown even if startup partially
  failed, provided the pipeline was constructed (use a `try/finally` guard around `yield`).
- The `InferenceEngine` is torn down **after** the pipeline is stopped; the pipeline must
  not call `engine.detect()` after `stop()` returns.

---

## Routers

The application is composed of three routers mounted on the root FastAPI app:

| Router module | Mount prefix | Responsibility |
|---|---|---|
| `config_router` | `/config` | Config API (CRUD for `RuntimeConfig`) |
| `stream_router` | (none) | Stream API (`/stream`) |
| `health_router` | (none) | Health check (`/healthz`) |

See individual router specifications:
- `routers/config.md`
- `routers/stream.md`
- `routers/health.md`

Static assets are mounted separately (see Static Assets section).

---

## Static Assets

### Frontend build location

The compiled frontend is built from `src/ui/` and output to `dist/`. The FastAPI app
serves files from the `dist/` directory, resolved relative to the installed package
using `importlib.resources` (or equivalent package-data resolution).

### Routing

| Path | Behaviour |
|---|---|
| `GET /` | Serves `dist/index.html` directly with `text/html` content type |
| `GET /favicon.svg` | Serves `dist/favicon.svg` with `image/svg+xml` content type |
| `GET /assets/{path}` | Serves files from `dist/assets/` via `StaticFiles` mount |

**Rules:**

- `GET /` serves `index.html` directly (not a redirect). The response includes an `ETag`
  header computed as the **MD5 hex digest** of the file's raw byte content
  (e.g., `ETag: "d41d8cd98f00b204e9800998ecf8427e"`). The value is a quoted string per
  the HTTP specification. This enables browser caching and conditional `GET` requests via
  `If-None-Match`.
- `GET /favicon.svg` serves `dist/favicon.svg` with `Content-Type: image/svg+xml`.
- All other unmatched paths that do not begin with `/config`, `/stream`, `/healthz`, or
  `/assets` fall through to a `404 Not Found` response (FastAPI default).
- `StaticFiles` is mounted at `/assets` and serves the compiled JS, CSS, and other assets
  from `dist/assets/`. The mount is conditional: if `dist/assets/` does not exist it is
  silently skipped.
- If the `dist/` directory or `dist/index.html` cannot be resolved at startup (package not
  installed correctly), the server logs `CRITICAL` and calls `sys.exit(1)`.

---

## Error Response Format

All error responses use FastAPI's standard `HTTPException` shape:

```json
{ "detail": "<human-readable message>" }
```

Custom error messages are used for domain-specific failures.
Pydantic validation errors use FastAPI's default `422` response body (array of error
objects under `"detail"`).
Any unhandled exceptions raised in the application layer or unexpected server failures automatically result in a `500 Internal Server Error` response.

---

## HTTP Status Code Map

The translation from internal failures to HTTP codes must follow these mappings:

| Status Code | Condition | Meaning |
|---|---|---|
| `400 Bad Request` | Malformed request body | Client sent invalid payload format (e.g., bad JSON) |
| `404 Not Found` | Unknown path or resource | Client requested a non-existent URL |
| `422 Unprocessable Entity` | Data validation fails | Request is grammatically correct but semantically invalid |
| `500 Internal Server Error` | Unexpected server failure | Unhandled exceptions in the application layer |

---

## Dependency Injection

The `DetectionPipeline` instance is stored in FastAPI's `app.state` during the lifespan
startup and accessed by routers via a FastAPI dependency:

```python
def get_pipeline(request: Request) -> DetectionPipeline:
    return request.app.state.pipeline
```

Routers declare this dependency with `Depends(get_pipeline)`. This avoids module-level
globals and makes the dependency explicit and testable.

---

## Module Structure

```
src/model_lens/
├── app.py          ← FastAPI app factory, lifespan, router mounting
├── schemas.py      ← Pydantic request/response models (see schemas.md)
├── routers/
│   ├── __init__.py
│   ├── config.py   ← Config API router (/config)
│   ├── stream.py   ← Stream API router (/stream)
│   └── health.py   ← Health check router (/healthz)
└── ...
```

---

## Constraints and Non-Goals

- No authentication or session management is in scope.
- The server does not support HTTPS termination directly; TLS is expected to be handled by
  a reverse proxy if required.
