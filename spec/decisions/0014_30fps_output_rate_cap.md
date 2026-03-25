# ADR 0014: 30 FPS Output Rate Cap via Sleep-Based Pacing

**Date:** 2026-03-24
**Status:** Accepted

## Context

The Detection Pipeline reads frames from the camera, runs inference, and publishes results to a
queue. Some cameras can deliver frames faster than 30 FPS (e.g., a local webcam at 60 FPS or a
high-speed industrial camera). Publishing every frame at the source rate would waste CPU on
inference calls that produce results faster than any browser can consume them, increase GPU/CPU
load, and fill the result queue prematurely.

The question is: should the pipeline cap its output rate, and if so, at what rate and using what
mechanism?

## Decision

The Detection Pipeline enforces a **maximum output rate of 30 FPS** on the pipeline's published
results — not on the camera's capture rate.

The mechanism is **sleep-based pacing**:

- `_last_frame_time` records the `time.monotonic()` timestamp of the last successfully published
  frame.
- Minimum inter-frame interval: `min_interval = 1.0 / 30` (~33.3 ms).
- At step ④ of the frame loop (before reading the next frame), the pipeline checks
  `time.monotonic() - _last_frame_time`. If `remaining = min_interval - elapsed > 0`, it calls
  `time.sleep(remaining)` and then continues to the next loop iteration.
- If the source delivers frames slower than 30 FPS, no sleep is inserted; the pipeline runs at
  the source rate.

The 30 FPS cap applies to **output** (published `PipelineResult` objects) only. The camera is
never instructed to change its capture rate.

## Rationale

### Why cap at 30 FPS?

- **Sufficient for live video** — 30 FPS matches the conventional "fluid motion" threshold for
  video streams. Browsers and users perceive no quality difference between 30 FPS and 60 FPS for
  surveillance-style video.
- **Halves inference load on 60 FPS sources** — at 30 FPS, inference runs at most ~30 times/s
  instead of 60. For CPU-only inference this is a significant saving.
- **Queue stays fresh** — at 30 FPS, a 5-item queue holds ~167 ms of frames. At 60 FPS the same
  queue would hold only ~83 ms, making the system more sensitive to brief consumer stalls.

### Why sleep-based pacing instead of controlling the camera?

- **Camera API may not support rate control** — `cv2.VideoCapture` exposes `CAP_PROP_FPS` but
  its effect depends on driver and device; it is unreliable for local USB cameras and unsupported
  for some RTSP sources.
- **Decoupling** — the camera is allowed to run at its native rate. The pipeline simply discards
  the pacing opportunity (sleeps) when it would exceed the target rate. If the camera is slower
  than 30 FPS, no frames are dropped.
- **Simple implementation** — a single `time.sleep()` call in the loop is easy to reason about
  and test.

### Why sleep rather than busy-wait or frame skipping?

- **Busy-wait wastes CPU** — spinning and checking `time.monotonic()` in a tight loop consumes
  a CPU core for no useful work.
- **Frame skipping without sleep** — calling `camera.read()` and immediately discarding the
  frame still runs inference on the next frame immediately after, providing no rate reduction.
  Actually skipping the read would require tracking source timestamps, adding complexity.
- **Sleep is accurate enough** — at 30 FPS, individual frames have a 33.3 ms budget.
  `time.sleep()` has millisecond-level accuracy on modern Linux/macOS kernels, which is
  sufficient for this granularity.

## Constraints

- `time.sleep()` is called with the actual remaining duration, not a fixed `sleep(1/30)`. This
  avoids accumulated drift from processing time and ensures the output rate stays near 30 FPS
  even when inference takes variable time.
- The sleep occurs **before** `camera.read()`, not after publish. This keeps the camera buffer
  from filling up while the pipeline sleeps.
- The cap is hard-coded. It is not exposed as a configuration parameter because 30 FPS is
  sufficient for all expected use cases; tuning FPS is a post-MVP concern.

## Alternatives Considered

- **No cap (run at source rate)** — rejected; wastes inference compute and risks overwhelming
  CPU-bound machines at high-FPS sources.
- **Configurable FPS cap** — deferred; adds decision burden on users for MVP with no clear
  benefit over the 30 FPS default.
- **Set `CAP_PROP_FPS` on the VideoCapture** — rejected; unreliable across devices and RTSP
  sources; the pipeline cannot depend on this being honoured.
- **Drop alternate frames (1-in-N skip)** — rejected; fragile at non-integer multiples of 30,
  produces uneven output cadence.

## Consequences

- Pipeline CPU and inference load is bounded at 30 FPS regardless of source camera rate.
- The 30 FPS cap is invisible to consumers; the Stream API and browser do not need to know about
  it.
- Changing the cap in the future requires a code change, not a config change.

## Superseded By / Supersedes

N/A
