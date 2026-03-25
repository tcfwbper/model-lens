# ADR 0013: Bounded Result Queue with Drop-Oldest Eviction

**Date:** 2026-03-24
**Status:** Accepted

## Context

The Detection Pipeline produces `PipelineResult` objects on a background thread and the Stream API
consumes them on the server's response thread. When the consumer (Stream API) is slower than the
producer (frame loop) — for example, due to a slow network connection or a paused browser tab —
the queue builds up. The queue must be bounded to avoid unbounded memory growth. When the queue
is full, the pipeline must decide what to do with the new result: block, drop the newest, or drop
the oldest.

## Decision

The result queue is bounded at **5 items** (`queue.Queue(maxsize=5)`).

When the pipeline attempts to publish a new `PipelineResult` and the queue is already full:

1. Discard the **oldest** item by calling `queue.Queue.get_nowait()` (non-blocking).
2. Log a `DEBUG` message indicating a frame was dropped due to a slow consumer.
3. Enqueue the new `PipelineResult` with `queue.Queue.put_nowait()`.

The pipeline never blocks waiting for the consumer to drain the queue.

## Rationale

### Why bounded?

An unbounded queue would allow memory to grow without limit if the consumer falls behind (e.g.,
slow network). A 5-item queue limits buffering to ~167 ms of frames at 30 FPS, after which
old frames are discarded — matching live-stream semantics where stale frames have no value.

### Why 5 items?

- **Enough for bursts** — 5 frames (~167 ms) smooths over brief consumer stalls (a GC pause,
  a transient syscall delay) without accumulating a large backlog.
- **Small enough to stay fresh** — beyond 5 frames, the consumer is so far behind that displaying
  old frames degrades the "live" experience more than simply increasing latency.
- **Low memory cost** — each JPEG-encoded frame is typically 50–200 KB; 5 frames peak at ~1 MB.

### Why drop-oldest over drop-newest?

- **Consumer gets the freshest data** — when the consumer catches up, it reads the most recent
  frame available, not a stale one from several seconds ago.
- **No blocking producer** — blocking on a full queue (`put()`) would stall the frame loop,
  causing inference and camera reads to back up behind the slow consumer.
- **Live-stream semantics** — a live camera feed has no value in replaying old frames; the user
  always wants to see what is happening now.

### Why not block on full queue?

Blocking the producer on a slow consumer would propagate backpressure up through the frame loop
to `camera.read()`, effectively pausing frame acquisition. This is undesirable: a paused consumer
(e.g., a browser tab in the background) would stall the entire pipeline, preventing the system
from serving any other consumer and causing the camera buffer to fill up.

## Alternatives Considered

- **Drop newest (discard incoming item when full)** — rejected because the consumer would receive
  a burst of old frames when it eventually re-connects, followed by a gap; fresh frames are more
  useful in a live-stream context.
- **Block producer until consumer drains** — rejected because a slow or disconnected consumer
  would freeze the frame loop.
- **Larger queue (e.g., 30 items)** — rejected; 30 items = ~1 s of buffering increases memory
  use and introduces noticeable lag before the consumer sees the current frame.
- **Dynamic queue size** — adds complexity without a clear benefit; the 5-item behaviour is
  sufficient for all expected consumer patterns.

## Consequences

- The Stream API always reads near-live frames; there is no replay buffer.
- A slow consumer silently drops frames; the `DEBUG` log is the only signal.
- Peak memory for the queue is bounded at approximately ~1 MB.
- If multiple SSE consumers are added in a future release, each will need its own queue or a
  fan-out mechanism; the current design assumes one consumer.

## Superseded By / Supersedes

N/A
