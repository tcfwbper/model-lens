# TargetLabels Component Specification

## Core Principle

`TargetLabels.tsx` provides a multi-select dropdown for choosing which detection labels to
filter on. Changes are only sent to the backend when the user explicitly clicks the update
button.

---

## Module Location

`src/ui/components/TargetLabels.tsx`

---

## Props

| Prop | Type | Description |
|---|---|---|
| `validLabels` | `string[]` | Full label list from `GET /config/labels`. Empty array if load failed. |
| `activeLabels` | `string[]` | Currently active `target_labels` from `GET /config`. |
| `onUpdate` | `(labels: string[]) => Promise<void>` | Callback to send `PUT /config/labels`. |

---

## Internal State

| State | Type | Initial Value |
|---|---|---|
| `selected` | `Set<string>` | Initialised from `props.activeLabels` |
| `searchTerm` | `string` | `""` |
| `dropdownOpen` | `boolean` | `false` |
| `dirty` | `boolean` | `false` |

When `props.activeLabels` changes (after a successful update from the parent), `selected`
resyncs and `dirty` resets to `false`.

---

## Rendering

### Multi-Select Dropdown

A custom dropdown (not a native `<select>`) with the following features:

**Trigger area:** Displays a summary of the current selection:
- If nothing selected: **"No labels selected"**
- If all selected: **"All labels selected"**
- Otherwise: **"{n} labels selected"**

Clicking the trigger toggles `dropdownOpen`.

**Dropdown panel** (visible when `dropdownOpen` is `true`):

1. **Search input** — text field at the top of the panel. Filters the label list below in
   real time (case-insensitive substring match on `searchTerm`). Placeholder: **"Search labels..."**.

2. **Bulk actions** — two text buttons below the search input:
   - **"Select All"** — adds all `validLabels` to `selected` (ignores current search filter;
     selects everything).
   - **"Clear All"** — removes all items from `selected`.

3. **Label list** — scrollable list of checkboxes, one per label in `validLabels` that
   matches the current `searchTerm`. Each row shows:
   - A checkbox (checked if the label is in `selected`).
   - The label text.
   - Clicking the row or checkbox toggles that label in `selected`.

Clicking outside the dropdown closes it.

### Update Button

- Label: **"Update Labels"**
- Positioned below the dropdown trigger (outside the dropdown panel).
- Disabled when `dirty` is `false`.
- On click: calls `props.onUpdate()` with `Array.from(selected)`.
- While the request is in flight: disabled, text changes to **"Updating..."**.
- On success: parent updates `props.activeLabels`, which resyncs internal state.
- On error: parent handles `alert()`. Internal state is **not** reset.

---

## Dirty Detection

`dirty` is `true` when the contents of `selected` differ from `props.activeLabels`
(compared as sorted arrays).
