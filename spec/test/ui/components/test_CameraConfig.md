# Test Specification: `test/ui/components/test_CameraConfig.md`

## Source File Under Test

`src/ui/components/CameraConfig.tsx`

## Test File

`test/ui/components/CameraConfig.test.tsx`

## Imports Required

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import CameraConfig from "../../../src/ui/components/CameraConfig";
```

---

## 1. `CameraConfig`

### 1.1 Happy Path — Rendering

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_camera_config_renders_local_source` | `unit` | When `camera` is local, dropdown shows "Local Camera" and device index field is visible | `camera={ source_type: "local", device_index: 0 }` | dropdown value is `"local"`; input with value `"0"` is visible |
| `test_camera_config_renders_rtsp_source` | `unit` | When `camera` is rtsp, dropdown shows "RTSP" and URL field is visible | `camera={ source_type: "rtsp", rtsp_url: "rtsp://192.168.1.10/stream" }` | dropdown value is `"rtsp"`; input with value `"rtsp://192.168.1.10/stream"` is visible |
| `test_camera_config_renders_null_camera` | `unit` | When `camera` is `null`, defaults to "Local Camera" with empty device index | `camera=null` | dropdown value is `"local"`; device index input is empty |

### 1.2 Happy Path — Source Type Switching

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_camera_config_switch_local_to_rtsp_shows_url_field` | `unit` | Switching from local to rtsp hides device index and shows URL field | initial `camera` is local; select `"rtsp"` | device index input disappears; RTSP URL input appears with empty value |
| `test_camera_config_switch_rtsp_to_local_shows_index_field` | `unit` | Switching from rtsp to local hides URL and shows device index field | initial `camera` is rtsp; select `"local"` | URL input disappears; device index input appears with empty value |
| `test_camera_config_switch_clears_hidden_field` | `unit` | Switching source type clears the value of the hidden field | initial local with `device_index: 2`; switch to rtsp then back to local | device index input is empty (not `"2"`) |

### 1.3 Happy Path — Update Submission

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_camera_config_update_local_calls_on_update` | `unit` | Clicking "Update Camera" with local config calls `onUpdate` with correct payload | change device index to `"3"`, click "Update Camera" | `onUpdate` called with `{ source_type: "local", device_index: 3 }` |
| `test_camera_config_update_rtsp_calls_on_update` | `unit` | Clicking "Update Camera" with rtsp config calls `onUpdate` with correct payload | switch to rtsp, enter URL, click "Update Camera" | `onUpdate` called with `{ source_type: "rtsp", rtsp_url: "rtsp://10.0.0.1/feed" }` |
| `test_camera_config_update_button_shows_loading` | `unit` | While `onUpdate` promise is pending, button shows "Updating..." and is disabled | click "Update Camera"; `onUpdate` returns a pending promise | button text is `"Updating..."`; button is disabled |
| `test_camera_config_update_success_resyncs_state` | `unit` | After parent updates `camera` prop, internal state resyncs and dirty resets | `onUpdate` resolves; parent re-renders with new `camera` prop | fields reflect new prop values; update button is disabled |
| `test_camera_config_update_failure_preserves_input` | `unit` | After `onUpdate` rejects, internal form state is preserved for retry | `onUpdate` rejects | field values are unchanged; button re-enables |

### 1.4 Dirty Detection

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_camera_config_button_disabled_when_clean` | `unit` | Update button is disabled when no changes have been made | render with `camera` prop; do not modify any fields | "Update Camera" button is disabled |
| `test_camera_config_button_enabled_when_type_changed` | `unit` | Changing source type marks form as dirty | initial local; switch to rtsp | "Update Camera" button is enabled |
| `test_camera_config_button_enabled_when_index_changed` | `unit` | Changing device index marks form as dirty | initial `device_index: 0`; change to `"1"` | "Update Camera" button is enabled |
| `test_camera_config_button_enabled_when_url_changed` | `unit` | Changing RTSP URL marks form as dirty | initial rtsp with URL; change URL text | "Update Camera" button is enabled |
| `test_camera_config_button_disabled_when_reverted` | `unit` | Reverting changes back to original values disables button | change device index, then revert to original value | "Update Camera" button is disabled |
| `test_camera_config_button_enabled_when_null_camera_and_input` | `unit` | When `camera` is `null`, any non-empty input is dirty | `camera=null`; type `"0"` in device index | "Update Camera" button is enabled |

---

## Summary Table

| Entity | Test Count (approx.) | unit | e2e | race | Key Concerns |
|---|---|---|---|---|---|
| `CameraConfig` | 17 | 17 | 0 | 0 | initial rendering, source type switching, field clearing, update submission, loading state, resync, dirty detection |
