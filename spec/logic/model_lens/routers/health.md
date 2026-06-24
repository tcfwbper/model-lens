# Health Router

## Overview

Provides a minimal liveness endpoint used by process supervisors and load balancers to confirm the process is alive. Does not check pipeline status, camera connectivity, or any other runtime health indicator.

## Boundaries

- Owns: responding to `GET /healthz` with `200 OK`.
- Must not: access `app.state`, `DetectionPipeline`, or any other runtime component.
- Must not: perform any health checks beyond confirming the process is responsive.

## Dependencies

| Collaborator | Role | Allowed Interaction | Forbidden Interaction |
|---|---|---|---|
| `fastapi.APIRouter` | Router framework | Define route via `@router.get("/healthz")` | — |
| `fastapi.responses.Response` | HTTP response | Construct with `status_code=200` | — |

Construction constraint: module-level `router = APIRouter()` instance. Included by `app.py` via `include_router()`.

## Behavior

### `GET /healthz`

1. Returns `Response(status_code=200)` with no body.
2. No parameters or dependencies.

## Inputs

None.

## Outputs

| Field | Type | Description |
|---|---|---|
| HTTP response | `200 OK` | Empty body |

## Invariants

- Always returns `200` regardless of pipeline or camera state.
- No dependencies on `app.state`.

## Edge Cases

None — this endpoint has no failure modes beyond the process being unreachable.

## Related

- [App](../app.md): mounts this router.
