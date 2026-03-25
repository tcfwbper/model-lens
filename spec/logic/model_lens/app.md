# App Specification for ModelLens

## Core Principle

`app.py` is the FastAPI application entry point. It owns the server lifecycle, mounts all API
routers and static assets, and wires together the `DetectionPipeline`, `InferenceEngine`, and
`RuntimeConfig` into a single running process. All HTTP concerns — routing, request validation,
response serialisation, and error handling — are defined here or in the routers it mounts.

---

## Module Location

`src/model_lens/app.py`

---

## Application Lifecycle

The FastAPI application uses a `lifespan` context manager (the modern FastAPI/Starlette
lifecycle hook) to manage startup and shutdown in the correct order.

### Startup Sequence

```
lifespan() enters
    │
    ▼
1. Load AppConfig (ConfigLoader)
    └── ConfigurationError → log CRITICAL, sys.exit(1)
    │
    ▼
2. Construct TorchInferenceEngine(
       model_path=app_config.model.model_path,
       confidence_threshold=app_config.model.confidence_threshold,
       labels_path=app_config.model.labels_path,
   )
    └── ConfigurationError / OperationError / ParseError → log CRITICAL, sys.exit(1)
    │
    ▼
3. Construct initial RuntimeConfig from AppConfig
    │
    ▼
4. Construct DetectionPipeline(engine, initial_config)
    │
    ▼
5. DetectionPipeline.start()
    └── RuntimeError (double-start) → log CRITICAL, sys.exit(1)
    │
    ▼
6. yield  ← application serves requests
    │
    ▼
(shutdown signal received)
```

### Shutdown Sequence

```
lifespan() resumes after yield
    │
    ▼
1. DetectionPipeline.stop()   ← blocks until background thread exits
    │
    ▼
2. TorchInferenceEngine.teardown()
    │
    ▼
lifespan() exits
```

### Rules

- All startup steps run sequentially in the `lifespan` coroutine before `yield`.
- Any unhandled exception during startup logs at `CRITICAL` and calls `sys.exit(1)`.
- `DetectionPipeline.stop()` is always called during shutdown even if startup partially
  failed, provided the pipeline was constructed (use a `try/finally` guard around `yield`).
- The `InferenceEngine` is torn down **after** the pipeline is stopped; the pipeline must
  not call `engine.detect()` after `stop()` returns.

---

## Routers

The application is composed of three routers mounted on the root FastAPI app:

| Router module | Mount prefix | Responsibility |
|---|---|---|
| `config_router` | `/config` | Config API (CRUD for `RuntimeConfig`) |
| `stream_router` | (none) | Stream API (`/stream`) |
| `health_router` | (none) | Health check (`/healthz`) |

Static assets are mounted separately (see Static Assets section).

---

## Config API

### Base path: `/config`

#### `GET /config`

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

#### `PUT /config/camera`

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

#### `PUT /config/labels`

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

## Stream API

### `GET /stream`

Pushes a continuous SSE stream of annotated frames and detection results to the client.

**Response content type:** `text/event-stream`

**SSE event format (one event per frame):**

Each event is a single SSE `data:` line containing a JSON object:

```
data: {"jpeg_b64":"<base64-encoded JPEG string>","timestamp":1748000400.123,"source":"local:0","detections":[{"label":"cat","confidence":0.87,"bounding_box":[0.1,0.2,0.4,0.6],"is_target":true}]}\n\n
```

JSON payload schema:

| Field | Type | Description |
|---|---|---|
| `jpeg_b64` | `str` | Base64-encoded JPEG bytes (standard alphabet, no line breaks) |
| `timestamp` | `float` | POSIX timestamp copied from `PipelineResult.timestamp` |
| `source` | `str` | Camera source identifier copied from `PipelineResult.source` |
| `detections` | `array` | Array of detection objects (see below); may be empty |

Each detection object:

| Field | Type | Description |
|---|---|---|
| `label` | `str` | Human-readable label string |
| `confidence` | `float` | Confidence score in `(0.0, 1.0]` |
| `bounding_box` | `[x1, y1, x2, y2]` | Normalised floats in `[0.0, 1.0]`, top-left origin |
| `is_target` | `bool` | `True` if label is in `target_labels` |

**Keepalive:**

When the queue is empty (no frame available within `1.0` second), the server sends an SSE
comment line to keep the connection alive and prevent proxy timeouts:

```
: keepalive\n\n
```

Keepalive comments are sent at most once per second of idle time. They carry no data and
are ignored by SSE clients.

**Server-side idle timeout (per connection):**

The SSE idle timeout is tracked **per connection**. Each new client connection starts its
own independent idle timer. The timer is reset to zero whenever a new `PipelineResult` is
successfully dequeued and sent to that client.

The connection is closed by the server after **30 seconds of continuous idle time** on that
connection (no frame dequeued and sent within 30 consecutive seconds). Keepalive comments
sent during the idle period do **not** reset the timer. When the timeout is reached, the
server closes the response stream cleanly (no error event). The client's built-in SSE
reconnect behaviour will re-establish the connection, which starts a fresh idle timer.

**Disconnect handling:**

If the client disconnects before the server closes the stream, the server detects the
disconnect via the ASGI `disconnect` signal (or `asyncio.CancelledError` on the generator)
and exits the streaming coroutine cleanly without logging an error.

---

## Health Check

### `GET /healthz`

Returns `200 OK` with an empty body. Used by process supervisors and load balancers to
confirm the process is alive. No pipeline or camera status is included.

**Response `200 OK`:** Empty body.

---

## Static Assets

### Frontend build location

