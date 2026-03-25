# Exceptions Specification for ModelLens

## Purpose

This document specifies the exception class definitions for `src/model_lens/exceptions.py`.
It defines the hierarchy, constructor contract, and extensibility rules for all project-specific exceptions.

---

## Source File

`src/model_lens/exceptions.py`

---

## Exception Hierarchy

```
ModelLensError               ← base for all project exceptions
├── ConfigurationError       ← invalid or missing configuration
├── HardwareError            ← failures interacting with hardware (e.g., camera device, GPU)
│   └── DeviceNotFoundError  ← a specific hardware device could not be found
├── DataError                ← unexpected or malformed data
│   ├── ValidationError      ← input fails validation rules
│   └── ParseError           ← data cannot be parsed or decoded
└── OperationError           ← a valid operation failed at runtime
```

### Extensibility Note

The hierarchy above is complete for the current version of ModelLens.
Future versions may introduce additional subclasses. New exceptions must:

- Always derive from `ModelLensError` or one of its existing subclasses.
- Be added to this spec before being implemented.
- Never derive directly from `Exception` or `BaseException`.

---

## Constructor Contract

All exception classes — `ModelLensError` and every subclass — accept **exactly one positional argument**:

| Parameter | Type | Description |
|---|---|---|
| `message` | `str` | A human-readable description of the error. Must be actionable (see Message Format below). |

No structured fields (e.g., `key`, `value`, `constraint`) are stored on the exception object.
All relevant context must be embedded in the `message` string.

### Example

```python
raise ConfigurationError(
    f"model.confidence_threshold must satisfy 0.0 < value <= 1.0, got {value!r}"
)
```

---

## Message Format

Messages must be **actionable** — they must state what happened, what value caused it, and (where applicable) what the constraint is:

```python
# Good
raise ValidationError(f"confidence_threshold must be positive, got {value!r}")

# Bad
raise ValidationError("Invalid value")
```

---

## Class Definitions

### `ModelLensError`

- Base class for all project-specific exceptions.
- Inherits from `Exception`.
- Accepts a single `message: str` argument.
- All other exception classes in this project inherit from `ModelLensError`.

### `ConfigurationError`

- Raised when configuration is invalid or missing.
- Inherits from `ModelLensError`.
- Typical triggers: a config key fails validation, a required path does not exist.

### `HardwareError`

- Raised when an interaction with hardware fails.
- Inherits from `ModelLensError`.
- Typical triggers: camera device cannot be opened, GPU is unavailable.

### `DeviceNotFoundError`

- Raised when a specific hardware device cannot be found.
- Inherits from `HardwareError`.
- Typical triggers: the requested camera device index does not exist, an RTSP URL is unreachable.

### `DataError`

- Raised when data is unexpected or malformed.
- Inherits from `ModelLensError`.
- Acts as a grouping base; prefer `ValidationError` or `ParseError` over raising `DataError` directly.

### `ValidationError`

- Raised when input fails validation rules.
- Inherits from `DataError`.
- Typical triggers: a field value is out of range, a required field is empty.

> **Naming conflict note:**
> `pydantic.ValidationError` and `model_lens.exceptions.ValidationError` coexist in the project.
> Per `spec/errors.md`, these two must never be confused or cross-imported — API-layer code uses
> Pydantic's `ValidationError`; domain-layer code uses this project's `ValidationError`.
> In the rare case that both must appear in the same module, import this class under the alias
> `ModelLensValidationError`:
>
> ```python
> from model_lens.exceptions import ValidationError as ModelLensValidationError
> ```

### `ParseError`

- Raised when data cannot be parsed or decoded.
- Inherits from `DataError`.
- Typical triggers: a label map file is empty or contains unparseable content, a TOML config file is malformed.

### `OperationError`

- Raised when a valid operation fails at runtime.
- Inherits from `ModelLensError`.
- Typical triggers: a model file cannot be loaded, an inference call fails unexpectedly.

---

## Full Class Summary

| Class | Parent | Typical Trigger |
|---|---|---|
| `ModelLensError` | `Exception` | Base; not raised directly in production code |
| `ConfigurationError` | `ModelLensError` | Invalid or missing configuration value |
| `HardwareError` | `ModelLensError` | Hardware interaction failure |
| `DeviceNotFoundError` | `HardwareError` | Specific device not found |
| `DataError` | `ModelLensError` | Unexpected or malformed data (prefer subclasses) |
| `ValidationError` | `DataError` | Input fails validation rules |
| `ParseError` | `DataError` | Data cannot be parsed or decoded |
| `OperationError` | `ModelLensError` | Valid operation failed at runtime |
