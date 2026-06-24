# TargetLabels

## Overview

Multi-select dropdown component for choosing which detection labels to monitor. Provides search filtering, bulk select/clear actions, and an explicit "Update Labels" button. Changes are only sent to the backend when the user clicks the update button.

## Boundaries

- Owns: local selection state (`selected` set); dropdown open/close behavior; search filtering; dirty detection; submission orchestration; component-level styling.
- Delegates: actual API call to the parent via `onUpdate` callback.
- Delegates: error display to the parent (errors surface via `alert()` in `useConfig`).
- Must not: call `fetch()` directly.
- Must not: auto-submit on selection change.

## Dependencies

| Collaborator | Role | Allowed Interaction | Forbidden Interaction |
|---|---|---|---|
| Parent (`App`) | Provides props and `onUpdate` callback | Receives props; calls `onUpdate` | Must not access parent state directly |
| `document` (browser API) | Click-outside detection | `addEventListener("mousedown", ...)`, `removeEventListener(...)` | — |
| Design Tokens | Visual constants | Consume via CSS custom properties | Must not hardcode values that differ from token definitions |

Construction constraint: Functional React component. Uses `useState`, `useEffect`, `useRef` from React.

## Behavior

### Props

| Prop | Type | Description |
|---|---|---|
| `validLabels` | `string[]` | Full list of valid labels from the server |
| `activeLabels` | `string[]` | Currently active target labels from server config |
| `onUpdate` | `(labels: string[]) => Promise<void>` | Callback to send label update. Resolves on success, rejects on error. |

### Internal State

| State | Type | Initial Value |
|---|---|---|
| `selected` | `Set<string>` | `new Set(activeLabels)` |
| `searchTerm` | `string` | `""` |
| `dropdownOpen` | `boolean` | `false` |
| `updating` | `boolean` | `false` |

### Sync from Props

When `activeLabels` prop changes (via `useEffect`): sets `selected` to `new Set(activeLabels)`.

### Click-Outside Detection

On mount, attaches a `mousedown` event listener to `document`. If the click target is outside the container ref, sets `dropdownOpen` to `false`. Cleans up listener on unmount.

### Dirty Detection

`isDirty()` returns `true` when:
- `selected.size` differs from `activeLabels.length`, OR
- Sorted contents of `selected` differ from sorted `activeLabels` (element-wise comparison).

### Trigger Button

- Displays summary text:
  - `selected.size === 0`: "No labels selected"
  - `selected.size === validLabels.length` (and `validLabels.length > 0`): "All labels selected"
  - Otherwise: "{n} labels selected"
- Clicking toggles `dropdownOpen`.
- **Styling**:
  - width: `100%`.
  - padding: `var(--spacing-sm) var(--spacing-md)` (`8px 12px`).
  - backgroundColor: `var(--color-bg-surface)` (`#FFFFFF`).
  - border: `1px solid var(--color-border)` (`1px solid #D4DAE0`).
  - borderRadius: `var(--radius-sm)` (`4px`).
  - color: `var(--color-text-primary)` (`#2C3E50`).
  - textAlign: `left`.
  - cursor: `pointer`.

### Dropdown Panel (visible when `dropdownOpen` is `true`)

**Panel container**:
- position: `absolute`.
- top: `100%`.
- left: `0`, right: `0`.
- backgroundColor: `var(--color-bg-surface)` (`#FFFFFF`).
- border: `1px solid var(--color-border)` (`1px solid #D4DAE0`).
- borderRadius: `var(--radius-sm)` (`4px`).
- marginTop: `var(--spacing-xs)` (`4px`).
- zIndex: `10`.
- maxHeight: `var(--dropdown-max-height)` (`300px`).
- display: `flex`, flexDirection: `column`.

1. **Search input**:
   - type: `text`, placeholder: `"Search labels..."`.
   - padding: `var(--spacing-sm) var(--spacing-md)` (`8px 12px`).
   - border: `none`.
   - borderBottom: `1px solid var(--color-border)` (`1px solid #D4DAE0`).
   - outline: `none`.
   - color: `var(--color-text-primary)` (`#2C3E50`).
   - Filters the label list in real-time (case-insensitive substring match).

