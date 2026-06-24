# RuntimeConfig

## Overview

The full runtime state of the server. Holds the active camera configuration, the list of target labels, and the model confidence threshold. Replaced atomically on each update; never mutated in place.

## Boundaries

- Owns: grouping camera config, target labels, and confidence threshold into a single immutable snapshot.
- Delegates: atomic swap of the reference to the Detection Pipeline (which owns the `RuntimeConfig` reference).
- Delegates: runtime modification of `camera` and `target_labels` to the Config API.
- Must not: perform any validation beyond dataclass construction.
- Must not: mutate any field after construction (frozen dataclass).

## Dependencies

| Collaborator | Role | Allowed Interaction | Forbidden Interaction |
|---|---|---|---|
| `CameraConfig` | Nested entity | Stored as the `camera` field | — |

Construction constraint: must be constructed via standard frozen dataclass instantiation. Fields use `field(default_factory=...)` for mutable defaults.

## Behavior

1. Implemented as a frozen dataclass (`@dataclass(frozen=True)`).
2. `camera` defaults to `LocalCameraConfig(device_index=0)` via `field(default_factory=...)`.
3. `target_labels` defaults to an empty list via `field(default_factory=list)`.
4. `confidence_threshold` defaults to `0.5`.
5. No `__post_init__` validation is performed — all field validation is the responsibility of the caller or nested entity constructors.

## Inputs

| Field | Type | Default | Constraints | Required? |
|---|---|---|---|---|
| `camera` | `CameraConfig` | `LocalCameraConfig(device_index=0)` | Must be a valid `CameraConfig` subclass instance | No (has default) |
| `target_labels` | `list[str]` | `[]` | List of label strings | No (has default) |
| `confidence_threshold` | `float` | `0.5` | Semantically `0.0 < value <= 1.0`, but not enforced here | No (has default) |

## Outputs

A frozen `RuntimeConfig` instance.

## Invariants

- Instance is immutable after construction.
- `target_labels` is always a list (never `None`).
- `camera` is always a `CameraConfig` subclass instance (never `None`).
- The Config API replaces the entire `RuntimeConfig` instance atomically; no in-place mutation occurs.
- `confidence_threshold` is set at startup from `AppConfig` and is not modifiable at runtime through the Config API.

## Edge Cases

- Condition: Constructed with no arguments.
  Expected: Valid instance with default camera (`LocalCameraConfig(0)`), empty `target_labels`, and `confidence_threshold=0.5`.

- Condition: `target_labels` is an empty list.
  Expected: Valid — no objects are flagged as targets until the user configures labels.

## Related

- [CameraConfig](./camera_config.md)
- [DetectionResult](./detection_result.md)
