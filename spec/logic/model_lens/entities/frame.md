# Frame

## Overview

A single decoded image captured from a camera source, together with metadata identifying when and where it was captured. The `data` array is stored as-is (no internal copy); `CameraCapture` is responsible for copying the camera buffer before constructing a `Frame`.

## Boundaries

- Owns: grouping image data, timestamp, and source identifier into a single object.
- Delegates: buffer copying to `CameraCapture` (must call `.copy()` before constructing `Frame`).
- Delegates: colour space conversion (BGR → RGB) to `InferenceEngine` if needed.
- Must not: copy or modify `data` internally.
- Must not: validate array shape or dtype.

## Dependencies

| Collaborator | Role | Allowed Interaction | Forbidden Interaction |
|---|---|---|---|
| `numpy` | Array type | `NDArray[np.uint8]` used as the type for `data` | — |

Construction constraint: standard (non-frozen) dataclass. Not frozen because `numpy.ndarray` is not hashable.

## Behavior

1. Implemented as a dataclass (`@dataclass`) — not frozen.
2. Stores `data`, `timestamp`, and `source` as provided at construction time.
3. No `__post_init__` validation is performed.
4. All consumers must treat `data` as read-only — mutation of the array is forbidden by convention.

## Inputs

| Field | Type | Constraints | Required? |
|---|---|---|---|
| `data` | `NDArray[np.uint8]` | Shape `(H, W, 3)`, dtype `uint8`, colour space BGR | Yes |
| `timestamp` | `float` | POSIX timestamp (seconds since epoch), sub-second precision | Yes |
| `source` | `str` | Human-readable identifier (e.g., `"local:0"` or RTSP URL) | Yes |

## Outputs

A `Frame` instance.

## Invariants

- `data` must be treated as read-only by all consumers (enforced by convention, not by the type system).
- `data` colour space is always BGR (OpenCV native).
- `timestamp` is always a POSIX timestamp with sub-second precision, captured immediately after a successful frame read.
- `source` is set by `CameraCapture` and reflects the active source at capture time.

## Edge Cases

- Condition: `data` is a view (not a copy) of a shared buffer.
  Expected: This is a caller error — `CameraCapture` must copy before constructing `Frame`. `Frame` itself does not enforce this.

## Related

- [CameraConfig](./camera_config.md): determines the source string format.
- [exceptions](../exceptions.md): `Frame` does not raise any exceptions at construction.
