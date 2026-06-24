# CameraConfig

## Overview

Abstract base class identifying the active camera source. Enforces mutual exclusivity at the type level via two concrete subclasses: `LocalCameraConfig` and `RtspCameraConfig`. Cannot be instantiated directly.

## Boundaries

- Owns: defining the abstract contract (`__post_init__`) that all camera config subclasses must implement.
- Must not: be instantiated directly — only concrete subclasses may be constructed.
- Must not: contain any logic beyond the abstract method declaration.

## Dependencies

| Collaborator | Role | Allowed Interaction | Forbidden Interaction |
|---|---|---|---|
| `model_lens.exceptions.ValidationError` | Error signaling | Raised by concrete subclasses in `__post_init__` | — |

Construction constraint: implemented as a frozen dataclass with `abc.ABC`. The `__post_init__` method is declared abstract to force subclass validation.

## Behavior

1. `CameraConfig` is a frozen dataclass decorated with `@dataclass(frozen=True)` and inheriting from `abc.ABC`.
2. Declares an abstract `__post_init__` method that subclasses must implement for field validation.
3. Direct instantiation raises `TypeError` due to the abstract method.

## Inputs

None (abstract class — no fields).

## Outputs

None (abstract class — not instantiated directly).

## Invariants

- `CameraConfig` is never instantiated directly.
- All concrete subclasses are frozen dataclasses.
- Equality comparison (`==`) between `CameraConfig` instances must not be relied upon by any component to decide whether to recreate the camera source.

## Edge Cases

- Condition: Attempt to instantiate `CameraConfig()` directly.
  Expected: `TypeError` raised by Python due to unimplemented abstract method.

## Related

- [LocalCameraConfig](./local_camera_config.md)
- [RtspCameraConfig](./rtsp_camera_config.md)

---

# LocalCameraConfig

## Overview

Concrete camera configuration for a locally attached camera device, identified by a zero-based device index.

## Boundaries

- Owns: validation of `device_index` at construction time.
- Delegates: usage of this configuration to `CameraCapture`.
- Must not: perform any camera I/O or device probing.

## Dependencies

| Collaborator | Role | Allowed Interaction | Forbidden Interaction |
|---|---|---|---|
| `model_lens.exceptions.ValidationError` | Error signaling | Raised when `device_index < 0` | — |

Construction constraint: must be constructed via standard dataclass instantiation (`LocalCameraConfig(device_index=...)`). Frozen after construction.

## Behavior

1. Inherits from `CameraConfig` as a frozen dataclass.
2. `__post_init__` validates that `device_index >= 0`.
3. Raises `ValidationError` with an actionable message if `device_index` is negative.

## Inputs

| Field | Type | Default | Constraints | Required? |
|---|---|---|---|---|
| `device_index` | `int` | `0` | `>= 0` | No (has default) |

## Outputs

A frozen `LocalCameraConfig` instance.

## Invariants

- `device_index` is always `>= 0` after successful construction.
- Instance is immutable after construction.

## Edge Cases

- Condition: `device_index` is negative.
  Expected: `ValidationError` raised with message including the invalid value.

- Condition: `device_index` is `0`.
  Expected: Valid construction (default value).

## Related

- [CameraConfig](./camera_config.md)
- [RtspCameraConfig](./rtsp_camera_config.md)

---

# RtspCameraConfig

## Overview

Concrete camera configuration for an RTSP network camera stream, identified by its URL.

## Boundaries

- Owns: validation that `rtsp_url` is non-empty at construction time.
- Delegates: network connectivity and stream reading to `CameraCapture`.
- Must not: perform any network I/O or URL reachability checks.

## Dependencies

| Collaborator | Role | Allowed Interaction | Forbidden Interaction |
|---|---|---|---|
| `model_lens.exceptions.ValidationError` | Error signaling | Raised when `rtsp_url` is empty | — |

Construction constraint: must be constructed via standard dataclass instantiation (`RtspCameraConfig(rtsp_url=...)`). Frozen after construction.

## Behavior

1. Inherits from `CameraConfig` as a frozen dataclass.
2. `__post_init__` validates that `rtsp_url` is a non-empty string.
3. Raises `ValidationError` with an actionable message if `rtsp_url` is empty.

## Inputs

| Field | Type | Default | Constraints | Required? |
|---|---|---|---|---|
| `rtsp_url` | `str` | `""` | Non-empty string | Effectively yes (default fails validation) |

## Outputs

A frozen `RtspCameraConfig` instance.

## Invariants

- `rtsp_url` is always a non-empty string after successful construction.
- Instance is immutable after construction.

## Edge Cases

- Condition: `rtsp_url` is an empty string (including default).
  Expected: `ValidationError` raised.

- Condition: `rtsp_url` contains whitespace only.
  Expected: Valid construction (not stripped — only empty-string check is performed).

## Related

- [CameraConfig](./camera_config.md)
- [LocalCameraConfig](./local_camera_config.md)
