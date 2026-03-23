# ADR 0005: SSE over WebSocket for the Live Stream

**Date:** 2026-03-23
**Status:** Accepted

## Context
The browser needs to receive a continuous stream of annotated frames and detection results from the server. The two primary options are Server-Sent Events (SSE) and WebSockets.

## Decision
Use Server-Sent Events (SSE) for the `/stream` endpoint.

## Rationale
The stream is strictly unidirectional (server → browser). SSE requires no handshake library, works natively over HTTP/1.1 and HTTP/2, and is directly supported by FastAPI's `StreamingResponse`. WebSockets add bidirectional complexity that is not needed here.

## Alternatives Considered
- **WebSocket** — rejected because the communication is one-way; WebSocket's bidirectional capability offers no benefit and adds dependency and protocol complexity.

## Consequences
- Simple server implementation with no additional library for the streaming protocol.
- Browser reconnects automatically on connection drop (built-in SSE behaviour).
- If bidirectional communication is ever required (e.g. user sends frame-level annotations), this decision should be revisited.

## Superseded By / Supersedes
N/A
