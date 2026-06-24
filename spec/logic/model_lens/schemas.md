# Schemas

## Overview

Defines all Pydantic v2 request models used by the API routers for HTTP request validation. These models are the single source of truth for request body structure and constraints. Does not define response models — response serialization is handled by the router modules directly.

## Boundaries

- Owns: definition and validation logic for all API request body models.
- Owns: discriminated union dispatch for polymorphic camera source requests.
- Delegates: response serialization to the individual router modules.
- Must not: contain any business logic, side effects, or imports from other `model_lens` modules.
- Must not: define response models (responses are serialized manually by routers).

## Dependencies

| Collaborator | Role | Allowed Interaction | Forbidden Interaction |
|---|---|---|---|
| `pydantic` | Validation framework | `BaseModel`, `Field`, `field_validator` | — |
| `typing` | Type annotations | `Annotated`, `Literal` | — |

Construction constraint: all models are standard Pydantic v2 `BaseModel` subclasses.

## Behavior

### `LocalCameraRequest`

1. Represents a request to select a local camera source.
2. `source_type` is a literal `"local"` — used as the discriminator value.
3. `device_index` is an integer with a default of `0`, constrained to `>= 0` via `pydantic.Field(ge=0)`.

### `RtspCameraRequest`

4. Represents a request to select an RTSP camera source.
5. `source_type` is a literal `"rtsp"` — used as the discriminator value.
6. `rtsp_url` is a required string.
7. A `field_validator` on `rtsp_url` raises `ValueError` if the value does not start with `"rtsp://"`.

### `UpdateCameraRequest`

8. Wraps a polymorphic camera request body.
9. `camera` field is a discriminated union of `LocalCameraRequest | RtspCameraRequest`, discriminated on `source_type`.
10. Uses `pydantic.Field(discriminator="source_type")` with `Annotated` syntax.

### `UpdateLabelsRequest`

11. Represents a request to replace the target label filter.
12. `target_labels` is a list of strings. May be empty.

## Inputs

### `LocalCameraRequest`

| Field | Type | Default | Constraints | Required? |
|---|---|---|---|---|
| `source_type` | `Literal["local"]` | — | Must be `"local"` | Yes |
| `device_index` | `int` | `0` | `>= 0` | No (has default) |

### `RtspCameraRequest`

| Field | Type | Default | Constraints | Required? |
|---|---|---|---|---|
| `source_type` | `Literal["rtsp"]` | — | Must be `"rtsp"` | Yes |
| `rtsp_url` | `str` | — | Must start with `"rtsp://"` | Yes |

### `UpdateCameraRequest`

| Field | Type | Default | Constraints | Required? |
|---|---|---|---|---|
| `camera` | `LocalCameraRequest \| RtspCameraRequest` | — | Discriminated on `source_type` | Yes |

### `UpdateLabelsRequest`

| Field | Type | Default | Constraints | Required? |
|---|---|---|---|---|
| `target_labels` | `list[str]` | — | Must be a JSON array of strings; may be empty | Yes |

## Outputs

Validated Pydantic model instances. On validation failure, Pydantic raises its own `ValidationError` which FastAPI translates to a `422` response.

## Invariants

- All models are pure data definitions — no methods beyond validators.
- No model imports from other `model_lens` modules.
- `device_index` constraint (`ge=0`) is enforced via `pydantic.Field`, not a custom validator.
- `rtsp_url` constraint is enforced via a `@field_validator` decorated classmethod.
- Discriminated union uses `Annotated[..., Field(discriminator="source_type")]` syntax.

## Edge Cases

- Condition: `device_index` is negative.
  Expected: Pydantic validation error (422 at the API level).

- Condition: `rtsp_url` does not start with `"rtsp://"`.
  Expected: `ValueError` raised by field validator → Pydantic validation error (422).

- Condition: `source_type` value does not match `"local"` or `"rtsp"`.
  Expected: Pydantic discriminator error (422).

- Condition: `target_labels` is an empty list `[]`.
  Expected: Valid — empty list is accepted.

## Related

- [Config Router](./routers/config.md): imports `UpdateCameraRequest`, `UpdateLabelsRequest`, `LocalCameraRequest`.
- [CONVENTIONS.md](../../CONVENTIONS.md): HTTP error code conventions.