The compiled frontend is built from `src/ui/` and output to `dist/`. The FastAPI app
serves files from the `dist/` directory, resolved relative to the installed package
using `importlib.resources` (or equivalent package-data resolution).

### Routing

| Path | Behaviour |
|---|---|
| `GET /` | Serves `dist/index.html` directly with `text/html` content type |
| `GET /static/{path}` | Serves files from `dist/static/` via `StaticFiles` mount |

**Rules:**

- `GET /` serves `index.html` directly (not a redirect). The response includes an `ETag`
  header computed as the **MD5 hex digest** of the file's raw byte content
  (e.g., `ETag: "d41d8cd98f00b204e9800998ecf8427e"`). The value is a quoted string per
  the HTTP specification. This enables browser caching and conditional `GET` requests via
  `If-None-Match`.
- All other unmatched paths that do not begin with `/config`, `/stream`, `/healthz`, or
  `/static` fall through to a `404 Not Found` response (FastAPI default).
- `StaticFiles` is mounted at `/static` and serves the compiled JS, CSS, and other assets
  from `dist/static/`.
- If the `dist/` directory or `dist/index.html` cannot be resolved at startup (package not
  installed correctly), the server logs `CRITICAL` and calls `sys.exit(1)`.

---

## Pydantic Request/Response Models

All request and response bodies are defined as Pydantic v2 models. They are defined in a
dedicated module `src/model_lens/schemas.py` and imported by the routers.

### `LocalCameraRequest`

```python
class LocalCameraRequest(BaseModel):
    source_type: Literal["local"]
    device_index: int = 0

    @field_validator("device_index")
    def device_index_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError(f"device_index must be >= 0, got {v!r}")
        return v
```

### `RtspCameraRequest`

```python
class RtspCameraRequest(BaseModel):
    source_type: Literal["rtsp"]
    rtsp_url: str

    @field_validator("rtsp_url")
    def rtsp_url_valid(cls, v: str) -> str:
        if not v.startswith("rtsp://"):
            raise ValueError(f"rtsp_url must start with rtsp://, got {v!r}")
        return v
```

### `UpdateCameraRequest`

```python
class UpdateCameraRequest(BaseModel):
    camera: LocalCameraRequest | RtspCameraRequest = Field(discriminator="source_type")
```

### `UpdateLabelsRequest`

```python
class UpdateLabelsRequest(BaseModel):
    target_labels: list[str]
```

### `DetectionResultResponse`

```python
class DetectionResultResponse(BaseModel):
    label: str
    confidence: float
    bounding_box: tuple[float, float, float, float]
    is_target: bool
```

### `FrameEventResponse`

Used by the SSE event payload:

```python
class FrameEventResponse(BaseModel):
    jpeg_b64: str
    timestamp: float
    source: str
    detections: list[DetectionResultResponse]
```

### `RuntimeConfigResponse`

```python
class LocalCameraResponse(BaseModel):
    source_type: Literal["local"]
    device_index: int

class RtspCameraResponse(BaseModel):
    source_type: Literal["rtsp"]
    rtsp_url: str

class RuntimeConfigResponse(BaseModel):
    camera: LocalCameraResponse | RtspCameraResponse
    confidence_threshold: float
    target_labels: list[str]
```

---

## Error Response Format

All error responses use FastAPI's standard `HTTPException` shape:

```json
{ "detail": "<human-readable message>" }
```

Custom error messages are used for domain-specific failures.
Pydantic validation errors use FastAPI's default `422` response body (array of error
objects under `"detail"`).
Any unhandled exceptions raised in the application layer or unexpected server failures automatically result in a `500 Internal Server Error` response.

---

## HTTP Status Code Map

The translation from internal failures to HTTP codes must follow these mappings:

| Status Code | Condition | Meaning |
|---|---|---|
| `400 Bad Request` | Malformed request body | Client sent invalid payload format (e.g., bad JSON) |
| `404 Not Found` | Unknown path or resource | Client requested a non-existent URL |
| `422 Unprocessable Entity` | Data validation fails | Request is grammatically correct but semantically invalid |
| `500 Internal Server Error` | Unexpected server failure | Unhandled exceptions in the application layer |

---

## Dependency Injection

The `DetectionPipeline` instance is stored in FastAPI's `app.state` during the lifespan
startup and accessed by routers via a FastAPI dependency:

```python
def get_pipeline(request: Request) -> DetectionPipeline:
    return request.app.state.pipeline
```

Routers declare this dependency with `Depends(get_pipeline)`. This avoids module-level
globals and makes the dependency explicit and testable.

---

## Module Structure

```
src/model_lens/
├── app.py          ← FastAPI app factory, lifespan, router mounting
├── schemas.py      ← Pydantic request/response models
├── routers/
│   ├── __init__.py
│   ├── config.py   ← Config API router (/config)
│   ├── stream.py   ← Stream API router (/stream)
│   └── health.py   ← Health check router (/healthz)
└── ...
```

---

## Constraints and Non-Goals

- No authentication or session management is in scope.
- A single concurrent SSE consumer is the expected load. Multiple simultaneous `/stream`
  connections are not explicitly prevented but are not a design target; each connection
  consumes from the same shared queue independently (each `GET /stream` request gets its
  own queue read loop, which means only one consumer receives any given frame).
- The server does not support HTTPS termination directly; TLS is expected to be handled by
  a reverse proxy if required.
- `confidence_threshold` is exposed in `GET /config` responses but cannot be updated via
  any Config API endpoint. Any `PUT` request that attempts to include `confidence_threshold`
  in the body must have that field ignored (not rejected).
