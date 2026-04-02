# Config Router Specification for ModelLens

## Core Principle

`config.py` is the Config API router. It exposes endpoints for reading and updating the
`RuntimeConfig` at runtime. All mutations trigger `DetectionPipeline.update_config()` so
that changes take effect immediately without restarting the server.

---

## Module Location

`src/model_lens/routers/config.py`

---

## Base Path: `/config`

This router is included on the root FastAPI app without a prefix. All route paths are
defined with the `/config` prefix inline (e.g. `@router.get("/config")`).

---

## Endpoints

### `GET /config`

Returns the current `RuntimeConfig` as JSON.

**Response `200 OK`:**

```json
{
  "camera": {
    "source_type": "local",
    "device_index": 0
  },
  "confidence_threshold": 0.5,
  "target_labels": ["cat", "dog"]
}
```

For `source_type = "rtsp"`:

```json
{
  "camera": {
    "source_type": "rtsp",
    "rtsp_url": "rtsp://192.168.1.10/stream"
  },
  "confidence_threshold": 0.5,
  "target_labels": []
}
```

- `confidence_threshold` is always present in the response (read-only; reflects the value
  fixed at startup from `AppConfig`).
- The `camera` object contains **only the fields relevant to the active `source_type`**:
  `device_index` is omitted when `source_type = "rtsp"`, and `rtsp_url` is omitted when
  `source_type = "local"`.

---

### `PUT /config/camera`

Replaces the camera configuration. Triggers `DetectionPipeline.update_config()` with a new
`RuntimeConfig` that carries the updated `CameraConfig` and preserves all other fields.

**Request body:**

```json
// source_type = "local"
{
  "camera": {
    "source_type": "local",
    "device_index": 0
  }
}

// source_type = "rtsp"
{
  "camera": {
    "source_type": "rtsp",
    "rtsp_url": "rtsp://192.168.1.10/stream"
  }
}
```

**Validation rules (Pydantic, raises `422` on failure):**

| Field | Rule |
|---|---|
| `source_type` | Must be `"local"` or `"rtsp"` |
| `device_index` | Required and `>= 0` when `source_type = "local"` |
| `rtsp_url` | Required, non-empty, and must start with `rtsp://` when `source_type = "rtsp"` |

**Response `200 OK`:** The full updated `RuntimeConfig` in the same shape as `GET /config`.

**Error responses:**

| Status | Condition |
|---|---|
| `400 Bad Request` | Request body is not valid JSON |
| `422 Unprocessable Entity` | Pydantic validation fails (wrong type, missing field, constraint violated) |

**Note:** Whether the camera device is actually reachable is **not** validated by this
endpoint. Camera connectivity is a runtime concern owned by `DetectionPipeline`. If the
device is unreachable, the pipeline logs the error and waits for a new config; the Config
API returns `200 OK` regardless.

---

### `GET /config/labels`

Returns the full set of labels known to the inference engine (i.e. the model's label map).
This is distinct from the active filter in `RuntimeConfig.target_labels`.

**Response `200 OK`:**

```json
{
  "valid_labels": ["person", "bicycle", "car", "cat", "dog"]
}
```

- The list is sourced directly from `YOLOInferenceEngine.get_label_map()` (the engine stored
  in `app.state.engine`), not from `RuntimeConfig`.
- The order of labels matches the model's internal label map order.

---

### `PUT /config/labels`

Replaces the target labels list. Triggers `DetectionPipeline.update_config()` with a new
`RuntimeConfig` that carries the updated `target_labels` and preserves all other fields.

**Request body:**

```json
{
  "target_labels": ["cat", "dog", "person"]
}
```

**Validation rules (Pydantic, raises `422` on failure):**

| Field | Rule |
|---|---|
| `target_labels` | Must be a JSON array of strings; may be empty (`[]`) |

**Response `200 OK`:** The full updated `RuntimeConfig` in the same shape as `GET /config`.

**Error responses:**

| Status | Condition |
|---|---|
| `400 Bad Request` | Request body is not valid JSON |
| `422 Unprocessable Entity` | Pydantic validation fails |

---

## Dependency

This router accesses `app.state` directly via the `Request` object:

- `request.app.state.pipeline` — the `DetectionPipeline` instance, used by all mutation
  endpoints (`PUT /config/camera`, `PUT /config/labels`) and `GET /config`.
- `request.app.state.engine` — the `YOLOInferenceEngine` instance, used by `GET /config/labels`
  to read the model's label map.

No `Depends()` injection is used; both values are cast with `cast()` at the call site.

---

## Constraints

- `confidence_threshold` is exposed in `GET /config` responses but cannot be updated via
  any Config API endpoint. Any `PUT` request that attempts to include `confidence_threshold`
  in the body must have that field ignored (not rejected).
