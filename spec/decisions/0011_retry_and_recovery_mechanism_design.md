# ADR 0011: Retry and Recovery Mechanism Design

**Date:** 2026-03-24
**Status:** Accepted

## Context

Camera streams can be interrupted by transient network issues (RTSP reconnect), USB disconnections (local camera reset), or driver hiccups. When `cv2.VideoCapture.read()` fails, the question is how many times to retry, how long to wait between retries, and when to give up.

## Decision

`CameraCapture.read()` implements a **3-attempt retry strategy** with exponential backoff and jitter:

| Attempt | Wait before | Total elapsed |
|---|---|---|
| 1 (initial)   | 0 s          | 0 s            |
| 2 (retry 1)   | 1 s + jitter | 1 s + jitter   |
| 3 (retry 2)   | 2 s + jitter | 3 s + 2×jitter |
| — (fail)      | 4 s + jitter | —              |

- **Jitter** is `uniform(0.0, 1.0)` seconds added to each wait.
- On each retry, the old `cv2.VideoCapture` handle is released and a new one is opened.
- If all 3 attempts are exhausted, `OperationError` is raised.

## Rationale

### Why 3 Attempts?

- **Covers transient glitches** — a single dropped frame, a brief network stall, or a camera driver hiccup recovers within one retry.
- **Avoids excessive retries** — retrying indefinitely (or dozens of times) would hang the pipeline forever on hardware failure, appearing to users as a hang rather than a prompt failure.
- **Balances resilience and responsiveness** — 3 attempts with exponential backoff gives ~3-5 seconds of recovery time before failing, which is long enough for most transient issues but not so long that users perceive unresponsive behaviour.

### Why Exponential Backoff (1 s, 2 s)?

- **Respects connection cool-down** — network devices and servers often need time to reset state after a failed connection attempt. Immediate retry (without backoff) often fails again.
- **Escalating timeouts** — later retries wait longer, assuming that if the first retry didn't work, the issue may take longer to resolve.
- **Prevents thundering herd** — if a central RTSP server drops and multiple clients connect to it simultaneously, exponential backoff naturally stagger reconnections, reducing load spikes.

### Why Jitter?

- **Breaks synchronization** — multiple clients experiencing the same connection failure (e.g., a brief network outage) would all retry at the exact same second without jitter, causing a load spike when the service recovers. Jitter spreads retries uniformly across the wait interval.
- **Example of thundering herd problem** — 1000 clients all retry at second N+1.0 exactly, overwhelming the server with a sudden 1000-RPS spike. With jitter, retries spread over [N+1.0, N+2.0], reducing peak load.
- **Uniform distribution** — `uniform(0.0, 1.0)` is simple and provides good spread without introducing distribution bias.

## Failure Modes Covered

| Failure | Recovery? | Timeline |
|---|---|---|
| Brief network glitch | ✅ Retry 1 succeeds | ~1 s |
| Camera driver hiccup | ✅ Retry 2 succeeds | ~3 s |
| Camera disconnected (hardware fault) | ❌ All 3 fail | ~5 s |
| RTSP server offline (temporary outage) | ✅ Retry 1–2 succeed | ~1–3 s |
| RTSP server offline (permanent) | ❌ All 3 fail | ~5 s |
| USB camera removed | ❌ All 3 fail immediately | <0.1 s |

## Alternatives Considered

- **No retry, fail immediately** — rejected; transient glitches are common and recoverable.
- **Retry indefinitely** — rejected; avoids declaring unrecoverable failures, causing the pipeline to hang indefinitely.
- **Fixed wait (e.g., 5 s between all retries)** — rejected; doesn't escalate severity of waits and provides no benefit over exponential backoff.
- **Jitter only on last retry** — rejected; thundering herd is most likely on first reconnect, so jitter on all waits is valuable.
- **Random (not uniform) jitter** — `uniform(0.0, 1.0)` is simpler and sufficient; Gaussian distribution would add complexity for minimal benefit.

## Hard-Coded vs Configurable

The retry strategy (3 attempts, 1/2/4 s waits, jitter) is **hard-coded** in `CameraCapture`. It is not exposed as a configuration parameter because:

- MVP users have no need to tune retry behaviour; the defaults work well for typical scenarios.
- Adding configurability introduces decision burden on users ("How many retries should I set?").
- The strategy can be exposed as CLI/environment parameters in a future release if operators request it.

## Interaction with Lock

The lock acquired by `read()` is held during the entire retry loop, including the sleep intervals. This means:

- A caller can call `close()` while `read()` is sleeping, but `close()` will block until the sleep completes.
- If you need to shut down the camera promptly, stop calling `read()` before calling `close()` (e.g., set a flag in the pipeline loop).

This is acceptable because the lock is scoped to a single camera instance, not a global resource.

## Consequences

- Camera transients are masked transparently; the pipeline sees only successful frames or an `OperationError` after ~5 s of retry.
- Users experience ~1–5 second latency when a camera fails, which is acceptable for a demo tool.
- The same strategy applies to both `LocalCamera` (USB cameras) and `RtspCamera`; RTSP reconnect logic is automatic via retry.
- If MVP users report issues with this strategy (e.g., retries are too aggressive or too lenient), the constants can be tweaked without changing the architecture.

## Superseded By / Supersedes

N/A
