# Test Specification: `App.test.tsx`

## Source File Under Test
`src/ui/src/App.tsx`

## Test File
`src/ui/src/App.test.tsx`

---

## `App`

### Happy Path — Rendering

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `renders_header_component` | `unit` | App renders the Header component. | Mock `useConfig` to return `{ runtimeConfig: null, validLabels: [], loading: false, updateCamera: vi.fn(), updateLabels: vi.fn() }`. | Render `<App />` | Header component is present in the document. |
| `renders_camera_config_with_camera_prop` | `unit` | App passes derived camera from runtimeConfig to CameraConfig. | Mock `useConfig` to return `{ runtimeConfig: { camera: { source_type: "local", device_index: 0 }, confidence_threshold: 0.5, target_labels: ["cat"] }, validLabels: ["cat","dog"], loading: false, updateCamera: vi.fn(), updateLabels: vi.fn() }`. | Render `<App />` | CameraConfig is rendered and receives `camera` prop equal to `{ source_type: "local", device_index: 0 }`. |
| `renders_stream_viewer_with_sse_inactive` | `unit` | StreamViewer receives sseActive as false initially. | Mock `useConfig` to return default state. | Render `<App />` | StreamViewer is rendered with `sseActive` prop `false`. |
| `renders_target_labels_with_props` | `unit` | TargetLabels receives validLabels and activeLabels from useConfig. | Mock `useConfig` to return `{ runtimeConfig: { camera: { source_type: "local", device_index: 0 }, confidence_threshold: 0.5, target_labels: ["cat"] }, validLabels: ["cat","dog"], loading: false, updateCamera: vi.fn(), updateLabels: vi.fn() }`. | Render `<App />` | TargetLabels is rendered with `validLabels=["cat","dog"]` and `activeLabels=["cat"]`. |
| `renders_start_and_stop_buttons` | `unit` | Both Start Stream and Stop Stream buttons are rendered. | Mock `useConfig` to return default state. | Render `<App />` | Both buttons with text "Start Stream" and "Stop Stream" are present. |

### State Transitions

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `start_button_sets_sse_active_true` | `unit` | Clicking Start Stream sets sseActive to true. | Mock `useConfig` to return default state. Render `<App />`. | Click "Start Stream" button. | StreamViewer receives `sseActive` as `true`; Start button becomes disabled; Stop button becomes enabled. |
| `stop_button_sets_sse_active_false` | `unit` | Clicking Stop Stream after starting sets sseActive back to false. | Mock `useConfig` to return default state. Render `<App />`. Click "Start Stream" first. | Click "Stop Stream" button. | StreamViewer receives `sseActive` as `false`; Start button becomes enabled; Stop button becomes disabled. |
| `start_button_disabled_when_sse_active` | `unit` | Start Stream button is disabled when sseActive is true. | Mock `useConfig` to return default state. Render `<App />`. Click "Start Stream". | Inspect Start button. | Start button has `disabled` attribute. |
| `stop_button_disabled_when_sse_inactive` | `unit` | Stop Stream button is disabled when sseActive is false (initial state). | Mock `useConfig` to return default state. | Render `<App />` | Stop button has `disabled` attribute. |

### Null / Empty Input

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `camera_null_when_config_null` | `unit` | When runtimeConfig is null, camera prop passed to CameraConfig is null. | Mock `useConfig` to return `{ runtimeConfig: null, validLabels: [], loading: false, updateCamera: vi.fn(), updateLabels: vi.fn() }`. | Render `<App />` | CameraConfig receives `camera` prop as `null`. |
| `active_labels_empty_when_config_null` | `unit` | When runtimeConfig is null, activeLabels is empty array. | Mock `useConfig` to return `{ runtimeConfig: null, validLabels: [], loading: false, updateCamera: vi.fn(), updateLabels: vi.fn() }`. | Render `<App />` | TargetLabels receives `activeLabels` as `[]`. |
| `confidence_threshold_null_when_config_null` | `unit` | When runtimeConfig is null, confidenceThreshold passed to StreamViewer is null. | Mock `useConfig` to return `{ runtimeConfig: null, validLabels: [], loading: false, updateCamera: vi.fn(), updateLabels: vi.fn() }`. | Render `<App />` | StreamViewer receives `confidenceThreshold` prop as `null`. |

