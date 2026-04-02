# Test Specification: `test/ui/test_App.md`

## Source File Under Test

`src/ui/App.tsx`

## Test File

`test/ui/App.test.tsx`

## Imports Required

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../../src/ui/App";
```

> **Note:** All `fetch` calls are mocked at the global level. No real HTTP requests are made.

---

## 1. `App`

### 1.1 Happy Path — Page Load

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_app_renders_header` | `unit` | Header with "ModelLens" is rendered on mount | render `<App />` | text `"ModelLens"` is present in the document |
| `test_app_fetches_config_on_mount` | `unit` | `GET /config` is called once on mount | render `<App />` | `fetch` called with `/config` |
| `test_app_fetches_labels_on_mount` | `unit` | `GET /config/labels` is called once on mount | render `<App />` | `fetch` called with `/config/labels` |
| `test_app_parallel_fetch_on_mount` | `unit` | Both `GET` requests are fired before either resolves | render `<App />` | Both `/config` and `/config/labels` fetches initiated before awaiting |
| `test_app_displays_camera_config_from_server` | `unit` | Camera config section reflects data from `GET /config` | mock returns `{ camera: { source_type: "local", device_index: 2 }, ... }` | `"Local Camera"` selected and `"2"` shown in device index field |
| `test_app_displays_target_labels_from_server` | `unit` | Target labels selection reflects `target_labels` from `GET /config` | mock returns `{ target_labels: ["cat", "dog"], ... }` | `"2 labels selected"` displayed in trigger area |
| `test_app_populates_valid_labels_dropdown` | `unit` | Valid labels from `GET /config/labels` populate the dropdown | mock returns `{ valid_labels: ["person", "cat", "dog"] }` | all three labels appear as checkbox items in the dropdown |
| `test_app_displays_confidence_threshold` | `unit` | `confidence_threshold` from `GET /config` shown below stream area | mock returns `{ confidence_threshold: 0.5, ... }` | text `"Confidence Threshold: 0.50"` is present |

### 1.2 Happy Path — Camera Update

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_app_camera_update_success_refreshes_display` | `unit` | After successful `PUT /config/camera`, camera config area reflects the updated value | change source type to `"rtsp"`, fill URL, click "Update Camera"; mock `PUT` returns updated config | camera config area shows new RTSP URL |

### 1.3 Happy Path — Labels Update

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_app_labels_update_success_refreshes_display` | `unit` | After successful `PUT /config/labels`, label selection reflects updated value | toggle a label, click "Update Labels"; mock `PUT` returns updated config | trigger area shows updated count |

### 1.4 Happy Path — SSE Controls

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_app_sse_default_inactive` | `unit` | On page load, stream is inactive | render `<App />` | "Start Stream" button is enabled; "Stop Stream" button is disabled |
| `test_app_start_stream_button_activates_sse` | `unit` | Clicking "Start Stream" activates the SSE connection | click "Start Stream" | "Start Stream" becomes disabled; "Stop Stream" becomes enabled |
| `test_app_stop_stream_button_deactivates_sse` | `unit` | Clicking "Stop Stream" deactivates the SSE connection | activate stream, then click "Stop Stream" | "Start Stream" becomes enabled; "Stop Stream" becomes disabled |

### 1.5 Error Propagation

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_app_get_config_failure_shows_alert` | `unit` | `GET /config` returning an error triggers `alert()` | mock `/config` returns `500` with body `"Internal Server Error"` | `window.alert` called with `"Error 500: Internal Server Error"` |
| `test_app_get_labels_failure_shows_alert` | `unit` | `GET /config/labels` returning an error triggers `alert()` | mock `/config/labels` returns `500` | `window.alert` called with error message |
| `test_app_network_error_shows_alert_with_404` | `unit` | Network failure (fetch throws) triggers `alert()` with 404 | mock `fetch` throws `TypeError` | `window.alert` called with `"Error 404: Server unreachable"` |
| `test_app_get_config_failure_renders_empty_defaults` | `unit` | When `GET /config` fails, page renders with empty default values | mock `/config` returns `500` | camera config fields are empty; no confidence threshold displayed |
| `test_app_get_labels_failure_renders_empty_dropdown` | `unit` | When `GET /config/labels` fails, dropdown has no items | mock `/config/labels` returns `500` | dropdown opens with no label items |
| `test_app_partial_failure_config_only` | `unit` | If `GET /config` fails but `GET /config/labels` succeeds, labels dropdown is populated but camera is empty | mock `/config` fails, `/config/labels` succeeds | valid labels are available; camera fields are empty |
| `test_app_partial_failure_labels_only` | `unit` | If `GET /config/labels` fails but `GET /config` succeeds, camera is populated but dropdown is empty | mock `/config/labels` fails, `/config` succeeds | camera config is displayed; dropdown has no items |

---

## Summary Table

| Entity | Test Count (approx.) | unit | e2e | race | Key Concerns |
|---|---|---|---|---|---|
| `App` | 18 | 18 | 0 | 0 | page load fetch, parallel requests, config display, SSE toggle, error alerts, partial failure |
