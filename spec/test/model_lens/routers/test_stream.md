# Test Specification: `test/model_lens/routers/test_stream.md`

## Source File Under Test

`src/model_lens/routers/stream.py`

## Test File

`test/model_lens/routers/test_stream.py`

## Imports Required

```python
import base64
import json
import time
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from model_lens.entities import DetectionResult
```

## Fixtures

Uses the shared `client` and `mock_pipeline` fixtures from `conftest.py`.

### `make_pipeline_result`

```python
@pytest.fixture
def make_pipeline_result():
    def _make(label="cat", confidence=0.9, is_target=True):
        result = MagicMock()
        result.jpeg_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 16  # minimal fake JPEG bytes
        result.timestamp = 1748000400.123456
        result.source = "local:0"
        detection = DetectionResult(
            label=label,
            confidence=confidence,
            bounding_box=(0.1, 0.2, 0.4, 0.6),
            is_target=is_target,
        )
        result.detections = [detection]
        return result
    return _make
```

---

## 1. Stream API — `GET /stream`

### 1.1 Happy Path — Event Payload Format

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_stream_returns_200` | `unit` | `GET /stream` returns HTTP 200 | one result in queue, then queue empty | `response.status_code == 200` |
| `test_stream_content_type_is_text_event_stream` | `unit` | Response `Content-Type` is `text/event-stream` | one result in queue | `"text/event-stream" in response.headers["content-type"]` |
| `test_stream_event_contains_jpeg_b64` | `unit` | SSE event payload contains `jpeg_b64` field | one result with known `jpeg_bytes` | `"jpeg_b64"` key present in parsed JSON; value is a non-empty string |
| `test_stream_event_jpeg_b64_is_valid_base64` | `unit` | `jpeg_b64` value is valid base64 | one result with known `jpeg_bytes` | `base64.b64decode(body["jpeg_b64"])` does not raise |
| `test_stream_event_jpeg_b64_decodes_to_original_bytes` | `unit` | Decoded `jpeg_b64` matches original `jpeg_bytes` | one result with known `jpeg_bytes` | `base64.b64decode(body["jpeg_b64"]) == result.jpeg_bytes` |
| `test_stream_event_contains_timestamp` | `unit` | SSE event payload contains `timestamp` field | one result with `timestamp=1748000400.123456` | `body["timestamp"] == 1748000400.123456` |
| `test_stream_event_contains_source` | `unit` | SSE event payload contains `source` field | one result with `source="local:0"` | `body["source"] == "local:0"` |
| `test_stream_event_contains_detections` | `unit` | SSE event payload contains `detections` array | one result with one detection | `len(body["detections"]) == 1` |
| `test_stream_event_detection_label` | `unit` | Detection object contains correct `label` | detection with `label="cat"` | `body["detections"][0]["label"] == "cat"` |
| `test_stream_event_detection_confidence` | `unit` | Detection object contains correct `confidence` | detection with `confidence=0.9` | `body["detections"][0]["confidence"] == 0.9` |
| `test_stream_event_detection_bounding_box` | `unit` | Detection object contains correct `bounding_box` | detection with `bounding_box=(0.1, 0.2, 0.4, 0.6)` | `body["detections"][0]["bounding_box"] == [0.1, 0.2, 0.4, 0.6]` |
| `test_stream_event_detection_is_target_true` | `unit` | Detection object contains `is_target=True` | detection with `is_target=True` | `body["detections"][0]["is_target"] is True` |
| `test_stream_event_detection_is_target_false` | `unit` | Detection object contains `is_target=False` | detection with `is_target=False` | `body["detections"][0]["is_target"] is False` |
| `test_stream_event_empty_detections` | `unit` | `detections` array is empty when no objects detected | result with `detections=[]` | `body["detections"] == []` |
| `test_stream_event_line_format` | `unit` | Each SSE event line starts with `data: ` | one result in queue | raw chunk starts with `b"data: "` |
| `test_stream_event_ends_with_double_newline` | `unit` | Each SSE event ends with `\n\n` | one result in queue | raw chunk ends with `b"\n\n"` |

### 1.2 Happy Path — Keepalive

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_stream_keepalive_sent_when_queue_empty` | `unit` | When the queue is empty for 1 second, a keepalive comment is sent | queue is empty; mock `time.monotonic` to advance by 1.0 s | a chunk matching `b": keepalive\n\n"` is received |
| `test_stream_keepalive_format` | `unit` | Keepalive line is an SSE comment (starts with `: `) | same as above | raw chunk is exactly `b": keepalive\n\n"` |

### 1.3 Happy Path — Idle Timeout

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_stream_idle_timeout_closes_connection` | `unit` | After 30 seconds of idle time the server closes the stream | queue is empty; mock `time.monotonic` to advance by 30.0 s without any frame dequeued | the response iterator ends (no more chunks); connection is closed cleanly |
| `test_stream_idle_timer_resets_on_frame` | `unit` | Receiving a frame resets the idle timer | one frame dequeued at t=25 s; mock `time.monotonic` to advance to t=54 s (25 s after the frame) | connection remains open at t=54 s (only 29 s since last frame) |
| `test_stream_keepalive_does_not_reset_idle_timer` | `unit` | Keepalive comments sent during idle do **not** reset the 30-second idle timer | queue is empty; mock `time.monotonic` to advance in 1 s steps so multiple keepalives are emitted, but total elapsed time reaches 30 s without any frame dequeued | the response iterator ends at the 30 s mark despite keepalives having been sent; connection is closed cleanly |

### 1.4 Resource Cleanup

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_stream_client_disconnect_does_not_raise` | `unit` | Closing the `TestClient` stream mid-flight does not raise a server-side exception | open stream with `stream=True`; close the response before all events are consumed | no exception is raised; `response.close()` completes cleanly |

---

## Summary Table

| Entity | Test Count (approx.) | unit | e2e | race | Key Concerns |
|---|---|---|---|---|---|
| `GET /stream` | 21 | 21 | 0 | 0 | event format, base64, keepalive, idle timeout (keepalive does not reset timer), disconnect |
