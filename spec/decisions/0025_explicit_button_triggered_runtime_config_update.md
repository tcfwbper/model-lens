# ADR 0025: RuntimeConfig Updates Triggered by Explicit Button Click; Single PUT per Submission

**Date:** 2026-04-02
**Status:** Accepted

## Context

The application exposes mutable runtime configuration through two API endpoints:

- `PUT /config/camera` — updates `CameraConfig`, which triggers `CameraCapture` to be torn
  down and re-initialised with the new source parameters.
- `PUT /config/labels` — updates `target_labels` inside the running pipeline.

Beyond these two, any other future runtime-configurable fields (e.g. `confidence_threshold`)
would similarly require partial or full re-initialisation of backend modules
(`InferenceEngine`, `DetectionPipeline`, etc.) upon change.

Each PUT request that modifies `RuntimeConfig` causes at least one backend module to be
re-initialised. If the frontend propagates changes dynamically (e.g. on every keystroke,
slider move, or dropdown selection), the backend would be hammered with rapid successive
re-initialisations. This is expensive: re-opening a camera device, reloading a model, or
restarting the detection loop all carry non-trivial overhead and can disrupt the live stream.

## Decision

1. **All runtime configuration updates are batched behind an explicit user action** — a
   dedicated "Update" button per configuration section. No PUT request is issued in response
   to individual field changes (keystrokes, dropdown selection, slider movement, etc.).

2. **Each button click sends exactly one PUT request** containing the full current local
   state of that configuration section. There is no incremental or partial update protocol.

3. **The UI accumulates local (uncommitted) state** in component-level state variables and
   tracks a `dirty` flag that becomes `true` whenever local state diverges from the last
   successfully committed server state. The Update button is disabled while `dirty` is
   `false`.

4. **After a successful PUT**, the component resets `dirty` to `false` and resyncs its local
   state from the response (or from the parent-propagated updated prop). On error, local
   state is preserved so the user can retry without re-entering values.

5. This rule applies to all current and future runtime-configurable sections: camera config,
   target labels, and any additional fields added later.

## Rationale

- **Backend re-initialisation cost** — each PUT to `/config/camera` or `/config/labels`
  causes one or more backend modules to be torn down and re-created. Rapid successive updates
  (e.g. one per keystroke) would chain expensive re-initialisations and degrade stream
  continuity.
- **Predictable state transitions** — a single atomic submission per user intent avoids
  partially-applied configurations where, for example, `source_type` is updated but
  `device_index` has not yet been sent.
- **Consistency with existing component design** — `CameraConfig.tsx` and `TargetLabels.tsx`
  already follow this pattern (`dirty` flag, disabled button, "Updating..." loading state).
  This ADR formalises the principle across all runtime config surfaces.
- **Simpler error handling** — with one PUT per submission, error feedback maps directly to
  a single user action. Dynamic updates would require correlating errors to intermediate
  states.

## Alternatives Considered

- **Dynamic updates on each field change (onChange PUT)** — rejected; triggers repeated
  backend re-initialisations per user interaction, increasing system load and disrupting the
  live stream.
- **Debounced dynamic updates** — rejected; reduces frequency but does not eliminate
  intermediate re-initialisations, and complicates error-state reasoning. The user intent is
  still better captured by an explicit confirmation action.
- **Single global "Apply All" button** — rejected for MVP; grouping unrelated config sections
  (camera and labels) into one submission couples independent concerns and makes partial
  updates harder to reason about.

## Consequences

- Every runtime-configurable UI section must include a dedicated Update button.
- The `dirty` flag pattern (local state vs. last committed state) is mandatory for all
  runtime config components.
- Backend re-initialisation is bounded to at most one occurrence per user-initiated
  submission, regardless of how many field edits preceded it.
- Future runtime config fields must follow the same explicit-submit pattern; dynamic
  propagation is not permitted without superseding this ADR.
