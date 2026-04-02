# ADR 0002: Single Bundled InferenceEngine

**Date:** 2026-03-23
**Status:** Superseded

## Context
The system needs to run object detection on each camera frame. There are multiple ways to structure the inference layer: a single hardcoded implementation, a registry of swappable backends, or a cloud-delegated API.

## Decision
Ship exactly one concrete InferenceEngine implementation in MVP. The model file is bundled with the package and loaded once at startup.

## Rationale
MVP scope is a local demo tool; runtime model swapping adds complexity without delivering user value at this stage. Bundling the model eliminates external dependencies at runtime.

## Alternatives Considered
- **Swappable backend registry** — rejected because it requires a model management UI and complicates startup logic; deferred post-MVP.
- **Cloud inference API** — rejected because it introduces network dependency, latency, and cost; not appropriate for a local demo.

## Consequences
- Simpler startup and no runtime model management.
- Model and confidence threshold can only be changed via environment variables before starting the server.
- Adding a second backend in future requires introducing a registry in the InferenceEngine layer without touching the pipeline or API.
- The abstract `InferenceEngine` base class defines an `ENGINE_REGISTRY` dict mapping backend name strings to concrete subclass types. Adding a new backend (e.g., ONNX, TFLite) requires: (1) implementing a new subclass, (2) importing it at startup, (3) adding one entry to `ENGINE_REGISTRY`. No changes to the Detection Pipeline or other components are required.

## Superseded By / Supersedes

- **Superseded By:** [ADR 0023](0023_model_registry_and_yolo_backend.md) — model is retrieved from a model registry; `YOLOInferenceEngine` is the named concrete backend.
