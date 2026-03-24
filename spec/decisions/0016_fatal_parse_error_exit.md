# ADR 0016: ParseError from Inference Treated as Fatal (sys.exit)

**Date:** 2026-03-24
**Status:** Accepted

## Context

`InferenceEngine.detect()` can raise two categories of error:

- **`OperationError`** — a transient or recoverable failure during inference (e.g., a tensor
  shape mismatch on a single frame, a GPU OOM on a transient spike). The frame is bad, but
  the next frame may succeed.
- **`ParseError`** — the model output cannot be parsed because the model and label map are
  permanently mismatched (e.g., the model outputs 80 classes but the label map contains 20
  entries). No future frame will ever succeed.

The question is: when `ParseError` is raised inside the frame loop, should the pipeline skip
the frame and continue, log and degrade gracefully, or terminate the process?

## Decision

When `engine.detect()` raises `ParseError`, the Detection Pipeline:

1. Logs the error at `CRITICAL` level with the full exception detail.
2. Calls `sys.exit(1)` to terminate the process immediately.

No retry, no frame skip, no graceful degradation.

## Rationale

### Why is `ParseError` unrecoverable?

`ParseError` indicates a permanent structural mismatch between the model and the label map —
for example, the model outputs class index 79 but the label map has only 20 entries. This
mismatch cannot be resolved by retrying the same frame or waiting for a new config. Every
subsequent frame will produce the same error. Continuing to loop silently discards all
detections (if implemented as "skip frame") while appearing to serve a live stream, which is
worse than a clear failure.

### Why `sys.exit(1)` rather than raising an exception?

- **Thread boundary** — the frame loop runs in a background `threading.Thread`. Exceptions
  raised in threads are not propagated to the main thread automatically; they are silently
  swallowed unless the thread is joined and re-raises. Using `sys.exit(1)` terminates the
  entire process unconditionally from any thread.
- **No ambiguity** — `sys.exit(1)` produces a clear, visible process exit. A raised exception
  inside the thread would require specific thread exception-handling infrastructure to surface
  to the operator.
- **Fast failure** — the process exits before serving further (corrupted) results, preventing
  silent mislabelling of detections.

### Why not graceful shutdown (signal main thread)?

The preferred alternative would be to signal the main thread (e.g., via an `Event` or a queue)
and let the FastAPI shutdown hook invoke `stop()` cleanly. However:

- **Complexity** — this requires a dedicated inter-thread channel and logic in the main thread
  to watch for a "fatal error" signal, increasing pipeline complexity for an edge case that
  should never occur in a correctly deployed system.
- **Urgency** — a `ParseError` means the running server cannot produce correct results; the
  sooner the operator is notified (via process exit and logs), the sooner they can fix the
  misconfiguration. A graceful shutdown that takes several seconds delays the operator's
  feedback loop.
- **Post-MVP** — if process supervision (systemd, Docker restart policy) is added later, a
  clean `sys.exit(1)` is exactly what the supervisor expects to trigger a restart. A graceful
  shutdown via FastAPI lifecycle would exit with code 0, confusing supervisors.

### Why `CRITICAL` log level?

- **Severity** — a `ParseError` indicates the system is fundamentally broken; `CRITICAL` is
  the appropriate level for conditions that require immediate operator attention.
- **Distinguishable** — `CRITICAL` is distinct from `ERROR` (used for recoverable frame
  failures) and ensures the root cause is immediately visible in log aggregation systems that
  filter by level.

## `OperationError` Contrast

`OperationError` from `engine.detect()` is handled differently:

- Log at `ERROR` level.
- **Skip this frame** (continue the loop).

`OperationError` is transient; the next frame may succeed. `ParseError` is permanent; the
next frame will always fail with the same error.

## Alternatives Considered

- **Skip frame and continue** — rejected for `ParseError`; the pipeline would silently produce
  results with 0 detections on every frame indefinitely, with no signal that detection has
  failed permanently.
- **Raise exception in thread (no sys.exit)** — rejected; Python does not propagate thread
  exceptions to the main thread automatically. The exception would be silently swallowed.
- **Signal main thread for graceful shutdown** — deferred; adds inter-thread signalling
  complexity. Acceptable as a future improvement once process supervision is in scope.
- **Log and serve partial results (no detections)** — rejected; serving a stream with no
  detections while silently failing is worse UX than an explicit failure. The operator would
  have no indication the system is broken.

## Consequences

- A `ParseError` terminates the server process with exit code 1 and a `CRITICAL` log entry.
- Operators must check logs to understand why the process exited; the log message identifies
  the mismatch.
- Process supervisors (systemd, Docker) can restart the process on non-zero exit; the restart
  will fail again until the configuration is corrected, providing a clear feedback loop.
- The `InferenceEngine` and `CameraCapture` instances are not cleanly closed before exit.
  This is acceptable because `ParseError` represents a programming or configuration error, not
  expected runtime behaviour. Resource leaks at process exit are reclaimed by the OS.

## Superseded By / Supersedes

N/A
