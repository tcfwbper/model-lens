# Stream Router Specification for ModelLens

## Core Principle

`stream.py` is the Stream API router. It pushes a continuous Server-Sent Events (SSE)
stream of annotated frames and detection results to connected clients.

---

## Module Location

`src/model_lens/routers/stream.py`

---

## Endpoints

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

---

## Keepalive

When the queue is empty (no frame available within `1.0` second), the server sends an SSE
comment line to keep the connection alive and prevent proxy timeouts:

```
: keepalive\n\n
```

Keepalive comments are sent at most once per second of idle time. They carry no data and
are ignored by SSE clients.

---

## Server-Side Idle Timeout (Per Connection)

The SSE idle timeout is tracked **per connection**. Each new client connection starts its
own independent idle timer. The timer is reset to zero whenever a new `PipelineResult` is
successfully dequeued and sent to that client.

The connection is closed by the server after **30 seconds of continuous idle time** on that
connection (no frame dequeued and sent within 30 consecutive seconds). Keepalive comments
sent during the idle period do **not** reset the timer. When the timeout is reached, the
server closes the response stream cleanly (no error event). The client's built-in SSE
reconnect behaviour will re-establish the connection, which starts a fresh idle timer.

---

## Disconnect Handling

If the client disconnects before the server closes the stream, the server detects the
disconnect via the ASGI `disconnect` signal (or `asyncio.CancelledError` on the generator)
and exits the streaming coroutine cleanly without logging an error.

---

## Dependency

This router accesses the `DetectionPipeline` via `Depends(get_pipeline)` (see `app.py`
dependency injection).

---

## Constraints

- A single concurrent SSE consumer is the expected load. Multiple simultaneous `/stream`
  connections are not explicitly prevented but are not a design target; each connection
  consumes from the same shared queue independently (each `GET /stream` request gets its
  own queue read loop, which means only one consumer receives any given frame).
