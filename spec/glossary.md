# Glossary for ModelLens

## Core Principle
This glossary is the **single source of truth for domain terminology**.
All contributors and AI agents must use these exact terms in code (identifiers, docstrings) and spec files.
When a term here conflicts with general usage, this definition wins.

---

## How to Use This File

- Before naming any class, function, variable, or file, check this glossary first.
- If a concept you need is not listed, **add it here before using it** — do not invent ad-hoc names.
- Entries are listed alphabetically within each section.

---

## Domain Terms

| Term Name | Definition | Code Identifier | Not to be Confused With |
| :--- | :--- | :--- | :--- |
| **Model Asset** | The static, trained weights and metadata files stored in a registry (e.g., S3 or HuggingFace). | `ModelAsset` | **Checkpoint**: Intermediate training states that aren't yet optimized for production. |
| **Inference Engine** | The specific backend software responsible for loading weights and executing tensor operations. | `InferenceEngine` | **Framework**: The library used for training (e.g., PyTorch) vs. the runtime (e.g., vLLM, TensorRT). |
| **Endpoint** | A logical, stable URL or entry point that users call to receive predictions. | `InferenceEndpoint` | **Worker/Pod**: The individual computing units that might change, while the Endpoint stays constant. |
| **Model Replica** | An active, running instance of a model loaded into memory (GPU/CPU) ready to serve requests. | `ModelReplica` | **Node**: The physical or virtual machine; one Node can host multiple Model Replicas. |
| **Frame** | A single decoded image captured from a camera source, represented as a NumPy array (HxWxC, BGR). | `Frame` | **Image**: A static file loaded from disk. A Frame is always live-captured. |
| **Detection Result** | The output of one inference pass for a single object hypothesis: label, confidence score, bounding box, and whether the label is in the configured target list. | `DetectionResult` | **Prediction**: A raw model output before filtering/thresholding. |
| **Label Map** | A bundled plain-text file (one label per line) that maps a model's raw integer output index to a human-readable class name string. Loaded once at startup together with the model file. | `label_map` | **Class Names**: An informal list not tied to a specific model file. A Label Map is always paired with a specific model. |
| **Camera Capture** | The abstraction that owns an open connection to a camera source and vends `Frame` objects on demand. | `CameraCapture` | **Video Stream**: The underlying protocol-level byte stream. `CameraCapture` is the decoded, frame-level interface. |
| **Detection Pipeline** | The background loop that repeatedly reads a `Frame` from `CameraCapture`, runs `InferenceEngine.detect()`, and publishes the annotated result to the SSE queue. | `pipeline` (module) | **Worker**: A pipeline is not a general worker; it is specifically the frame→inference→publish loop. |
| **Engine Registry** | A module-level dict mapping engine name strings to `InferenceEngine` subclasses, enabling runtime swapping without code changes. | `ENGINE_REGISTRY` | **Plugin System**: The registry is intentionally minimal — no dynamic loading; engines must be imported at startup. |

---

## Abbreviations and Acronyms

| Abbreviation | Full Form | Notes |
|---|---|---|

---

## Technical Terms (Project-Specific Usage)

| Term Name | Project-Specific Usage | Standard Meaning | Reason for Distinction |
| :--- | :--- | :--- | :--- |
| **Worker** | Strictly mapped to a **single K8s Pod** running one model instance. | Any background process or computing node. | To simplify GPU resource isolation and scheduling. |
| **Request** | A specific **Unary API call** containing a prompt and inference parameters. | Any general HTTP or network communication. | To distinguish between network-level pings and business-level inference tasks. |
| **Stream** | A **Server-Sent Events (SSE)** protocol used for real-time token generation. | General data streaming (e.g., video, binary). | Ensures consistent handling of "typewriter-style" UI updates. |
| **Namespace** | A **multi-tenancy boundary** used for resource quotas and billing. | Language-level scoping or native K8s namespaces. | Used to link application-level logic with underlying infrastructure RBAC. |

---

## Out-of-Scope Terms

Terms that are explicitly **not** used in this codebase and what to use instead:

| Avoid | Use instead | Reason |
|---|---|---|
| Job | Mission | [Inference Context Only] To follow team conventions. |
| Task | Mission | [Inference Context Only] To follow team conventions. |
