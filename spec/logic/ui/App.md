# App

## Overview

Root React component for the ModelLens UI. Orchestrates page layout, owns the SSE active/inactive toggle state, and distributes runtime configuration data and mutation callbacks to child components. Does not fetch data itself — delegates all API communication to the `useConfig` hook.

## Boundaries

- Owns: page-level layout structure, SSE toggle state (`sseActive`), wiring of callbacks between hooks and child components.
- Owns: rendering of the Start/Stop Stream buttons in a button row within the right column.
- Owns: page-level visual styling (background color, min-height, font-family).
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
| Design Tokens | Visual constants | Consume via CSS custom properties | Must not hardcode values that differ from token definitions |

Construction constraint: Functional component using hooks. No class component.

## Behavior

1. Calls `useConfig()` on mount to obtain `runtimeConfig`, `validLabels`, `updateCamera`, and `updateLabels`.
2. Maintains a local `sseActive` boolean state, initially `false`.
3. Derives `camera` from `runtimeConfig?.camera ?? null`.
4. Derives `activeLabels` from `runtimeConfig?.target_labels ?? []`.
5. Derives `confidenceThreshold` from `runtimeConfig?.confidence_threshold ?? null`.
6. Renders `Header` at the top spanning full width.
7. Renders a content area below the header with padding `var(--spacing-lg) var(--spacing-xl)` (`16px 24px`).
8. Within the content area, renders `CameraConfig` spanning full width, passing `camera` and a handler that calls `updateCamera`.
9. Below the camera config (margin-top `var(--spacing-lg)` / `16px`), renders a two-column flex layout with gap `var(--spacing-lg)` (`16px`):
   - Left column (flex: 2): `StreamViewer` with `sseActive`, `onToggleSSE`, and `confidenceThreshold`.
   - Right column (flex: 1, flexDirection: column, gap: `var(--spacing-lg)` / `16px`): `TargetLabels` followed by a button row.
10. Button row: a flex container with gap `var(--spacing-sm)` (`8px`) containing Start and Stop buttons side by side.
11. Start Stream button:
    - flex: 1.
    - padding: `var(--spacing-sm) var(--spacing-lg)` (`8px 16px`).
    - backgroundColor: `var(--color-primary-disabled)` (`#A8C4DC`) when disabled; `var(--color-primary)` (`#5B8CB8`) when enabled.
    - color: `var(--color-white)` (`#FFFFFF`).
    - border: none.
    - borderRadius: `var(--radius-sm)` (`4px`).
    - cursor: `default` when disabled; `pointer` when enabled.
    - Disabled when `sseActive` is `true`; on click sets `sseActive` to `true`.
12. Stop Stream button:
    - flex: 1.
    - padding: `var(--spacing-sm) var(--spacing-lg)` (`8px 16px`).
    - backgroundColor: `var(--color-secondary-disabled)` (`#D4DAE0`) when disabled; `var(--color-secondary)` (`#6B7B8D`) when enabled.
    - color: `var(--color-white)` (`#FFFFFF`).
    - border: none.
    - borderRadius: `var(--radius-sm)` (`4px`).
    - cursor: `default` when disabled; `pointer` when enabled.
    - Disabled when `sseActive` is `false`; on click sets `sseActive` to `false`.

### Page-Level Styling (root div)

- minHeight: `100vh`.
- backgroundColor: `var(--color-bg-page)` (`#F5F6F8`).
- fontFamily: `var(--font-family)` (`system-ui, -apple-system, sans-serif`).

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
- All visual constants must come from design tokens.

## Edge Cases

- Condition: `runtimeConfig` is `null` (initial load failed or still loading).
  Expected: `camera` is `null`, `activeLabels` is `[]`, `confidenceThreshold` is `null`. Components render with empty/default states.

- Condition: User clicks Start Stream while config is still loading.
  Expected: `sseActive` becomes `true`; `StreamViewer` activates SSE connection regardless of config load state.

## Related

- [Design Tokens](./styles/design-tokens.md): defines all visual constants.
- [useConfig hook](./hooks/useConfig.md): provides all config state and mutations.
- [Header](./components/Header.md): title bar component.
- [CameraConfig](./components/CameraConfig.md): camera configuration form.
- [TargetLabels](./components/TargetLabels.md): label selection dropdown.
- [StreamViewer](./components/StreamViewer.md): canvas-based frame renderer.
