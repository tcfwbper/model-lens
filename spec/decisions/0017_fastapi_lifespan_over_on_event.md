# ADR 0017: FastAPI Lifespan Context Manager over on_event Hooks

**Date:** 2026-03-24
**Status:** Accepted

## Context

FastAPI (and its underlying Starlette) originally provided `@app.on_event("startup")` and
`@app.on_event("shutdown")` decorators for managing application startup and shutdown logic.
These hooks have been deprecated in favour of the `lifespan` context manager, which expresses
startup and shutdown as a single `async` generator function: code before `yield` runs at startup,
code after `yield` runs at shutdown.

`app.py` must initialise `ConfigLoader`, `TorchInferenceEngine`, `RuntimeConfig`, and
`DetectionPipeline` in the correct order at startup, and then tear them down in the correct
order at shutdown. A `try/finally` guard around `yield` is needed to ensure teardown always
runs even when startup partially fails.

## Decision

Use the `lifespan` async context manager (via `@asynccontextmanager`) as the single entry point
for all application startup and shutdown logic. The `on_event` decorator is not used anywhere
in `app.py`.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    ...
    try:
        yield
    finally:
        # --- shutdown ---
        ...

app = FastAPI(lifespan=lifespan)
```

## Rationale

- **`on_event` is deprecated** — Starlette and FastAPI have marked `on_event` hooks as deprecated
  since Starlette 0.20. Using the current recommended API keeps the codebase aligned with upstream
  and avoids a future breaking-change migration.
- **Single coherent function** — the `lifespan` generator expresses startup and shutdown as one
  logical unit. Variables initialised before `yield` (the pipeline, engine, etc.) are
  naturally in scope for the shutdown code after `yield` without any instance-variable gymnastics.
- **`try/finally` teardown guarantee** — wrapping `yield` in `try/finally` guarantees shutdown
  runs even if startup raises midway through. With two separate `on_event` handlers, ensuring
  teardown of a partially-initialised pipeline requires extra bookkeeping.
- **Testability** — `lifespan` can be injected into a `TestClient` context via
  `with TestClient(app) as client:`, giving integration tests full startup/shutdown coverage.

## Alternatives Considered

- **`@app.on_event("startup")` / `@app.on_event("shutdown")`** — rejected because they are
  deprecated, do not share a natural scope for locally-initialised objects, and make
  `try/finally` teardown coordination more complex.
- **Explicit `startup()` / `shutdown()` functions called from lifespan** — acceptable, but adds
  indirection without benefit for the current startup sequence length. Reconsidered if the
  lifespan function grows excessively long.

## Consequences

- All startup and shutdown logic lives in one place (`app.py:lifespan`), making the sequence
  easy to audit.
- Partial startup failures are handled cleanly: `try/finally` ensures `DetectionPipeline.stop()`
  is called if the pipeline was constructed, and `TorchInferenceEngine.teardown()` is called
  after that.
- Future developers must not introduce `@app.on_event` hooks; all lifecycle logic belongs in
  `lifespan`.

## Superseded By / Supersedes
N/A
