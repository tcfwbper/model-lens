# ADR 0018: DetectionPipeline Dependency Injection via app.state and Depends

**Date:** 2026-03-24
**Status:** Accepted

## Context

The `config_router`, `stream_router`, and other routers need access to the live
`DetectionPipeline` instance to read from its result queue and push config updates. There are
two common patterns in FastAPI for sharing application-level objects with route handlers:

1. **Module-level global** — instantiate the pipeline at module import time and import it into
   each router.
2. **`app.state` + `Depends`** — store the instance in `app.state` during `lifespan` startup
   and expose it through a FastAPI dependency function injected via `Depends`.

## Decision

The `DetectionPipeline` instance is stored in `app.state.pipeline` during `lifespan` startup.
Routers access it through a dependency function:

```python
from fastapi import Request, Depends

def get_pipeline(request: Request) -> DetectionPipeline:
    return request.app.state.pipeline
```

Route handlers declare the dependency explicitly:

```python
@router.get("/config")
def get_config(pipeline: DetectionPipeline = Depends(get_pipeline)):
    ...
```

## Rationale

- **No module-level globals** — a module-level pipeline instance would be initialised at
  import time, before the `lifespan` startup sequence (and before `ConfigLoader` has validated
  the configuration). `app.state` defers assignment until after successful initialisation.
- **Testability** — replacing `app.state.pipeline` with a mock in tests requires only setting
  an attribute on the test app instance; no import patching or monkey-patching needed.
- **Explicit dependencies** — `Depends(get_pipeline)` makes the pipeline dependency visible in
  the function signature, enabling dependency graph introspection and easier understanding of
  what each route needs.
- **Thread-safe access** — `app.state.pipeline` is set once during startup; all subsequent
  reads from request handlers are read-only references. No additional locking is required.
- **Standard FastAPI idiom** — `app.state` combined with `Depends` is the officially recommended
  pattern for sharing application-level state in FastAPI.

## Alternatives Considered

- **Module-level global** — rejected because it is initialised at import time (before startup),
  cannot be replaced cleanly in tests without import patching, and conflates module
  initialisation with application lifecycle.
- **Router-level global (assigned in lifespan via closure)** — functionally equivalent to
  `app.state` but less idiomatic and harder to mock; rejected in favour of the standard pattern.
- **Dependency override at test time (`app.dependency_overrides`)** — this is a valid testing
  strategy and is compatible with the `Depends(get_pipeline)` approach. It can be used
  alongside (not instead of) `app.state`.

## Consequences

- The `DetectionPipeline` instance must be assigned to `app.state.pipeline` before any request
  handler that uses `Depends(get_pipeline)` is invoked. `lifespan` guarantees this ordering.
- If a request arrives before startup completes (unlikely with Uvicorn's default behaviour but
  theoretically possible), `get_pipeline` raises `AttributeError`. This is acceptable; the
  process would exit on startup failure anyway.
- All future application-level shared objects (e.g., a metrics registry, a secondary pipeline)
  should follow the same `app.state` + `Depends` pattern for consistency.

## Superseded By / Supersedes
N/A
