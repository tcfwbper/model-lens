# Test Specification: `CameraConfig.test.tsx`

## Source File Under Test
`src/ui/src/components/CameraConfig.tsx`

## Test File
`src/ui/src/components/CameraConfig.test.tsx`

---

## `CameraConfig`

### Happy Path — Rendering

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `renders_local_camera_fields` | `unit` | Shows device index input when camera is local type. | | Render `<CameraConfig camera={{ source_type: "local", device_index: 2 }} onUpdate={vi.fn()} />` | A number input with value `"2"` is visible. Source type dropdown shows "local" selected. |
| `renders_rtsp_fields` | `unit` | Shows RTSP URL input when camera is rtsp type. | | Render `<CameraConfig camera={{ source_type: "rtsp", rtsp_url: "rtsp://cam" }} onUpdate={vi.fn()} />` | A text input with value `"rtsp://cam"` is visible. Source type dropdown shows "rtsp" selected. |
| `renders_with_null_camera` | `unit` | Renders with defaults when camera prop is null. | | Render `<CameraConfig camera={null} onUpdate={vi.fn()} />` | Dropdown defaults to "local". Device index input is empty. Update button is disabled. |

### State Transitions

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `type_change_clears_fields` | `unit` | Changing source type clears both input fields. | Render with `camera={{ source_type: "local", device_index: 3 }}`. | Change dropdown to "rtsp". | RTSP URL input is empty. Device index field is cleared/hidden. |
| `syncs_state_when_camera_prop_changes` | `unit` | Internal state resyncs when camera prop changes. | Render with `camera={{ source_type: "local", device_index: 0 }}`. | Re-render with `camera={{ source_type: "rtsp", rtsp_url: "rtsp://new" }}`. | Dropdown shows "rtsp". RTSP URL input value is `"rtsp://new"`. |
| `updating_flag_disables_button_during_submit` | `unit` | Update button shows "Updating..." and is disabled during submission. | Render with `camera={{ source_type: "local", device_index: 0 }}`. `onUpdate` returns a pending promise. | Change device index to `"5"`, click "Update Camera". | Button text is "Updating..." and button is disabled. |
| `updating_flag_resets_after_success` | `unit` | Update button re-enables after successful submission. | Render with `camera={{ source_type: "local", device_index: 0 }}`. `onUpdate` resolves. | Change device index to `"5"`, click "Update Camera", await resolution. | Button text is "Update Camera" and button is re-enabled (after prop resync makes it clean). |
| `updating_flag_resets_after_error` | `unit` | Update button re-enables after failed submission. | Render with `camera={{ source_type: "local", device_index: 0 }}`. `onUpdate` rejects with an error. | Change device index to `"5"`, click "Update Camera", await rejection. | Button text is "Update Camera". Form fields retain value `"5"`. |

### Happy Path — Dirty Detection

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `button_disabled_when_clean` | `unit` | Update button disabled when form matches camera prop. | | Render `<CameraConfig camera={{ source_type: "local", device_index: 0 }} onUpdate={vi.fn()} />` | "Update Camera" button is disabled. |
| `button_enabled_when_device_index_differs` | `unit` | Button enables when device index changes from prop value. | Render with `camera={{ source_type: "local", device_index: 0 }}`. | Type `"3"` in device index input. | "Update Camera" button is enabled. |
| `button_enabled_when_type_differs` | `unit` | Button enables when source type differs from prop. | Render with `camera={{ source_type: "local", device_index: 0 }}`. | Change dropdown to "rtsp", type `"rtsp://x"` in URL input. | "Update Camera" button is enabled. |
| `button_enabled_when_rtsp_url_differs` | `unit` | Button enables when RTSP URL changes from prop value. | Render with `camera={{ source_type: "rtsp", rtsp_url: "rtsp://old" }}`. | Type `"rtsp://new"` in URL input. | "Update Camera" button is enabled. |
| `button_enabled_when_camera_null_and_input_provided` | `unit` | Button enables when camera is null and user enters a value. | Render with `camera={null}`. | Type `"0"` in device index input. | "Update Camera" button is enabled. |

### Mock / Dependency Interaction

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `calls_on_update_with_local_config` | `unit` | Submit calls onUpdate with assembled local camera config. | Render with `camera={{ source_type: "local", device_index: 0 }}`. `onUpdate` is `vi.fn(() => Promise.resolve())`. | Change device index to `"2"`, click "Update Camera". | `onUpdate` called with `{ source_type: "local", device_index: 2 }`. |
| `calls_on_update_with_rtsp_config` | `unit` | Submit calls onUpdate with assembled RTSP camera config. | Render with `camera={{ source_type: "rtsp", rtsp_url: "rtsp://old" }}`. `onUpdate` is `vi.fn(() => Promise.resolve())`. | Change URL to `"rtsp://new"`, click "Update Camera". | `onUpdate` called with `{ source_type: "rtsp", rtsp_url: "rtsp://new" }`. |

### Boundary Values — deviceIndex

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `non_numeric_device_index_enables_button` | `unit` | Non-numeric text in device index field enables button (treated as dirty). | Render with `camera={{ source_type: "local", device_index: 0 }}`. | Type `"abc"` in device index input. | "Update Camera" button is enabled. |
| `submits_nan_for_non_numeric_device_index` | `unit` | Non-numeric device index submits NaN as device_index value. | Render with `camera={{ source_type: "local", device_index: 0 }}`. `onUpdate` is `vi.fn(() => Promise.resolve())`. | Type `"abc"` in device index, click "Update Camera". | `onUpdate` called with `{ source_type: "local", device_index: NaN }`. |

### Happy Path — Styling

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `container_has_card_style` | `unit` | Container div applies card-level design token styles. | | Render `<CameraConfig camera={{ source_type: "local", device_index: 0 }} onUpdate={vi.fn()} />` | Container has `backgroundColor` of `#FFFFFF`, `border` of `1px solid #D4DAE0`, `borderRadius` of `8px`, `padding` of `16px`, `display: flex`, `alignItems: center`, `gap` of `12px`. |
| `update_button_enabled_style` | `unit` | Update Camera button has primary color when enabled. | Render with `camera={{ source_type: "local", device_index: 0 }}`. | Change device index to `"5"`. Inspect "Update Camera" button. | Button has `backgroundColor` of `#5B8CB8` (or `var(--color-primary)`), `color` of `#FFFFFF`, `borderStyle` of `"none"`, `borderRadius` of `4px`, `cursor: pointer`. |
| `update_button_disabled_style` | `unit` | Update Camera button has disabled color when clean. | | Render `<CameraConfig camera={{ source_type: "local", device_index: 0 }} onUpdate={vi.fn()} />` | Button has `backgroundColor` of `#A8C4DC` (or `var(--color-primary-disabled)`), `cursor: default`. |
| `select_has_input_style` | `unit` | Source type select applies input design token styles. | | Render `<CameraConfig camera={{ source_type: "local", device_index: 0 }} onUpdate={vi.fn()} />` | Select element has `border` of `1px solid #D4DAE0`, `borderRadius` of `4px`. |
| `device_index_input_has_fixed_width` | `unit` | Device index input has width 120px. | | Render `<CameraConfig camera={{ source_type: "local", device_index: 0 }} onUpdate={vi.fn()} />` | Device index input has `width` of `120px`. |
| `rtsp_input_has_flex_1` | `unit` | RTSP URL input fills remaining space. | | Render `<CameraConfig camera={{ source_type: "rtsp", rtsp_url: "rtsp://cam" }} onUpdate={vi.fn()} />` | RTSP URL input has `flex: 1`. |
