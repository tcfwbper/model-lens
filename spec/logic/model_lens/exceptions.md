# Exceptions

## Overview

Defines the project-specific exception hierarchy for ModelLens. All exceptions derive from `ModelLensError`. Each class accepts exactly one positional argument — a human-readable, actionable message string. This module contains only class definitions; it does not catch, log, or re-raise exceptions.

## Boundaries

- Owns: definition of all project-specific exception classes and their inheritance relationships.
- Owns: enforcement of the single-message constructor contract via `ModelLensError.__init__`.
- Must not: catch, handle, or log exceptions.
- Must not: import from any other `model_lens` module (leaf dependency).

## Dependencies

None. This module is a leaf dependency with no collaborators.

## Behavior

1. `ModelLensError` inherits from `Exception` and defines `__init__(self, message: str)` which calls `super().__init__(message)`.
2. All subclasses inherit `ModelLensError.__init__` without overriding it — the single-message contract is enforced by the base class.
3. The hierarchy provides semantic grouping for exception handling at system boundaries:
   - `ConfigurationError` — invalid or missing configuration.
   - `HardwareError` — hardware interaction failures.
   - `DeviceNotFoundError` — a specific device cannot be found (subclass of `HardwareError`).
   - `DataError` — unexpected or malformed data (grouping base).
   - `ValidationError` — input fails validation rules (subclass of `DataError`).
   - `ParseError` — data cannot be parsed or decoded (subclass of `DataError`).
   - `OperationError` — a valid operation failed at runtime.

## Inputs

| Field | Type | Constraints | Required? |
|---|---|---|---|
| `message` | `str` | Human-readable, actionable description of the error | Yes |

## Outputs

Each class, when raised, carries the `message` as the sole positional argument accessible via `args[0]` and `str(exc)`.

## Invariants

- Every exception class in this module derives from `ModelLensError`.
- No exception class derives directly from `Exception` or `BaseException` (except `ModelLensError` itself).
- All classes accept exactly one positional `str` argument; no structured fields are stored.
- `DataError` is a grouping base — production code prefers raising `ValidationError` or `ParseError` over `DataError` directly.

## Edge Cases

- Condition: `ModelLensError` instantiated with zero arguments.
  Expected: `TypeError` raised by Python (positional argument `message` is required).

- Condition: `ModelLensError` instantiated with more than one positional argument.
  Expected: `TypeError` raised by Python.

## Related

- [CONVENTIONS.md — Error Handling](../../CONVENTIONS.md): defines the boundary rule, message format, and when to raise vs. return.
- [ARCHITECTURE.md](../../ARCHITECTURE.md): lists `ModelLensError` as the root of the exception hierarchy.
