# Schemas Specification for ModelLens

## Core Principle

`schemas.py` defines all Pydantic v2 request and response models used by the API routers.
These models are the single source of truth for HTTP request validation and response
serialisation. They are imported by the router modules and must not contain any business
logic or side effects.

---

## Module Location

`src/model_lens/schemas.py`

---

## Request Models

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

---

## Response Models

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

- The `camera` object contains **only the fields relevant to the active `source_type`**:
  `device_index` is omitted when `source_type = "rtsp"`, and `rtsp_url` is omitted when
  `source_type = "local"`.
- `confidence_threshold` is always present in the response (read-only; reflects the value
  fixed at startup from `AppConfig`).
