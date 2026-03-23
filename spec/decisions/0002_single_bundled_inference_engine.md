# ADR 0002: Single Bundled InferenceEngine

**Date:** 2026-03-23
**Status:** Accepted

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

## Superseded By / Supersedes
N/A
