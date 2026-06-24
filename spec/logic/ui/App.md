# App

## Overview

Root React component for the ModelLens UI. Orchestrates page layout, owns the SSE active/inactive toggle state, and distributes runtime configuration data and mutation callbacks to child components. Does not fetch data itself — delegates all API communication to the `useConfig` hook.

## Boundaries

- Owns: page-level layout structure, SSE toggle state (`sseActive`), wiring of callbacks between hooks and child components.
- Owns: rendering of the Start/Stop Stream buttons in the right column.
- Delegates: all API communication (fetch config, update camera, update labels) to `useConfig` hook.
- Delegates: SSE connection lifecycle to `useStream` hook (via `StreamViewer`).
- Delegates: camera form UI to `CameraConfig` component.
- Delegates: label selection UI to `TargetLabels` component.
- Delegates: frame rendering to `StreamViewer` component.
- Must not: call `fetch()` directly.
- Must not: manage EventSource connections.
- Must not: contain form validation logic.

## Dependencies

| Collaborator | Role | Allowed Interaction | Forbidden Interaction |
|---|---|---|---|
| `useConfig` hook | Config state & mutations | Call hook; read `runtimeConfig`, `validLabels`; invoke `updateCamera`, `updateLabels` | Must not bypass hook to call API directly |
| `Header` component | Title bar rendering | Render as child | — |
| `CameraConfig` component | Camera form | Pass `camera` prop and `onUpdate` callback | — |
| `TargetLabels` component | Label multi-select | Pass `validLabels`, `activeLabels`, `onUpdate` | — |
| `StreamViewer` component | Frame display | Pass `sseActive`, `onToggleSSE`, `confidenceThreshold` | — |

Construction constraint: Functional component using hooks. No class component.

## Behavior

1. Calls `useConfig()` on mount to obtain `runtimeConfig`, `validLabels`, `updateCamera`, and `updateLabels`.
2. Maintains a local `sseActive` boolean state, initially `false`.
3. Derives `camera` from `runtimeConfig?.camera ?? null`.
4. Derives `activeLabels` from `runtimeConfig?.target_labels ?? []`.
5. Derives `confidenceThreshold` from `runtimeConfig?.confidence_threshold ?? null`.
6. Renders `Header` at the top spanning full width.
7. Renders `CameraConfig` below the header spanning full width, passing `camera` and a handler that calls `updateCamera`.
8. Below the camera config, renders a two-column layout:
   - Left column (flex: 2): `StreamViewer` with `sseActive`, `onToggleSSE`, and `confidenceThreshold`.
   - Right column (flex: 1): `TargetLabels` followed by Start/Stop Stream buttons.
9. Start Stream button: disabled when `sseActive` is `true`; on click sets `sseActive` to `true`. Uses Primary color when enabled, Primary Disabled color when disabled.
10. Stop Stream button: disabled when `sseActive` is `false`; on click sets `sseActive` to `false`. Uses neutral grey when enabled, lighter grey when disabled.

## Inputs

| Field | Type | Source | Description |
|---|---|---|---|
| (none — root component) | — | — | No props received |

## Outputs

Renders the full application UI to the DOM.

## Invariants

- Must not start the SSE stream on page load; `sseActive` defaults to `false`.
- Start and Stop buttons are mutually exclusive in enabled state.
- All API error handling is performed inside `useConfig`; App does not catch or display errors itself.

## Edge Cases

- Condition: `runtimeConfig` is `null` (initial load failed or still loading).
  Expected: `camera` is `null`, `activeLabels` is `[]`, `confidenceThreshold` is `null`. Components render with empty/default states.

- Condition: User clicks Start Stream while config is still loading.
  Expected: `sseActive` becomes `true`; `StreamViewer` activates SSE connection regardless of config load state.

## Related

- [useConfig hook](./hooks/useConfig.md): provides all config state and mutations.
- [Header](./components/Header.md): title bar component.
- [CameraConfig](./components/CameraConfig.md): camera configuration form.
- [TargetLabels](./components/TargetLabels.md): label selection dropdown.
- [StreamViewer](./components/StreamViewer.md): canvas-based frame renderer.
