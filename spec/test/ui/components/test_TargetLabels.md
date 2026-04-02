# Test Specification: `test/ui/components/test_TargetLabels.md`

## Source File Under Test

`src/ui/components/TargetLabels.tsx`

## Test File

`test/ui/components/TargetLabels.test.tsx`

## Imports Required

```tsx
import { render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import TargetLabels from "../../../src/ui/components/TargetLabels";
```

---

## 1. `TargetLabels`

### 1.1 Happy Path — Rendering

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_target_labels_trigger_shows_count` | `unit` | Trigger area shows number of selected labels | `validLabels=["cat","dog","person"]`, `activeLabels=["cat","dog"]` | trigger text is `"2 labels selected"` |
| `test_target_labels_trigger_shows_none_selected` | `unit` | Trigger shows "No labels selected" when `activeLabels` is empty | `activeLabels=[]` | trigger text is `"No labels selected"` |
| `test_target_labels_trigger_shows_all_selected` | `unit` | Trigger shows "All labels selected" when all valid labels are active | `validLabels=["cat","dog"]`, `activeLabels=["cat","dog"]` | trigger text is `"All labels selected"` |
| `test_target_labels_dropdown_closed_by_default` | `unit` | Dropdown panel is not visible on initial render | render component | dropdown panel is not in the document |

### 1.2 Happy Path — Dropdown Interaction

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_target_labels_click_trigger_opens_dropdown` | `unit` | Clicking the trigger opens the dropdown panel | click trigger area | dropdown panel becomes visible with checkboxes |
| `test_target_labels_click_trigger_again_closes_dropdown` | `unit` | Clicking trigger when open closes the dropdown | click trigger twice | dropdown panel is not visible |
| `test_target_labels_click_outside_closes_dropdown` | `unit` | Clicking outside the dropdown closes it | open dropdown, click outside | dropdown panel is not visible |
| `test_target_labels_active_labels_pre_checked` | `unit` | Labels in `activeLabels` are pre-checked in the dropdown | `activeLabels=["cat"]`; open dropdown | `"cat"` checkbox is checked; `"dog"` checkbox is unchecked |
| `test_target_labels_toggle_label_on` | `unit` | Clicking an unchecked label checks it | open dropdown; click `"dog"` row | `"dog"` checkbox becomes checked |
| `test_target_labels_toggle_label_off` | `unit` | Clicking a checked label unchecks it | open dropdown; click `"cat"` (pre-checked) | `"cat"` checkbox becomes unchecked |

### 1.3 Happy Path — Select All / Clear All

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_target_labels_select_all` | `unit` | "Select All" checks every label | open dropdown; click "Select All" | all checkboxes are checked; trigger shows `"All labels selected"` |
| `test_target_labels_clear_all` | `unit` | "Clear All" unchecks every label | open dropdown; click "Clear All" | all checkboxes are unchecked; trigger shows `"No labels selected"` |
| `test_target_labels_select_all_ignores_search_filter` | `unit` | "Select All" selects all valid labels, not just filtered ones | search for `"cat"`; click "Select All" | all labels (including non-matching) are checked |

### 1.4 Happy Path — Search

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_target_labels_search_filters_list` | `unit` | Typing in search filters visible labels | `validLabels=["cat","car","dog"]`; type `"ca"` in search | `"cat"` and `"car"` visible; `"dog"` not visible |
| `test_target_labels_search_case_insensitive` | `unit` | Search is case-insensitive | type `"CAT"` in search | `"cat"` is visible |
| `test_target_labels_search_no_match` | `unit` | Search with no matches shows empty list | type `"zzz"` in search | no label rows visible |
| `test_target_labels_clear_search_restores_list` | `unit` | Clearing search text restores the full list | type `"ca"`, then clear input | all labels visible |

### 1.5 Happy Path — Update Submission

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_target_labels_update_calls_on_update` | `unit` | Clicking "Update Labels" calls `onUpdate` with selected labels | toggle `"person"` on; click "Update Labels" | `onUpdate` called with array containing `"person"` |
| `test_target_labels_update_button_shows_loading` | `unit` | While `onUpdate` promise is pending, button shows "Updating..." and is disabled | click "Update Labels"; `onUpdate` returns pending promise | button text is `"Updating..."`; button is disabled |
| `test_target_labels_update_success_resyncs` | `unit` | After parent updates `activeLabels` prop, `selected` resyncs and dirty resets | `onUpdate` resolves; parent re-renders with new `activeLabels` | trigger shows updated count; update button is disabled |
| `test_target_labels_update_failure_preserves_selection` | `unit` | After `onUpdate` rejects, internal selection is preserved | `onUpdate` rejects | selected checkboxes unchanged; button re-enables |

### 1.6 Dirty Detection

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_target_labels_button_disabled_when_clean` | `unit` | Update button is disabled when selection matches `activeLabels` | render without modifying selection | "Update Labels" button is disabled |
| `test_target_labels_button_enabled_when_label_toggled` | `unit` | Toggling a label makes the button enabled | toggle one label | "Update Labels" button is enabled |
| `test_target_labels_button_disabled_when_reverted` | `unit` | Reverting toggle back to original disables button | toggle label on then off | "Update Labels" button is disabled |
| `test_target_labels_button_enabled_after_select_all` | `unit` | "Select All" when not all selected makes button enabled | `activeLabels=["cat"]`; click "Select All" | "Update Labels" button is enabled |
| `test_target_labels_button_enabled_after_clear_all` | `unit` | "Clear All" when some selected makes button enabled | `activeLabels=["cat"]`; click "Clear All" | "Update Labels" button is enabled |

### 1.7 None / Empty Input

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_target_labels_empty_valid_labels` | `unit` | When `validLabels` is empty, dropdown opens but shows no items | `validLabels=[]`; open dropdown | dropdown panel visible; no label rows rendered |
| `test_target_labels_empty_active_labels` | `unit` | When `activeLabels` is empty, nothing is pre-checked | `activeLabels=[]`; open dropdown | all checkboxes are unchecked |

---

## Summary Table

| Entity | Test Count (approx.) | unit | e2e | race | Key Concerns |
|---|---|---|---|---|---|
| `TargetLabels` | 27 | 27 | 0 | 0 | trigger text, dropdown open/close, toggle labels, select all/clear all, search filter, update submission, loading, resync, dirty detection, empty inputs |
