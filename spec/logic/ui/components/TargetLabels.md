# TargetLabels

## Overview

Multi-select dropdown component for choosing which detection labels to monitor. Provides search filtering, bulk select/clear actions, and an explicit "Update Labels" button. Changes are only sent to the backend when the user clicks the update button.

## Boundaries

- Owns: local selection state (`selected` set); dropdown open/close behavior; search filtering; dirty detection; submission orchestration.
- Delegates: actual API call to the parent via `onUpdate` callback.
- Delegates: error display to the parent (errors surface via `alert()` in `useConfig`).
- Must not: call `fetch()` directly.
- Must not: auto-submit on selection change.

## Dependencies

| Collaborator | Role | Allowed Interaction | Forbidden Interaction |
|---|---|---|---|
| Parent (`App`) | Provides props and `onUpdate` callback | Receives props; calls `onUpdate` | Must not access parent state directly |
| `document` (browser API) | Click-outside detection | `addEventListener("mousedown", ...)`, `removeEventListener(...)` | — |

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

### Dropdown Panel (visible when `dropdownOpen` is `true`)

1. **Search input**: text field with placeholder "Search labels...". Filters the label list in real-time (case-insensitive substring match of `searchTerm` against each label).
2. **Bulk action buttons** (below search, above list):
   - "Select All": sets `selected` to `new Set(validLabels)` (all valid labels, ignoring current search filter).
   - "Clear All": sets `selected` to empty `Set`.
3. **Label list**: scrollable (max-height 220px) list of checkboxes, one per label in `validLabels` that matches `searchTerm`. Each row:
   - Checkbox: checked if the label is in `selected`.
   - Label text beside checkbox.
   - Clicking checkbox or label toggles that label in/out of `selected`.

### Update Button

- Label: "Update Labels"
- Positioned below the trigger button (outside the dropdown panel).
- Full width.
- Disabled when `isDirty()` returns `false` OR `updating` is `true`.
- On click:
  1. Sets `updating` to `true`.
  2. Calls `onUpdate(Array.from(selected))`.
  3. On success: parent updates `activeLabels` prop, triggering resync.
  4. On error: caught silently. Internal state not reset.
  5. In all cases (`finally`): sets `updating` to `false`.
- Text changes to "Updating..." while in flight.

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
- `onUpdate` is never called while `updating` is true (button disabled).

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

- [App](../App.md): parent that provides props and wires to `useConfig`.
- [useConfig](../hooks/useConfig.md): actual API communication.
