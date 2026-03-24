# ADR 0019: SSE Keepalive Comments and 30-Second Server-Side Idle Timeout

**Date:** 2026-03-24
**Status:** Accepted

## Context

The `GET /stream` endpoint is a long-lived Server-Sent Events (SSE) connection. Two operational
concerns arise for any persistent HTTP streaming connection:

1. **Proxy keepalive** — HTTP proxies and load balancers typically close idle connections after
   a configurable inactivity timeout (e.g., AWS ALB defaults to 60 seconds, nginx defaults to
   75 seconds). If the pipeline produces no frame for several seconds (e.g., camera reconnect
   in progress), the proxy will silently close the connection, causing the browser to observe
   a dead stream with no error.

2. **Server resource release** — if the browser tab is closed or the client disconnects while
   the server is idle (no frames produced), the server must eventually notice and release the
   response coroutine. Holding an open response coroutine for a pipeline that has stopped
   producing frames wastes server resources indefinitely.

## Decision

### Keepalive comments

When the pipeline result queue is empty (the server waits up to **1 second** for a frame via a
blocking get with timeout), and no frame is available, the server writes an SSE comment line:

```
: keepalive\n\n
```

This is sent at most **once per second** of idle time. SSE comment lines are part of the SSE
specification and are silently ignored by browser `EventSource` implementations.

### Server-side idle timeout

If no `PipelineResult` has been produced for **30 consecutive seconds**, the server closes the
SSE response stream cleanly (no error event). The client's built-in `EventSource` auto-reconnect
behaviour re-establishes the connection. The 30-second timer resets each time a frame is
successfully read from the queue; it does not reset on keepalive writes.

## Rationale

### Why SSE comments for keepalive?

SSE comments (`lines starting with :`) are defined in the SSE specification (WHATWG) and
explicitly reserved for keepalive use by servers. Browsers ignore them without triggering an
event, which means they do not pollute the application event stream. They do keep the TCP
connection alive and reset any proxy idle-close timer, which is the only goal.

### Why 1-second probe interval?

- **Under the proxy timeout** — a 1-second probe interval keeps the connection alive against
  any proxy with an idle timeout ≥ 2 seconds, which covers all common reverse proxies and CDNs.
- **Low overhead** — writing a short comment line once per second has negligible CPU and
  bandwidth impact.
- **Matches queue read granularity** — the stream loop already calls `queue.get(timeout=1.0)`
  as its natural polling interval; the keepalive write is a zero-cost side effect of each
  timed-out get, requiring no separate timer or thread.

### Why 30 seconds for the server-side idle timeout?

- **Long enough for camera reconnect** — the camera retry/recovery mechanism (ADR 0011) uses
  exponential back-off with a maximum interval of several seconds. 30 seconds gives the
  pipeline enough time to recover from a camera dropout without the browser reconnecting.
- **Short enough to release resources** — if the pipeline is genuinely stuck or the process is
  half-dead, holding an SSE response open indefinitely wastes a goroutine/coroutine and a file
  descriptor. 30 seconds is a reasonable upper bound before concluding the server is not
  recovering promptly.
- **Consistent with industry practice** — 30 seconds is a common server-side SSE timeout used
  by platforms such as GitHub's event streams, allowing clients to reconnect cleanly.

### Why close cleanly (no error event)?

The browser's `EventSource` object reconnects automatically after the connection is closed by
the server. Sending an error event before closing would trigger the `onerror` handler in
application code, potentially displaying a user-visible error for what is a routine reconnect.
A clean close produces a quiet reconnect with no application-level error.

## Alternatives Considered

- **No keepalive** — rejected because proxies with short idle timeouts (< 30 s) would silently
  drop the connection, causing a dead stream with no browser-visible error.
- **Heartbeat data events (empty `data:` lines)** — rejected because `data:` lines dispatch
  events to JavaScript `addEventListener` handlers, polluting the application stream with
  no-op events that handlers must explicitly ignore.
- **Separate keepalive timer/thread** — rejected; the natural 1-second `queue.get(timeout=1.0)`
  loop iteration already provides the timing without additional concurrency.
- **No server-side idle timeout (stream open forever)** — rejected because it holds server
  resources (coroutine, file descriptor, queue subscription) indefinitely if the pipeline stops
  producing frames.
- **Shorter idle timeout (e.g., 10 seconds)** — rejected; 10 seconds may cut the stream during
  a camera reconnect that the pipeline is actively recovering from (ADR 0011), causing
  unnecessary browser reconnects and visible stream interruptions.

## Consequences

- The SSE stream survives transient camera dropouts without the browser reconnecting.
- Proxy idle-close timers are neutralised by the 1-second keepalive comment.
- Server resources are released at most 30 seconds after the pipeline stops producing frames.
- The stream produces no keepalive traffic when frames are arriving normally (e.g., 30 FPS).
- Client-side SSE code should not assume any event type for comment lines; they are invisible
  to `EventSource`.

## Superseded By / Supersedes
N/A
