# ADR 0008: Concurrency and Thread Safety Strategy

**Date:** 2026-03-24
**Status:** Accepted

## Context

The Detection Pipeline runs continuously in a loop acquiring frames and running inference. Simultaneously, the Config API may update `RuntimeConfig` and the browser may request frame data via the Stream API. Multiple threads access shared data structures (`CameraCapture`, `InferenceEngine`, `RuntimeConfig`) without explicit coordination.

## Decision

The system employs fine-grained per-component thread safety:

1. **`CameraCapture.read()` and `close()`** — each acquisition is protected by a per-instance `threading.Lock`.
2. **`InferenceEngine.detect()`** — each inference call is protected by a per-instance `threading.Lock`.
3. **`RuntimeConfig` atomic replacement** — the Detection Pipeline holds a reference to the current instance; replacement is a single atomic pointer swap under a lock.

No global lock is used. Each component is responsible for its own thread safety.

## Rationale

- **Per-instance locks** avoid contention bottlenecks. Locking the engine does not block camera access and vice versa.
- **`threading.Lock` (not RLock or Semaphore)** — the simplest synchronization primitive is sufficient. Each lock is acquired once per operation and always released before any blocking I/O. No recursive locking or counting is needed.
- **Atomic config swap** — `RuntimeConfig` replacement is a single pointer assignment under a lock, ensuring the pipeline always reads a coherent configuration snapshot without holding the lock during frame processing.
- **No inter-thread signalling** — the pipeline does not wait for the camera to be "ready" or for the engine to be "initialized"; all initialization happens before the pipeline starts.

## Constraints

- The lock acquired by `read()` is held during retry sleeps (1 s, 2 s, 4 s intervals). A caller that needs prompt shutdown should stop calling `read()` before calling `close()` rather than expecting `close()` to interrupt a sleeping `read()`.
- `detect()` holds its lock for the entire inference duration. If inference is slow (e.g., on a CPU-only machine), concurrent detection requests will queue behind this lock. This is acceptable for MVP; a future optimization could introduce a thread pool for inference.

## Alternatives Considered

- **Global lock for all components** — simpler implementation but introduces unnecessary contention and reduces throughput as camera, inference, and config updates all serialize on a single lock.
- **Lock-free (atomic/compare-and-swap)** — more complex and error-prone for the structures involved; not worth the complexity for the throughput and latency targets of this demo tool.
- **Explicit signalling channels (queue/event)** — adds inter-component coupling and message marshalling overhead. The current in-loop config reading is simpler.

## Consequences

- Each component guarantees safety on its own; the pipeline does not need to coordinate locks.
- `RuntimeConfig` replacement is fast (pointer swap); no serialization overhead during frame processing.
- If a caller holds the camera or engine lock for an extended period (e.g., during inference), other threads attempting to read or detect will block. This is expected and correct behaviour.
- Adding a new component that shares mutable state requires adding a corresponding per-instance lock and documenting any lock ordering (e.g., "always acquire camera lock before engine lock") if multiple locks must be held simultaneously.

## Superseded By / Supersedes

N/A
