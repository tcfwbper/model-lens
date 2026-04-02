# ADR 0023: Model and Label Map from Model Registry; YOLOInferenceEngine as Sole Backend

**Date:** 2026-04-02
**Status:** Accepted

## Context

ADR 0002 decided to ship a single bundled model file loaded once at startup. ADR 0012 defined
a file-path resolution strategy: `TorchInferenceEngine.__init__()` accepted `model_path` and
`labels_path` as either an absolute filesystem path or an empty string (falling back to a
package-bundled resource via `importlib.resources`).

Two changes invalidate these decisions:

1. The model and label map are no longer sourced from external files or package-bundled data.
   Instead, the engine obtains them through an interface that pulls configuration from a
   **model registry**.
2. The sole concrete backend class is `YOLOInferenceEngine`, not `TorchInferenceEngine`. The
   label map is derived directly from the loaded YOLO model's `.names` attribute; no separate
   label map file is parsed.

## Decision

1. `YOLOInferenceEngine` is the only concrete `InferenceEngine` subclass for MVP. Its
   constructor accepts a model identifier (e.g., a path or registry key) and a confidence
   threshold. There is no `TorchInferenceEngine`.
2. The model artefact and label map are retrieved through the model registry interface, not
   from an explicit filesystem path or `importlib.resources` bundled data. The engine calls
   the registry at construction time and fails fast with `ConfigurationError` if the requested
   model cannot be resolved.
3. The label map is derived from the YOLO model's `.names` attribute (a `dict[int, str]`)
   after the model is loaded. No separate label-map file path is accepted or parsed.
4. `ENGINE_REGISTRY` remains a module-level `dict[str, type[InferenceEngine]]` and maps the
   string `"yolo"` to `YOLOInferenceEngine`. Future backends are added by inserting a new
   entry; no other component changes.

## Rationale

- **Registry decoupling** — sourcing models from a registry separates model lifecycle
  management from the engine implementation. The engine need not know where files are stored
  or how the package was installed.
- **Label map co-location** — YOLO models carry their own class names in `.names`. Parsing a
  separate file introduces an additional source of truth and the risk of misalignment between
  model and labels (the problem ADR 0010 addressed). Deriving labels from the model eliminates
  this class of error entirely.
- **Naming clarity** — `YOLOInferenceEngine` names the backend precisely. The previous name
  `TorchInferenceEngine` referred to the underlying framework (PyTorch) rather than the model
  family (YOLO), making it less descriptive and incorrect if YOLO is later run on a non-Torch
  runtime.
- **Fail fast at construction** — registry resolution and model loading still happen in
  `__init__()`, not lazily. `ConfigurationError` is raised immediately if the registry cannot
  satisfy the request.

## Alternatives Considered

- **Keep file-path resolution (ADR 0012)** — rejected; the registry interface renders explicit
  file paths and `importlib.resources` fallback unnecessary and inconsistent with the new
  model sourcing approach.
- **Keep bundled model (ADR 0002)** — rejected; the registry approach removes the coupling
  between the Python package and the model binary, enabling model updates without a full
  package re-release.
- **Retain `TorchInferenceEngine` name as alias** — rejected; maintaining two names for the
  same class adds confusion with no benefit.
- **Separate label map file alongside registry** — rejected; YOLO `.names` is authoritative
  and already available after model load. A separate file reintroduces the alignment risk.

## Consequences

- `YOLOInferenceEngine.__init__()` no longer accepts `model_path` or `labels_path` file-path
  arguments. It accepts a model registry key/identifier and a confidence threshold.
- `TorchInferenceEngine` does not exist; any references to it in older specs or tests must be
  updated.
- The label map is always consistent with the loaded model; no label-map file mismatch is
  possible at the engine level.
- Adding a new backend (e.g., ONNX) still requires only: (1) a new subclass, (2) importing it
  at startup, (3) one new `ENGINE_REGISTRY` entry. Pipeline and API are unaffected.
- ADR 0010 (label map empty-line handling) is rendered moot for `YOLOInferenceEngine` because
  the label map file is no longer parsed; `.names` is a structured dict.

## Superseded By / Supersedes

- **Supersedes:** ADR 0002 (single bundled model), ADR 0012 (package data resource resolution)
