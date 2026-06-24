# Test Specification: `test_stream.py`

## Source File Under Test
`src/model_lens/routers/stream.py`

## Test File
`tests/model_lens/routers/test_stream.py`

---

## `_event_generator`

### Happy Path — _event_generator

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_event_generator_emits_frame` | `unit` | Yields an SSE data line for a single frame. | Create a mock pipeline whose `get_queue().get()` returns a `PipelineResult` (with `jpeg_bytes`, `timestamp`, `source`, and `detections`) on first call, then raises `queue.Empty` followed by triggering idle timeout. Patch `_monotonic` to return controlled timestamps. | A pipeline with one queued frame | First yielded value is `b"data: ..."` containing JSON with keys `jpeg_b64`, `timestamp`, `source`, `detections` |
| `test_event_generator_serializes_detections` | `unit` | Each detection is serialized with `label`, `confidence`, `bounding_box` (as list), and `is_target`. | Create a mock pipeline returning a `PipelineResult` with two detections. Patch `_monotonic`. | A pipeline result with multiple detections | The `detections` array in the SSE payload contains dicts with keys `label`, `confidence`, `bounding_box`, `is_target`; `bounding_box` is a JSON array of 4 floats |
| `test_event_generator_base64_encoding` | `unit` | JPEG bytes are base64-encoded in the payload. | Create a mock pipeline returning a `PipelineResult` with known `jpeg_bytes`. Patch `_monotonic`. | Known JPEG bytes `b"\xff\xd8"` | `jpeg_b64` field in the payload equals `base64.b64encode(b"\xff\xd8").decode()` |

### Happy Path — GET /stream

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_stream_endpoint_returns_event_stream` | `unit` | Returns a StreamingResponse with `text/event-stream` media type. | Create a `TestClient` from a FastAPI app with `stream.router`. Set `app.state.pipeline` to a mock. Patch `_monotonic` to trigger immediate idle timeout after one frame. | `GET /stream` | Response `Content-Type` header is `text/event-stream` |

### Mock / Dependency Interaction

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_event_generator_calls_queue_get_with_timeout` | `unit` | Calls `queue.get(timeout=_QUEUE_TIMEOUT)`. | Create a mock pipeline with a mock queue. Patch `_monotonic` to trigger idle timeout on first empty iteration. | Empty queue | `queue.get` is called with `timeout=1.0` |

### Happy Path — Keepalive

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_event_generator_emits_keepalive` | `unit` | Emits a keepalive comment after 30 seconds of no frames. | Create a mock pipeline whose queue always raises `queue.Empty`. Patch `_monotonic` to simulate: first call returns `0.0`, subsequent calls return `30.0` (triggers keepalive), then `60.0` (triggers idle timeout). | No frames in queue | Generator yields `b": keepalive\n\n"` before closing |

### State Transitions

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_event_generator_idle_timeout_closes_stream` | `unit` | Closes the generator after 30 seconds of no frames. | Create a mock pipeline whose queue always raises `queue.Empty`. Patch `_monotonic` to simulate: initial time `0.0`, then `30.0` on next check. | No frames in queue | Generator terminates (raises `StopIteration`) after yielding keepalive |
| `test_event_generator_frame_resets_idle_timer` | `unit` | Receiving a frame resets the idle timeout. | Create a mock pipeline that returns a frame at simulated time `29.0`, then raises `queue.Empty` at time `30.0` (within 30s of last frame). Patch `_monotonic` accordingly. | Frame received at second 29 | Generator does NOT close at time `30.0`; continues waiting |
| `test_keepalive_does_not_reset_idle_timer` | `unit` | Keepalive emission does not extend the idle timeout. | Create a mock pipeline with empty queue. Patch `_monotonic` so that keepalive fires at `30.0` and idle timeout also fires at `30.0` in the same iteration. | No frames | Generator yields keepalive then terminates in the same iteration |
