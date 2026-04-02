# Health Router Specification for ModelLens

## Core Principle

`health.py` is the Health check router. It provides a minimal liveness endpoint used by
process supervisors and load balancers to confirm the process is alive.

---

## Module Location

`src/model_lens/routers/health.py`

---

## Endpoints

### `GET /healthz`

Returns `200 OK` with an empty body. Used by process supervisors and load balancers to
confirm the process is alive. No pipeline or camera status is included.

**Response `200 OK`:** Empty body.
