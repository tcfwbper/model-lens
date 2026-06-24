# DetectionResult

## Overview

Represents a single detected object produced by one inference pass. Contains the resolved human-readable label, confidence score, normalised bounding box, and a flag indicating whether the label is in the configured target list.

## Boundaries

- Owns: validation of `label` (non-empty) and `confidence` (in range `(0.0, 1.0]`) at construction time.
- Delegates: label resolution (raw index → string) to `InferenceEngine` — this entity only stores the resolved string.
- Delegates: `is_target` computation to `InferenceEngine.detect()`, which checks `label` against `target_labels` passed per call.
- Must not: access `RuntimeConfig` or any external state.

## Dependencies

| Collaborator | Role | Allowed Interaction | Forbidden Interaction |
|---|---|---|---|
| `model_lens.exceptions.ValidationError` | Error signaling | Raised in `__post_init__` when fields are invalid | — |

Construction constraint: must be constructed via standard frozen dataclass instantiation. Validation runs in `__post_init__`.

## Behavior

1. Implemented as a frozen dataclass (`@dataclass(frozen=True)`).
2. `__post_init__` validates:
   - `label` is non-empty — raises `ValidationError` if empty.
   - `confidence` satisfies `0.0 < value <= 1.0` — raises `ValidationError` if out of range.
3. `bounding_box` is stored as-is without validation (normalised coordinate correctness is the responsibility of `InferenceEngine`).
4. `is_target` is stored as-is — the caller is responsible for computing it correctly.

## Inputs

| Field | Type | Constraints | Required? |
|---|---|---|---|
| `label` | `str` | Non-empty | Yes |
| `confidence` | `float` | `0.0 < value <= 1.0` | Yes |
| `bounding_box` | `tuple[float, float, float, float]` | `(x1, y1, x2, y2)`, normalised `[0.0, 1.0]` | Yes |
| `is_target` | `bool` | — | Yes |

### Bounding Box Format

- `(x1, y1, x2, y2)`: top-left and bottom-right corners.
- All values are normalised floats in `[0.0, 1.0]`.
- Coordinate origin: top-left of the frame. `x` increases left→right; `y` increases top→bottom.
- Values are not clamped or validated by this entity.

## Outputs

A frozen `DetectionResult` instance, or `ValidationError` on invalid inputs.

## Invariants

- `label` is always a non-empty string after successful construction.
- `confidence` is always in `(0.0, 1.0]` after successful construction.
- Instance is immutable after construction.
- `label` is always a resolved human-readable string — raw integer indices must never appear.

## Edge Cases

- Condition: `label` is an empty string.
  Expected: `ValidationError` raised.

- Condition: `confidence` is `0.0`.
  Expected: `ValidationError` raised (range is exclusive of zero).

- Condition: `confidence` is `1.0`.
  Expected: Valid construction (range is inclusive of 1.0).

- Condition: `confidence` is negative or greater than `1.0`.
  Expected: `ValidationError` raised.

## Related

- [RuntimeConfig](./runtime_config.md): provides `target_labels` used to compute `is_target`.
- [exceptions](../exceptions.md): `ValidationError` raised on invalid fields.
