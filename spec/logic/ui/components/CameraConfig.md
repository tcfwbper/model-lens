# CameraConfig

## Overview

Form component that displays the current camera configuration and allows the user to modify it. Changes are only sent to the backend when the user explicitly clicks the "Update Camera" button. Does not call the API directly — invokes a parent-provided callback.

## Boundaries

- Owns: local form state (selected type, device index text, RTSP URL text, updating flag); dirty detection logic; form submission orchestration; form-level styling.
- Delegates: actual API call to the parent via `onUpdate` callback.
- Delegates: error display to the parent (errors surface via `alert()` in `useConfig`).
- Must not: call `fetch()` directly.
- Must not: modify parent state other than through the `onUpdate` callback.

## Dependencies

| Collaborator | Role | Allowed Interaction | Forbidden Interaction |
|---|---|---|---|
| Parent (`App`) | Provides `camera` prop and `onUpdate` callback | Receives props; calls `onUpdate` | Must not access parent state directly |
| Design Tokens | Visual constants | Consume via CSS custom properties | Must not hardcode values that differ from token definitions |

Construction constraint: Functional React component. Uses `useState`, `useEffect` from React.

## Behavior

### Props

| Prop | Type | Description |
|---|---|---|
| `camera` | `CameraConfigData \| null` | Current camera config from server. `null` if initial load failed. |
| `onUpdate` | `(camera: CameraConfigData) => Promise<void>` | Callback that sends the update. Resolves on success, rejects on error. |

### Internal State

| State | Type | Initial Value |
|---|---|---|
| `selectedType` | `"local" \| "rtsp"` | `camera?.source_type ?? "local"` |
| `deviceIndex` | `string` | `camera?.source_type === "local" ? String(camera.device_index) : ""` |
| `rtspUrl` | `string` | `camera?.source_type === "rtsp" ? camera.rtsp_url : ""` |
| `updating` | `boolean` | `false` |

### Sync from Props

When `camera` prop changes (via `useEffect` on `camera`):
1. Sets `selectedType` to `camera.source_type`.
2. If local: sets `deviceIndex` to string of `camera.device_index`, clears `rtspUrl`.
3. If RTSP: sets `rtspUrl` to `camera.rtsp_url`, clears `deviceIndex`.

### Dirty Detection

The component is "dirty" (update button enabled) when:
- `camera` is `null` AND (selectedType is "local" with non-empty `deviceIndex`, OR selectedType is "rtsp" with non-empty `rtspUrl`).
- `selectedType` differs from `camera.source_type`.
- selectedType is "local" AND `parseInt(deviceIndex)` differs from `camera.device_index` (treats non-numeric `deviceIndex` as dirty if non-empty).
- selectedType is "rtsp" AND `rtspUrl` differs from `camera.rtsp_url`.

### Type Change

When the source type dropdown changes:
1. Updates `selectedType`.
2. Clears both `deviceIndex` and `rtspUrl` (resets input fields).

### Submit

1. Sets `updating` to `true`.
2. Calls `onUpdate` with the assembled `CameraConfigData`:
   - Local: `{ source_type: "local", device_index: parseInt(deviceIndex, 10) }`
   - RTSP: `{ source_type: "rtsp", rtsp_url: rtspUrl }`
3. On success: parent updates `camera` prop, which triggers resync.
4. On error: caught silently (error handled by parent via alert). Internal state is not reset.
5. In all cases (`finally`): sets `updating` to `false`.

### Rendering & Styling

1. **Container div**:
   - backgroundColor: `var(--color-bg-surface)` (`#FFFFFF`).
   - border: `1px solid var(--color-border)` (`1px solid #D4DAE0`).
   - borderRadius: `var(--radius-md)` (`8px`).
   - padding: `var(--spacing-lg)` (`16px`).
   - display: `flex`.
   - alignItems: `center`.
   - gap: `var(--spacing-md)` (`12px`).

2. **Source type `<select>`**:
   - Options: "Local Camera" (value "local"), "RTSP" (value "rtsp").
   - padding: `var(--spacing-sm) var(--spacing-md)` (`8px 12px`).
   - border: `1px solid var(--color-border)` (`1px solid #D4DAE0`).
   - borderRadius: `var(--radius-sm)` (`4px`).
   - color: `var(--color-text-primary)` (`#2C3E50`).

3. **Device index input** (when selectedType is "local"):
   - type: `number`, min: `0`.
   - padding: `var(--spacing-sm) var(--spacing-md)` (`8px 12px`).
   - border: `1px solid var(--color-border)` (`1px solid #D4DAE0`).
   - borderRadius: `var(--radius-sm)` (`4px`).
   - color: `var(--color-text-primary)` (`#2C3E50`).
   - width: `120px`.

4. **RTSP URL input** (when selectedType is "rtsp"):
   - type: `text`, placeholder: `"rtsp://..."`.
   - padding: `var(--spacing-sm) var(--spacing-md)` (`8px 12px`).
   - border: `1px solid var(--color-border)` (`1px solid #D4DAE0`).
   - borderRadius: `var(--radius-sm)` (`4px`).
   - color: `var(--color-text-primary)` (`#2C3E50`).
   - flex: `1` (fills remaining space).

5. **"Update Camera" button**:
   - padding: `var(--spacing-sm) var(--spacing-lg)` (`8px 16px`).
   - backgroundColor: `var(--color-primary)` (`#5B8CB8`) when enabled; `var(--color-primary-disabled)` (`#A8C4DC`) when disabled.
   - color: `var(--color-white)` (`#FFFFFF`).
   - border: `none`.
   - borderRadius: `var(--radius-sm)` (`4px`).
   - cursor: `pointer` when enabled; `default` when disabled.
   - Disabled when not dirty or `updating` is true.
   - Text changes to "Updating..." while in flight.

## Inputs

| Field | Type | Constraints | Required |
|---|---|---|---|
| `camera` | `CameraConfigData \| null` | Discriminated union or null | Yes |
| `onUpdate` | `(camera: CameraConfigData) => Promise<void>` | Must return a promise | Yes |

## Outputs

JSX element representing the camera configuration form row.

## Invariants

- Internal state always resyncs when `camera` prop changes.
- The update button is never enabled when the form is clean (matches current `camera` prop).
- `onUpdate` is never called while `updating` is `true` (button disabled prevents it).
- `parseInt` uses radix 10 for device index conversion.
- All visual constants must come from design tokens.

## Edge Cases

- Condition: `camera` prop is `null` (server unreachable on load).
  Expected: Form renders with defaults (local type, empty device index). Button is disabled until user enters a value.

- Condition: User enters non-numeric text in device index field.
  Expected: `parseInt` returns `NaN`; dirty detection treats non-empty non-numeric input as dirty (button enables). Submission sends `NaN` as `device_index` — server will reject with validation error.

- Condition: `onUpdate` rejects (API error).
  Expected: `updating` returns to `false`. Form fields retain user's input for retry.

## Related

- [Design Tokens](../styles/design-tokens.md): defines all visual constants.
- [App](../App.md): parent that provides props and wires to `useConfig`.
- [useConfig](../hooks/useConfig.md): actual API communication.
