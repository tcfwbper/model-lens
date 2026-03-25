# ADR 0020: Pydantic Discriminated Union for Camera Configuration

**Date:** 2026-03-24
**Status:** Accepted

## Context

The camera configuration supports two mutually exclusive source types:

- **`"local"`** — requires `device_index: int` (a non-negative integer); `rtsp_url` is not
  applicable.
- **`"rtsp"`** — requires `rtsp_url: str` (a non-empty URL starting with `rtsp://`);
  `device_index` is not applicable.

Both request (`PUT /config/camera`) and response (`GET /config`) payloads must carry only the
fields relevant to the active source type. This means:

- `LocalCameraRequest` / `LocalCameraResponse` contains `source_type` + `device_index`.
- `RtspCameraRequest` / `RtspCameraResponse` contains `source_type` + `rtsp_url`.

The wrapping `UpdateCameraRequest` model must accept either variant in the `camera` field and
delegate validation to the correct model based on the value of `source_type`.

A naive single-model approach (e.g., `Optional[int] device_index`, `Optional[str] rtsp_url`
on one model) would allow invalid combinations (e.g., both fields present, or neither field
present) and would include irrelevant fields in response payloads.

## Decision

Use Pydantic v2 discriminated unions with `Field(discriminator="source_type")`:

```python
from pydantic import BaseModel, Field
from typing import Literal

class LocalCameraRequest(BaseModel):
    source_type: Literal["local"]
    device_index: int = 0

class RtspCameraRequest(BaseModel):
    source_type: Literal["rtsp"]
    rtsp_url: str

class UpdateCameraRequest(BaseModel):
    camera: LocalCameraRequest | RtspCameraRequest = Field(discriminator="source_type")
```

Pydantic reads `source_type` first and dispatches validation to the matching model variant.
An unknown `source_type` value raises a `ValidationError` that FastAPI converts to `422`.

The same discriminated-union pattern is used for response models
(`LocalCameraResponse | RtspCameraResponse`) to ensure only the relevant fields appear in
serialised responses.

## Rationale

- **Type safety** — each variant carries only the fields that are valid for that source type.
  There is no representation for an impossible state (e.g., a `"local"` config with an
  `rtsp_url`).
- **Clean serialisation** — Pydantic serialises the active variant only; irrelevant fields are
  absent from the JSON output, matching the API specification exactly.
- **Pydantic v2 native** — `Field(discriminator=...)` is the idiomatic Pydantic v2 approach
  for tagged unions. It produces accurate OpenAPI schema output (a `oneOf` with a discriminator
  property), which improves generated client code and API documentation.
- **Single point of validation** — `source_type`-specific field constraints (`device_index >= 0`,
  `rtsp_url starts with rtsp://`) live on the leaf models. Adding a third source type requires
  adding a new leaf model and extending the union; no existing model changes.
- **Automatic `422` on invalid `source_type`** — Pydantic raises `ValidationError` for an
  unrecognised `source_type` (e.g., `"usb"`), which FastAPI correctly converts to an HTTP `422`
  response without any custom error-handling code.

## Alternatives Considered

- **Single flat model with optional fields** — rejected because it allows invalid combinations
  (both `device_index` and `rtsp_url` present; neither present) and offers no compile-time
  or schema-level guarantee about exclusivity. Validation logic would have to be duplicated
  in a root `model_validator`.
- **`Union` without discriminator** — Pydantic v2 still supports untagged unions but must
  attempt each variant in order until one succeeds. This is slower, produces less specific
  validation error messages, and does not generate a proper OpenAPI discriminator. Rejected in
  favour of the explicit discriminator.
- **Custom validator on `UpdateCameraRequest`** — using a `@model_validator` to branch on
  `source_type` and manually validate fields is functionally equivalent but adds boilerplate
  and duplicates logic already handled by Pydantic's discriminated union machinery.

## Consequences

- Each source type is a separate Pydantic model; adding a new source type requires a new model
  class and a union extension, not modifying existing models.
- Response payloads contain only the fields for the active camera type; no `null` fields appear
  in the output.
- The OpenAPI schema emitted by FastAPI correctly represents the discriminated union as
  `oneOf` with a `discriminator` object, which enables accurate client code generation.
- Developers working on camera configuration must update both request and response union types
  when adding a new source type (four model classes total per new source type).

## Superseded By / Supersedes
N/A
