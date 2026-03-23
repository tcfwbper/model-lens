# ADR 0007: OpenCV for Both Camera Source Types

**Date:** 2026-03-23
**Status:** Accepted

## Context
The system supports two camera source types: local webcam and RTSP/IP camera. Each could use a different capture library.

## Decision
Both `LocalCamera` and `RtspCamera` use OpenCV (`cv2.VideoCapture`) as the capture backend.

## Rationale
Using a single library for both source types means frame decoding, colour conversion, and scaling code is shared. OpenCV's `VideoCapture` handles both `device_index` (for local) and RTSP URLs transparently, minimising the surface area of the CameraCapture abstraction.

## Alternatives Considered
- **GStreamer directly for RTSP** — rejected because it requires a separate dependency and duplicates frame-handling code that OpenCV already provides for both source types.

## Consequences
- A single OpenCV dependency covers both source types.
- RTSP reconnect logic is isolated to `RtspCamera` and does not affect `LocalCamera`.
- Switching away from OpenCV in future would require updating both camera implementations.

## Superseded By / Supersedes
N/A
