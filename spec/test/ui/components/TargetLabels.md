# Test Specification: `TargetLabels.test.tsx`

## Source File Under Test
`src/ui/src/components/TargetLabels.tsx`

## Test File
`src/ui/src/components/TargetLabels.test.tsx`

---

## `TargetLabels`

### Happy Path — Rendering

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `renders_trigger_button_with_count` | `unit` | Trigger button shows selected count. | | Render `<TargetLabels validLabels={["cat","dog","bird"]} activeLabels={["cat","dog"]} onUpdate={vi.fn()} />` | Button text is "2 labels selected". |
| `renders_no_labels_selected_text` | `unit` | Trigger shows "No labels selected" when none active. | | Render `<TargetLabels validLabels={["cat","dog"]} activeLabels={[]} onUpdate={vi.fn()} />` | Button text is "No labels selected". |
| `renders_all_labels_selected_text` | `unit` | Trigger shows "All labels selected" when all active. | | Render `<TargetLabels validLabels={["cat","dog"]} activeLabels={["cat","dog"]} onUpdate={vi.fn()} />` | Button text is "All labels selected". |
| `dropdown_hidden_initially` | `unit` | Dropdown panel is not visible on initial render. | | Render `<TargetLabels validLabels={["cat","dog"]} activeLabels={["cat"]} onUpdate={vi.fn()} />` | No checkbox elements visible. Search input not visible. |
| `dropdown_opens_on_trigger_click` | `unit` | Clicking trigger button opens dropdown panel. | | Render `<TargetLabels validLabels={["cat","dog"]} activeLabels={["cat"]} onUpdate={vi.fn()} />`. Click trigger button. | Checkboxes for "cat" and "dog" are visible. Search input is visible. |

### State Transitions

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `toggle_label_selection` | `unit` | Clicking a label checkbox toggles its selection. | Render with `validLabels={["cat","dog","bird"]}`, `activeLabels={["cat"]}`. Open dropdown. | Click "dog" checkbox. | "dog" checkbox becomes checked. Trigger shows "2 labels selected". |
| `deselect_label` | `unit` | Clicking a checked label deselects it. | Render with `validLabels={["cat","dog"]}`, `activeLabels={["cat","dog"]}`. Open dropdown. | Click "cat" checkbox. | "cat" checkbox becomes unchecked. Trigger shows "1 labels selected". |
| `select_all_selects_all_valid_labels` | `unit` | "Select All" selects all validLabels regardless of search filter. | Render with `validLabels={["cat","dog","bird"]}`, `activeLabels={[]}`. Open dropdown. Type "cat" in search. | Click "Select All". | All three labels are selected. Trigger shows "All labels selected". |
| `clear_all_deselects_everything` | `unit` | "Clear All" clears all selections. | Render with `validLabels={["cat","dog"]}`, `activeLabels={["cat","dog"]}`. Open dropdown. | Click "Clear All". | All checkboxes unchecked. Trigger shows "No labels selected". |
| `syncs_selected_when_active_labels_change` | `unit` | Internal selected state resyncs when activeLabels prop changes. | Render with `activeLabels={["cat"]}`. | Re-render with `activeLabels={["dog"]}`. | Selected set contains only "dog". |
| `dropdown_closes_on_click_outside` | `unit` | Dropdown closes when user clicks outside the container. | Render and open dropdown. | Dispatch `mousedown` event on `document.body` (outside container). | Dropdown panel is hidden. |
| `updating_flag_disables_button_during_submit` | `unit` | Update button shows "Updating..." during submission. | Render with `validLabels={["cat","dog"]}`, `activeLabels={["cat"]}`. `onUpdate` returns pending promise. | Toggle "dog" on, click "Update Labels". | Button text is "Updating..." and button is disabled. |
| `updating_flag_resets_after_success` | `unit` | Update button re-enables after successful update. | Render with `validLabels={["cat","dog"]}`, `activeLabels={["cat"]}`. `onUpdate` resolves. | Toggle "dog", click "Update Labels", await resolution. | Button text is "Update Labels". |
| `updating_flag_resets_after_error` | `unit` | Update button re-enables after failed update, selection retained. | Render with `validLabels={["cat","dog"]}`, `activeLabels={["cat"]}`. `onUpdate` rejects. | Toggle "dog", click "Update Labels", await rejection. | Button text is "Update Labels". Selected still includes "dog". |

### Happy Path — Dirty Detection

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `update_button_disabled_when_clean` | `unit` | Update button disabled when selection matches activeLabels. | | Render `<TargetLabels validLabels={["cat","dog"]} activeLabels={["cat"]} onUpdate={vi.fn()} />` | "Update Labels" button is disabled. |
| `update_button_enabled_when_dirty` | `unit` | Update button enabled when selection differs from activeLabels. | Render with `activeLabels={["cat"]}`. Open dropdown. | Toggle "dog" on. | "Update Labels" button is enabled. |

### Happy Path — Search Filtering

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `filters_labels_by_search_term` | `unit` | Typing in search input filters displayed labels (case-insensitive). | Render with `validLabels={["cat","dog","catfish"]}`, `activeLabels={[]}`. Open dropdown. | Type "cat" in search input. | Only "cat" and "catfish" checkboxes visible. "dog" not visible. |
| `empty_search_shows_all_labels` | `unit` | Empty search term shows all labels. | Render with `validLabels={["cat","dog"]}`. Open dropdown. Type "cat", then clear input. | Clear search input. | Both "cat" and "dog" checkboxes visible. |
| `search_filters_out_all_labels` | `unit` | Search with no matches shows empty list. | Render with `validLabels={["cat","dog"]}`. Open dropdown. | Type "xyz" in search. | No checkbox elements visible in label list. |

### Mock / Dependency Interaction

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `calls_on_update_with_selected_labels` | `unit` | Clicking Update Labels calls onUpdate with array of selected labels. | Render with `validLabels={["cat","dog"]}`, `activeLabels={["cat"]}`. `onUpdate` is `vi.fn(() => Promise.resolve())`. Open dropdown, toggle "dog". | Click "Update Labels". | `onUpdate` called with array containing "cat" and "dog" (order may vary). |

### Null / Empty Input

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `empty_valid_labels_renders_no_checkboxes` | `unit` | When validLabels is empty, dropdown has no checkboxes. | | Render `<TargetLabels validLabels={[]} activeLabels={[]} onUpdate={vi.fn()} />`. Open dropdown. | No checkbox elements present. Trigger text is "No labels selected". |
| `select_all_with_empty_valid_labels` | `unit` | "Select All" with empty validLabels results in empty set. | Render with `validLabels={[]}`, `activeLabels={[]}`. Open dropdown. | Click "Select All". | Selection remains empty. Button stays disabled. |