### Mock / Dependency Interaction

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `calls_update_camera_via_camera_config` | `unit` | CameraConfig onUpdate callback calls useConfig's updateCamera. | Mock `useConfig` with `updateCamera` as `vi.fn()`. Render `<App />`. | Trigger CameraConfig's `onUpdate` with `{ source_type: "rtsp", rtsp_url: "rtsp://x" }`. | `updateCamera` was called with `{ source_type: "rtsp", rtsp_url: "rtsp://x" }`. |
| `calls_update_labels_via_target_labels` | `unit` | TargetLabels onUpdate callback calls useConfig's updateLabels. | Mock `useConfig` with `updateLabels` as `vi.fn()`. Render `<App />`. | Trigger TargetLabels' `onUpdate` with `["cat","dog"]`. | `updateLabels` was called with `["cat","dog"]`. |
| `sse_active_default_false` | `unit` | sseActive defaults to false on initial render (stream not auto-started). | Mock `useConfig` to return default state. | Render `<App />` | StreamViewer receives `sseActive` as `false`. |

### Happy Path — Page-Level Styling

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `root_div_has_min_height_100vh` | `unit` | Root div applies minHeight 100vh. | Mock `useConfig` to return default state. | Render `<App />` | Root container element has inline style `minHeight: "100vh"`. |
| `root_div_has_page_background_color` | `unit` | Root div uses page background color token. | Mock `useConfig` to return default state. | Render `<App />` | Root container element has inline style `backgroundColor` set to `var(--color-bg-page)` or the resolved value `#F5F6F8`. |
| `root_div_has_font_family` | `unit` | Root div applies font-family token. | Mock `useConfig` to return default state. | Render `<App />` | Root container element has inline style `fontFamily` set to `var(--font-family)` or the resolved value `system-ui, -apple-system, sans-serif`. |

### Happy Path — Button Styling

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `start_button_enabled_style` | `unit` | Start button has primary background color when enabled. | Mock `useConfig` to return default state. | Render `<App />` | Start Stream button has `backgroundColor` of `var(--color-primary)` or `#5B8CB8`, `color` of `#FFFFFF`, `borderStyle` of `"none"`, `borderRadius` of `4px`, `cursor` of `pointer`. |
| `start_button_disabled_style` | `unit` | Start button has primary-disabled background when disabled. | Mock `useConfig` to return default state. Render `<App />`. Click "Start Stream". | Inspect Start button. | Start Stream button has `backgroundColor` of `var(--color-primary-disabled)` or `#A8C4DC`, `cursor` of `default`. |
| `stop_button_enabled_style` | `unit` | Stop button has secondary background color when enabled. | Mock `useConfig` to return default state. Render `<App />`. Click "Start Stream". | Inspect Stop button. | Stop Stream button has `backgroundColor` of `var(--color-secondary)` or `#6B7B8D`, `color` of `#FFFFFF`, `borderStyle` of `"none"`, `borderRadius` of `4px`, `cursor` of `pointer`. |
| `stop_button_disabled_style` | `unit` | Stop button has secondary-disabled background when disabled. | Mock `useConfig` to return default state. | Render `<App />` | Stop Stream button has `backgroundColor` of `var(--color-secondary-disabled)` or `#D4DAE0`, `cursor` of `default`. |

### Happy Path — Layout Structure

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `content_area_has_correct_padding` | `unit` | Content area below header has correct padding. | Mock `useConfig` to return default state. | Render `<App />` | Content area has padding matching `16px 24px` (or `var(--spacing-lg) var(--spacing-xl)`). |
| `two_column_layout_with_flex` | `unit` | Two-column layout uses flex with correct proportions. | Mock `useConfig` to return default state. | Render `<App />` | Two-column container is `display: flex` with `gap: 16px`. Left column has `flex: 2`, right column has `flex: 1`. |
| `button_row_has_gap` | `unit` | Button row container has flex display with 8px gap. | Mock `useConfig` to return default state. | Render `<App />` | Button row container has `display: flex` and `gap: 8px`. Both buttons have `flex: 1`. |
