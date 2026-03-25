# Error Handling Conventions for ModelLens

## Core Principle
Errors must be **explicit, typed, and traceable**. Never swallow exceptions silently.
All public functions communicate failure through typed exceptions — never via sentinel values
(e.g., returning `None`, `-1`, or `""` to signal error).

---

## Exception Hierarchy

Define project exceptions in `src/model_lens/exceptions.py`.

For the complete definition of the exception hierarchy, base classes, and individual exception types, see [Exceptions Specification](logic/model_lens/exceptions.md).

**Rules:**
- All project-specific exceptions derive from `ModelLensError`.
- Never raise `Exception` or `BaseException` directly in production code.
- Third-party exceptions may propagate unless the module is a boundary (see below).

---

## Boundary Rule

At **system boundaries** (entry points, external library calls), catch third-party exceptions
and re-raise as the appropriate `ModelLensError` subclass:

```python
try:
    result = some_external_lib.call()
except SomeExternalError as exc:
    raise OperationError("Description of what failed") from exc
```

**Do not** re-raise with a bare `raise SomeExternalError(...)` from within internal modules —
callers should only need to handle `ModelLensError` subtypes.

---

## When to Raise vs. When to Return

| Situation | Approach |
|---|---|
| Invalid input from caller | Raise `ValidationError` |
| External system unavailable | Raise `HardwareError` or `OperationError` |
| True optional result | Return `T \| None` with clear docstring |
| Expected empty collection | Return `[]` / `{}` — not an error |
| Unrecoverable internal state | Raise `ModelLensError` with full context message |

**Never** use exceptions for flow control (e.g., `try/except` as an `if`).

---

## Exception Message Format

Messages must be **actionable** — include what happened, what value caused it, and where applicable:

```python
# Good
raise ValidationError(f"Temperature threshold must be positive, got {value!r}")

# Bad
raise ValidationError("Invalid value")
```

---

## Logging Convention

Use the standard `logging` module. Never use `print()` in production code.

| Level | When to use |
|---|---|
| `DEBUG` | Detailed internal state, loop iterations, intermediate values |
| `INFO` | Normal milestones: module initialised, task completed |
| `WARNING` | Recoverable unexpected state; operation continues |
| `ERROR` | Operation failed; exception will be raised or was caught at boundary |
| `CRITICAL` | System-level failure; process may not continue |

```python
import logging

logger = logging.getLogger(__name__)  # one logger per module, named by module
```

**Rules:**
- Obtain the logger at module level with `logging.getLogger(__name__)`.
- Do not configure handlers in library code — only in entry points.
- Log **before** raising an exception at boundaries (so the error appears in logs even if the
  caller does not log it).

---

## Type Annotation for Errors

- Annotate `raises` in Google docstrings for all public functions that raise:

```python
def read_device(device_id: int) -> DeviceInfo:
    """Read information from a GPU device.

    Args:
        device_id: The zero-based device index.

    Returns:
        A DeviceInfo describing the device.

    Raises:
        DeviceNotFoundError: If no device with the given ID exists.
        OperationError: If the device query fails unexpectedly.
    """
```

---

## HTTP API Error Conventions

The FastAPI application layer translates domain exceptions and request validation failures into
standard HTTP error responses. All error responses share a common JSON shape.

### Error Response Format

All error responses use FastAPI's standard `HTTPException` body:

```json
{ "detail": "<human-readable message>" }
```

Custom error messages are used for domain-specific failures (e.g., `"No frame available"`).
Pydantic validation errors use FastAPI's default `422` response body (array of error objects
under `"detail"`).

### HTTP Status Code Map

The translation from internal failures to HTTP codes must follow these mappings:

| Status Code | Condition | Meaning |
|---|---|---|
| `202 Accepted` | Resource not yet available | Request accepted but content isn't ready (e.g. no frames available yet) |
| `400 Bad Request` | Malformed request body | Client sent invalid payload format (e.g., bad JSON) |
| `404 Not Found` | Unknown path or resource | Client requested a non-existent URL |
| `422 Unprocessable Entity` | Data validation fails | Request is grammatically correct but semantically invalid |
| `500 Internal Server Error` | Unexpected server failure | Unhandled exceptions in the application layer |

### Pydantic vs. Domain ValidationError

Two distinct `ValidationError` types coexist in the project:

| Class | Namespace | Used in | HTTP mapping |
|---|---|---|---|
| `pydantic.ValidationError` | `pydantic` | API request/response models (`schemas.py`) | Handled by FastAPI → `422` response |
| `model_lens.exceptions.ValidationError` | `model_lens.exceptions` | Domain entities, camera capture | Never crosses HTTP boundary directly |

API-layer code (routers, schemas) always works with Pydantic's `ValidationError`. Domain-layer
code (entities, camera capture, inference engine) always works with the project's
`ValidationError`. These two must never be confused or cross-imported.

### Startup Fatal Errors

During the FastAPI `lifespan` startup sequence, the following domain exceptions are treated as
fatal and result in `sys.exit(1)` (they never become HTTP responses):

| Exception | Trigger |
|---|---|
| `ConfigurationError` | Invalid `AppConfig` or unresolvable model/label paths |
| `OperationError` | Model file cannot be loaded by inference engine |
| `ParseError` | Label map file is empty or unparseable |
| `RuntimeError` | `DetectionPipeline.start()` called more than once |

All fatal startup errors are logged at `CRITICAL` level before `sys.exit(1)`.

### Async Hardware Validation and API Responses

Hardware connectivity is **not** validated synchronously by API endpoints. If a configuration
update request specifies a hardware source (such as a camera) that is unreachable, the API returns `200 OK` regardless.
Hardware reachability is a runtime concern handled by the background processing pipelines, which log the
error and wait for a new config. This separation ensures that the API layer never raises
`HardwareError` or `DeviceNotFoundError` synchronously as an HTTP error.
