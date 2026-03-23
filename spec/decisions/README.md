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
