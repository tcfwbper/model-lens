# Architecture for ModelLens

## Purpose

ModelLens is a lightweight AI demo tool that:

1. Streams frames from a camera source (local webcam or RTSP/IP camera).
2. Runs a bundled object-detection model against each frame to determine whether specific objects are present.
3. Exposes a browser-based web UI for configuring the camera source and the target object labels — without restarting the server.

---

## System Overview

```
┌──────────────────────────────────────────────────────────┐
│                       Browser (UI)                       │
│  ┌──────────────┐   ┌──────────────────────────────────┐ │
│  │ Config Page  │   │  Live Stream + Detection Overlay │ │
│  └──────┬───────┘   └──────────────────┬───────────────┘ │
└─────────┼──────────────────────────────┼─────────────────┘
          │ REST (CRUD config)           │ SSE stream
┌─────────▼──────────────────────────────▼─────────────────┐
│                    FastAPI Web Server                    │
│  ┌─────────────┐  ┌───────────────┐  ┌─────────────────┐ │
│  │  Config API │  │  Stream API   │  │  Static Assets  │ │
│  │ (in-memory) │  │               │  │  (bundled)      │ │
│  └──────┬──────┘  └──────┬────────┘  └─────────────────┘ │
│         │                │                               │
│  ┌──────▼────────────────▼────────────────────────────┐  │
│  │               Detection Pipeline                   │  │
│  │  ┌───────────────┐      ┌──────────────────────┐   │  │
│  │  │ CameraCapture │─────►│  InferenceEngine     │   │  │
│  │  │  (OpenCV)     │frame │  (bundled model)     │   │  │
│  │  └───────────────┘      └──────────────────────┘   │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

---

## Components

### Web Server
Bootstraps the application and owns the lifecycle of the Detection Pipeline. Serves bundled static assets and mounts the Config API and Stream API.

### Config API
Accepts runtime configuration changes (camera source, target labels). State is held **in memory only**; there is no persistence between restarts. Changes take effect on the next frame loop iteration without restarting the server.

### Stream API
Pushes a continuous stream of annotated frames and detection results to the browser over SSE. Also provides a single-frame snapshot for debugging.

### Detection Pipeline
Runs the frame loop in a background task: reads frames from CameraCapture, passes them to InferenceEngine, and publishes annotated results to the in-memory queue consumed by Stream API. Reacts to config changes between frames without restarting.

### CameraCapture
Abstracts over local (webcam) and RTSP camera sources. Recreated when the camera configuration changes.

### InferenceEngine
Loads a bundled model file and its corresponding label map once at startup, then produces detection results for each frame. Raw model output indices are translated to human-readable label strings using the label map before being returned as `DetectionResult` objects. The model, label map, and confidence threshold are fixed at startup and cannot be changed at runtime. Designed as an abstract base to allow future backend alternatives without touching other components.

---

## Entities

### CameraConfig
Identifies the camera source: either a local device index or an RTSP URL.

### RuntimeConfig
The full runtime state: camera configuration, target labels, and confidence threshold.

### DetectionResult
A single detected object: label, confidence score, bounding box, and whether the label matched the target list.

### Frame
A raw image buffer as captured from the camera, passed between CameraCapture and InferenceEngine.

---

## Extensibility Notes

| Capability | Addition point |
|---|---|
| Persist config across restarts | Add a Config Store behind the existing Config API |
| Pull assets from external storage. Either from local path or S3 | Add an asset-sync step in the server startup hook |

---

## Constraints

- Python 3.11+.
- The server process must be able to reach the camera hardware or RTSP URL at startup.
- A single concurrent stream consumer is the expected load (demo tool, not production serving).
- No authentication or multi-user session management is in scope.
- Model path and confidence threshold are configured via environment variables with package-data defaults; no user-facing model management is provided.
