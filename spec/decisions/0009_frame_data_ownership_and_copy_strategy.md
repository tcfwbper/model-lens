# ADR 0009: Frame Data Ownership and Copy Strategy

**Date:** 2026-03-24
**Status:** Accepted

## Context

`CameraCapture.read()` returns a `Frame` with pixel data. OpenCV's `cv2.VideoCapture.read()` returns a reference to an internal buffer that is reused across successive calls. The question is whether `Frame.data` should be a reference to this buffer or a copy.

## Decision

`CameraCapture` must copy the frame buffer returned by `cv2.VideoCapture.read()` before constructing the `Frame`. The `Frame.data` field is always a fresh `numpy.ndarray` copy, never a view or reference into the `VideoCapture` internal pool.

## Rationale

- **Buffer reuse in OpenCV** — `cv2.VideoCapture` maintains a small pool of internal buffers and reuses them across `read()` calls. A subsequent call to `read()` may overwrite the array returned by the previous call. Without copying, code holding a stale `Frame` reference sees corrupted or unrelated pixel data.
- **Decoupling lifetimes** — copying the buffer decouples `Frame` lifetime from `VideoCapture` state. The `Frame` can be held, queued, or transmitted without risk of data corruption.
- **Simplicity for InferenceEngine** — the engine receives `numpy.ndarray` and assumes it is safe to read repeatedly without copying again. If `Frame.data` were a reference to a reused buffer, the engine would have no way to know if the data was overwritten between receiving the `Frame` and executing `detect()`.

## Constraints and Trade-offs

- **Memory cost** — approximately 3–4 MB per frame (1080p RGB). At 30 FPS, this is 90–120 MB/s of allocation and copy overhead. This is acceptable for a local demo tool running on modern hardware; optimization to zero-copy (via memory-mapped buffers or ring queues) is deferred post-MVP.
- **CPU cost** — `numpy.ndarray.copy()` uses `memcpy`, which is fast but not free. On CPU-constrained systems, this could become a bottleneck at very high frame rates; trade-off is acceptable for MVP.
- **Colour space** — the copy preserves BGR; conversion to RGB (if required by the inference backend) is the responsibility of `InferenceEngine` and must be done without modifying the original `Frame.data` to maintain immutability semantics.

## Alternatives Considered

- **Reference semantics (no copy)** — faster but unsafe; stale `Frame` references become data corruption hazards, particularly in a multi-threaded environment with queued frames.
- **Lazy copy on access** — adds complexity and is fragile if the `Frame` is ever transmitted across threads or stored beyond one frame cycle.
- **Ring buffer with explicit ownership** — zero-copy but requires explicit reference counting and lifetime management; overkill for MVP.

## `RtspCamera` vs `LocalCamera` — No Difference

Both subclasses use the same OpenCV `VideoCapture` API and thus face the same buffer reuse problem. Both must copy the frame data; there is no optimization opportunity specific to RTSP or local devices.

## Frame Data Immutability

Although `Frame` is a non-frozen dataclass (because `numpy.ndarray` is not hashable), the `data` field is **treated as read-only** by all consumers:

- `InferenceEngine.detect()` must not modify `frame.data`. If RGB conversion is needed, create a separate array.
- The Stream API must not modify `frame.data` when encoding or annotating.
- Any future component receiving a `Frame` must treat `data` as immutable.

This is a contract, not enforced by the type system (enforcement would require memmap or other exotic structures).

## Consequences

- Every `Frame` is independent; no stale-data bugs from OpenCV buffer reuse.
- Memory and CPU overhead is predictable and acceptable for local demo use.
- Switching to zero-copy mechanisms (ring buffers, memory mapping) in the future requires minimal changes to `Frame` semantics; the copy can be replaced with a reference without changing the public interface.

## Superseded By / Supersedes

N/A
