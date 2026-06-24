# Config Router

## Overview

Exposes endpoints for reading and updating the `RuntimeConfig` at runtime. All mutations trigger `DetectionPipeline.update_config()` so that changes take effect immediately without restarting the server. Does not validate camera device reachability — that is a runtime concern owned by `DetectionPipeline`.

## Boundaries

- Owns: HTTP endpoint definitions for `/config`, `/config/camera`, `/config/labels`.
- Owns: serialization of `RuntimeConfig` and label map into JSON response dictionaries.
- Owns: mapping between request schema models and domain entity construction.
- Delegates: request body validation to Pydantic schemas (`UpdateCameraRequest`, `UpdateLabelsRequest`).
- Delegates: runtime state management to `DetectionPipeline` (via `update_config`, `get_config`).
- Delegates: label map access to `YOLOInferenceEngine` (via `get_label_map`).
- Must not: validate camera device reachability.
- Must not: use `Depends()` injection for pipeline/engine access (uses `cast()` on `request.app.state` directly).

## Dependencies

| Collaborator | Role | Allowed Interaction | Forbidden Interaction |
|---|---|---|---|
| `model_lens.detection_pipeline.DetectionPipeline` | Runtime state | `get_config()`, `update_config(new_config)` | Must not call `start()`, `stop()`, or access queue |
| `model_lens.inference_engine.YOLOInferenceEngine` | Label source | `get_label_map()` | Must not call `detect()` or `teardown()` |
| `model_lens.entities.RuntimeConfig` | Domain entity | Construct new instances for updates | — |
| `model_lens.entities.LocalCameraConfig` | Domain entity | Construct from `LocalCameraRequest` fields | — |
| `model_lens.entities.RtspCameraConfig` | Domain entity | Construct from `RtspCameraRequest` fields | — |
| `model_lens.schemas.UpdateCameraRequest` | Request validation | Type annotation on endpoint parameter | — |
| `model_lens.schemas.UpdateLabelsRequest` | Request validation | Type annotation on endpoint parameter | — |
| `model_lens.schemas.LocalCameraRequest` | Type dispatch | `isinstance` check for camera type branching | — |
| `fastapi.APIRouter` | Router framework | Define routes | — |
| `fastapi.responses.JSONResponse` | HTTP response | Construct with serialized dict | — |

Construction constraint: module-level `router = APIRouter()` instance. Accesses `request.app.state.pipeline` and `request.app.state.engine` via `cast()`.

## Behavior

### Internal Helper: `_serialize_config(config: RuntimeConfig) -> dict`

1. Inspects `config.camera` type:
   - If `LocalCameraConfig`: builds `{"source_type": "local", "device_index": camera.device_index}`.
   - If `RtspCameraConfig`: builds `{"source_type": "rtsp", "rtsp_url": camera.rtsp_url}`.
2. Returns `{"camera": <cam_dict>, "confidence_threshold": config.confidence_threshold, "target_labels": config.target_labels}`.

### Internal Helper: `_serialize_labels(label_map: dict[int, str]) -> dict`

3. Returns `{"valid_labels": list(label_map.values())}`.

### `GET /config`

4. Retrieves `DetectionPipeline` from `request.app.state.pipeline` via `cast()`.
5. Calls `pipeline.get_config()` to obtain the current `RuntimeConfig`.
6. Serializes via `_serialize_config()` and returns `JSONResponse`.

### `PUT /config/camera`

7. Retrieves `DetectionPipeline` from `request.app.state.pipeline` via `cast()`.
8. Calls `pipeline.get_config()` to get the current config.
9. Inspects `body.camera`:
   - If `LocalCameraRequest`: constructs `LocalCameraConfig(device_index=body.camera.device_index)`.
   - Else (RtspCameraRequest): constructs `RtspCameraConfig(rtsp_url=body.camera.rtsp_url)`.
10. Constructs a new `RuntimeConfig` with the new camera, preserving `target_labels` and `confidence_threshold` from the current config.
11. Calls `pipeline.update_config(new_config)`.
12. Calls `pipeline.get_config()` again and serializes the result via `_serialize_config()`.
13. Returns `JSONResponse` with the updated config.

### `GET /config/labels`

14. Retrieves `YOLOInferenceEngine` from `request.app.state.engine` via `cast()`.
15. Calls `engine.get_label_map()`.
16. Serializes via `_serialize_labels()` and returns `JSONResponse`.

### `PUT /config/labels`

17. Retrieves `DetectionPipeline` from `request.app.state.pipeline` via `cast()`.
18. Calls `pipeline.get_config()` to get the current config.
19. Constructs a new `RuntimeConfig` with `target_labels=body.target_labels`, preserving `camera` and `confidence_threshold` from the current config.
20. Calls `pipeline.update_config(new_config)`.
21. Calls `pipeline.get_config()` again and serializes the result via `_serialize_config()`.
22. Returns `JSONResponse` with the updated config.

## Inputs

### `PUT /config/camera` request body

| Field | Type | Constraints | Required? |
|---|---|---|---|
| `camera.source_type` | `Literal["local"] \| Literal["rtsp"]` | Discriminator | Yes |
| `camera.device_index` | `int` | `>= 0` (when `source_type == "local"`) | No (default 0) |
| `camera.rtsp_url` | `str` | Starts with `"rtsp://"` (when `source_type == "rtsp"`) | Yes (for rtsp) |

### `PUT /config/labels` request body

| Field | Type | Constraints | Required? |
|---|---|---|---|
| `target_labels` | `list[str]` | Array of strings; may be empty | Yes |

## Outputs

### `GET /config` response (200)

```json
{
  "camera": {"source_type": "local", "device_index": 0},
  "confidence_threshold": 0.5,
  "target_labels": ["cat", "dog"]
}
```

### `PUT /config/camera` response (200)

Same shape as `GET /config`.

### `GET /config/labels` response (200)

```json
{
  "valid_labels": ["person", "bicycle", "car", "cat", "dog"]
}
```

### `PUT /config/labels` response (200)

Same shape as `GET /config`.

### Error responses

| Status | Condition |
|---|---|
| `400 Bad Request` | Request body is not valid JSON (handled by app-level exception handler) |
| `422 Unprocessable Entity` | Pydantic validation fails |

## Invariants

- `confidence_threshold` is always present in `GET /config` responses but cannot be updated via any endpoint.
- The `camera` object in responses contains only fields relevant to the active source type.
- All mutation endpoints (`PUT`) call `pipeline.get_config()` after `update_config()` to return the actual current state (not the input).
- The `GET /config/labels` endpoint reads from the engine's label map, not from `RuntimeConfig.target_labels`.
- Label order in `GET /config/labels` matches the model's internal label map order.

## Edge Cases

- Condition: `PUT /config/camera` with unreachable device.
  Expected: `200 OK` returned — device reachability is not validated by this router.

- Condition: `PUT /config/labels` with empty list `[]`.
  Expected: `200 OK` — valid; no objects will be flagged as targets.

- Condition: Request body is not valid JSON.
  Expected: `400 Bad Request` (handled by the app-level `RequestValidationError` handler).

## Related

- [App](../app.md): mounts this router, defines the `RequestValidationError` handler.
- [Schemas](../schemas.md): request body models.
- [DetectionPipeline](../detection_pipeline.md): state management collaborator.
- [InferenceEngine](../inference_engine.md): label map source.
- [RuntimeConfig](../entities/runtime_config.md): domain entity constructed and returned.
- [CameraConfig](../entities/camera_config.md): `LocalCameraConfig`, `RtspCameraConfig` entities.