2. **Bulk action row** (below search, above list):
   - display: `flex`, gap: `var(--spacing-sm)` (`8px`).
   - padding: `var(--spacing-xs) var(--spacing-md)` (`4px 12px`).
   - borderBottom: `1px solid var(--color-border)` (`1px solid #D4DAE0`).
   - Two buttons:
     - "Select All": sets `selected` to `new Set(validLabels)` (all valid labels, ignoring current search filter).
     - "Clear All": sets `selected` to empty `Set`.
   - Button styling:
     - background: `none`.
     - border: `none`.
     - color: `var(--color-primary)` (`#5B8CB8`).
     - cursor: `pointer`.
     - padding: `var(--spacing-xs)` (`4px`).
     - fontSize: `var(--font-size-small)` (`0.85rem`).

3. **Label list**:
   - overflowY: `auto`.
   - maxHeight: `var(--dropdown-list-max-height)` (`220px`).
   - Each row (`<label>` element):
     - display: `flex`.
     - alignItems: `center`.
     - gap: `var(--spacing-sm)` (`8px`).
     - padding: `6px var(--spacing-md)` (`6px 12px`).
     - cursor: `pointer`.
     - color: `var(--color-text-primary)` (`#2C3E50`).
   - Checkbox: checked if the label is in `selected`. Clicking toggles that label in/out of `selected`.

### Update Button

- Positioned below the trigger button (outside the dropdown panel).
- marginTop: `var(--spacing-sm)` (`8px`).
- padding: `var(--spacing-sm) var(--spacing-lg)` (`8px 16px`).
- backgroundColor: `var(--color-primary)` (`#5B8CB8`) when enabled; `var(--color-primary-disabled)` (`#A8C4DC`) when disabled.
- color: `var(--color-white)` (`#FFFFFF`).
- border: `none`.
- borderRadius: `var(--radius-sm)` (`4px`).
- cursor: `pointer` when enabled; `default` when disabled.
- width: `100%`.
- Disabled when `isDirty()` returns `false` OR `updating` is `true`.
- On click:
  1. Sets `updating` to `true`.
  2. Sets `dropdownOpen` to `false`.
  3. Calls `onUpdate(Array.from(selected))`.
  4. On success: parent updates `activeLabels` prop, triggering resync.
  5. On error: caught silently. Internal state not reset.
  6. In all cases (`finally`): sets `updating` to `false`.
- Text: "Update Labels" normally; "Updating..." while in flight.

### Container

- The outermost div uses `position: relative` (for absolute dropdown positioning).
- ref: `containerRef` (for click-outside detection).

## Inputs

| Field | Type | Constraints | Required |
|---|---|---|---|
| `validLabels` | `string[]` | May be empty | Yes |
| `activeLabels` | `string[]` | Subset of validLabels | Yes |
| `onUpdate` | `(labels: string[]) => Promise<void>` | Must return a promise | Yes |

## Outputs

JSX element containing the trigger button, dropdown panel (conditionally), and update button.

## Invariants

- `selected` always resyncs when `activeLabels` prop changes.
- Update button is never enabled when selection matches `activeLabels`.
- "Select All" always selects from `validLabels` (full list), not the filtered list.
- "Clear All" clears everything regardless of search filter.
- Dropdown closes on click outside the container.
- Dropdown closes on submit (before API call).
- `onUpdate` is never called while `updating` is true (button disabled).
- All visual constants must come from design tokens.

## Edge Cases

- Condition: `validLabels` is empty (server returned no labels or load failed).
  Expected: Trigger shows "No labels selected". Dropdown panel has no checkboxes. "Select All" results in empty set. Update button stays disabled (nothing dirty).

- Condition: User selects labels, then `activeLabels` prop changes externally.
  Expected: `selected` resyncs to new `activeLabels`, discarding uncommitted local selections.

- Condition: `searchTerm` filters out all labels.
  Expected: Empty label list in dropdown. Bulk actions still work on the full `validLabels` set.

- Condition: `onUpdate` rejects (API error).
  Expected: `updating` returns to `false`. `selected` retains user's choices for retry.

## Related

- [Design Tokens](../styles/design-tokens.md): defines all visual constants.
- [App](../App.md): parent that provides props and wires to `useConfig`.
- [useConfig](../hooks/useConfig.md): actual API communication.
