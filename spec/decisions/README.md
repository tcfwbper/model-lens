# Architecture Decision Records (ADR)

## What is an ADR?

An Architecture Decision Record captures a significant design choice: what was decided,
why it was chosen, and what alternatives were rejected.

**AI agents must read relevant ADRs before proposing changes** to any area covered by a decision.
An ADR is not a suggestion — it is a binding constraint until explicitly superseded.

---

## ADR Index

| ID | Title | Status |
|---|---|---|
| [0001](0001_initial_toolchain.md) | Initial Python toolchain selection | Accepted |
| [0002](0002_single_bundled_inference_engine.md) | Single bundled InferenceEngine | Accepted |
| [0003](0003_in_memory_config_only.md) | In-memory config only | Accepted |
| [0004](0004_bundled_static_assets.md) | Bundled static assets | Accepted |
| [0005](0005_sse_over_websocket.md) | SSE over WebSocket for the live stream | Accepted |
| [0006](0006_config_applied_in_loop.md) | Config changes applied in-loop | Accepted |
| [0007](0007_opencv_for_camera_sources.md) | OpenCV for both camera source types | Accepted |
| [0008](0008_concurrency_and_thread_safety.md) | Concurrency and thread safety strategy | Accepted |
| [0009](0009_frame_data_ownership_and_copy_strategy.md) | Frame data ownership and copy strategy | Accepted |
| [0010](0010_label_map_empty_line_handling.md) | Label map empty line handling | Accepted |
| [0011](0011_retry_and_recovery_mechanism_design.md) | Retry and recovery mechanism design | Accepted |
| [0012](0012_package_data_resource_resolution.md) | Package data resource resolution and fallback | Accepted |
| [0013](0013_bounded_queue_drop_oldest_strategy.md) | Bounded result queue with drop-oldest eviction | Accepted |
| [0014](0014_30fps_output_rate_cap.md) | 30 FPS output rate cap via sleep-based pacing | Accepted |
| [0015](0015_jpeg_encoding_in_pipeline.md) | JPEG encoding inside the Detection Pipeline | Accepted |
| [0016](0016_fatal_parse_error_exit.md) | ParseError from inference treated as fatal (sys.exit) | Accepted |
| [0017](0017_fastapi_lifespan_over_on_event.md) | FastAPI lifespan context manager over on_event hooks | Accepted |
| [0018](0018_pipeline_dependency_injection_via_app_state.md) | DetectionPipeline dependency injection via app.state and Depends | Accepted |
| [0019](0019_sse_keepalive_and_idle_timeout.md) | SSE keepalive comments and 30-second server-side idle timeout | Accepted |
| [0020](0020_pydantic_discriminated_union_for_camera_config.md) | Pydantic discriminated union for camera configuration | Accepted |

---

## ADR Status Definitions

| Status | Meaning |
|---|---|
| `Accepted` | Active decision; must be followed |
| `Superseded` | Replaced by a newer ADR (link to new one) |
| `Deprecated` | No longer relevant; do not follow |
| `Proposed` | Under discussion; not yet binding |

---

## How to Add a New ADR

1. Create `spec/decisions/<next_number>_<short_title>.md` using the template below.
2. Add a row to the index table above.
3. Commit with message: `spec(decisions): add ADR <number> - <short title>`

## ADR Template

```markdown
# ADR <number>: <Title>

**Date:** YYYY-MM-DD
**Status:** Proposed | Accepted | Superseded | Deprecated

## Context
<What problem or question prompted this decision?>

## Decision
<What was decided?>

## Rationale
<Why was this option chosen over alternatives?>

## Alternatives Considered
- **Option A:** ... — rejected because ...
- **Option B:** ... — rejected because ...

## Consequences
<What becomes easier or harder as a result of this decision?>

## Superseded By / Supersedes
N/A
```
