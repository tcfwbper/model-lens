# Error Handling Conventions for ModelLens

## Core Principle
Errors must be **explicit, typed, and traceable**. Never swallow exceptions silently.
All public functions communicate failure through typed exceptions — never via sentinel values
(e.g., returning `None`, `-1`, or `""` to signal error).

---

## Exception Hierarchy

Define project exceptions in `src/model_lens/exceptions.py`:

```
ModelLensError               ← base for all project exceptions
├── ConfigurationError     ← invalid or missing configuration
├── HardwareError          ← failures interacting with hardware (e.g., GPU)
│   └── DeviceNotFoundError
├── DataError              ← unexpected or malformed data
│   ├── ValidationError    ← input fails validation rules
│   └── ParseError         ← data cannot be parsed/decoded
└── OperationError         ← a valid operation failed at runtime
```

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
