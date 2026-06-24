# Test Specification: `useConfig.test.ts`

## Source File Under Test
`src/ui/src/hooks/useConfig.ts`

## Test File
`src/ui/src/hooks/useConfig.test.ts`

---

## `useConfig`

### Happy Path — Initialization

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `fetches_config_and_labels_on_mount` | `unit` | Fetches both /config and /config/labels on mount. | Mock `fetch` to resolve: `/config` returns `{ camera: { source_type: "local", device_index: 0 }, confidence_threshold: 0.5, target_labels: ["cat"] }`, `/config/labels` returns `{ valid_labels: ["cat","dog"] }`. | Render hook via `renderHook(() => useConfig())`. | `runtimeConfig` equals the config response. `validLabels` equals `["cat","dog"]`. `loading` is `false`. |
| `loading_true_initially` | `unit` | loading is true before fetches settle. | Mock `fetch` to return pending promises. | Render hook. | `loading` is `true` immediately after render. |
| `loading_false_after_both_settle` | `unit` | loading becomes false after both requests complete. | Mock `fetch` to resolve both requests. | Render hook, await next update. | `loading` is `false`. |

### Error Propagation

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `alerts_on_config_fetch_non_ok` | `unit` | Calls alert with status and body on non-OK /config response. | Mock `fetch`: `/config` returns Response-like `{ ok: false, status: 500, text: () => Promise.resolve("Internal error") }`. `/config/labels` returns OK. Mock `window.alert`. | Render hook, await settlement. | `alert` called with `"Error 500: Internal error"`. `runtimeConfig` is `null`. |
| `alerts_on_labels_fetch_non_ok` | `unit` | Calls alert with status and body on non-OK /config/labels response. | Mock `fetch`: `/config` OK. `/config/labels` returns Response-like `{ ok: false, status: 404, text: () => Promise.resolve("Not found") }`. Mock `window.alert`. | Render hook, await settlement. | `alert` called with `"Error 404: Not found"`. `validLabels` is `[]`. |
| `alerts_on_network_error_config` | `unit` | Calls alert with "Server unreachable" on TypeError from /config fetch. | Mock `fetch` for `/config` to throw `TypeError("Failed to fetch")`. `/config/labels` OK. Mock `window.alert`. | Render hook, await settlement. | `alert` called with `"Error 404: Server unreachable"`. `runtimeConfig` is `null`. |
| `alerts_on_network_error_labels` | `unit` | Calls alert with "Server unreachable" on TypeError from /config/labels fetch. | Mock `fetch` for `/config/labels` to throw `TypeError`. `/config` OK. Mock `window.alert`. | Render hook, await settlement. | `alert` called with `"Error 404: Server unreachable"`. `validLabels` is `[]`. |
| `both_fail_produces_two_alerts` | `unit` | Both requests failing produces two separate alerts. | Mock `fetch` to throw `TypeError` for both URLs. Mock `window.alert`. | Render hook, await settlement. | `alert` called twice. `runtimeConfig` is `null`. `validLabels` is `[]`. `loading` is `false`. |

### Happy Path — updateCamera

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `update_camera_sends_put_and_updates_state` | `unit` | updateCamera sends PUT /config/camera and updates runtimeConfig on success. | Mock initial fetches OK. Mock `fetch` for PUT `/config/camera` to return OK with updated config `{ camera: { source_type: "rtsp", rtsp_url: "rtsp://new" }, confidence_threshold: 0.5, target_labels: ["cat"] }`. | Call `result.current.updateCamera({ source_type: "rtsp", rtsp_url: "rtsp://new" })`. | `fetch` called with `"/config/camera"`, method `"PUT"`, JSON body `{ camera: { source_type: "rtsp", rtsp_url: "rtsp://new" } }`. `runtimeConfig` updated to the response. |
| `update_camera_alerts_and_rejects_on_error` | `unit` | updateCamera alerts and rejects on non-OK response. | Mock initial fetches OK. Mock PUT `/config/camera` to return a Response-like object: `{ ok: false, status: 422, text: () => Promise.resolve("Invalid") }`. Mock `window.alert`. | Call `result.current.updateCamera(...)` and catch the rejection (e.g. wrap in try/catch or use `.catch()`). After the promise settles, assert alert. | `alert` called with `"Error 422: Invalid"`. The returned promise rejects. `runtimeConfig` unchanged. |
| `update_camera_alerts_on_network_error` | `unit` | updateCamera alerts "Server unreachable" on TypeError. | Mock initial fetches OK. Mock PUT to reject with `new TypeError("Failed to fetch")`. Mock `window.alert`. | Call `result.current.updateCamera(...)` and catch the rejection. After the promise settles, assert alert. | `alert` called with `"Error 404: Server unreachable"`. The returned promise rejects. |

### Happy Path — updateLabels

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `update_labels_sends_put_and_updates_state` | `unit` | updateLabels sends PUT /config/labels and updates runtimeConfig on success. | Mock initial fetches OK. Mock PUT `/config/labels` to return OK with updated config. | Call `result.current.updateLabels(["cat","dog"])`. | `fetch` called with `"/config/labels"`, method `"PUT"`, JSON body `{ target_labels: ["cat","dog"] }`. `runtimeConfig` updated. |
| `update_labels_alerts_and_rejects_on_error` | `unit` | updateLabels alerts and rejects on non-OK response. | Mock initial fetches OK. Mock PUT `/config/labels` to return a Response-like object: `{ ok: false, status: 400, text: () => Promise.resolve("Bad request") }`. Mock `window.alert`. | Call `result.current.updateLabels([])` and catch the rejection. After the promise settles, assert alert. | `alert` called with `"Error 400: Bad request"`. The returned promise rejects. `runtimeConfig` unchanged. |

### Idempotency

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `update_camera_is_referentially_stable` | `unit` | updateCamera function reference does not change between renders. | Mock initial fetches OK. | Render hook, capture `result.current.updateCamera`. Re-render. | Reference is the same object (strict equality). |
| `update_labels_is_referentially_stable` | `unit` | updateLabels function reference does not change between renders. | Mock initial fetches OK. | Render hook, capture `result.current.updateLabels`. Re-render. | Reference is the same object (strict equality). |

### Asynchronous Flow

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `update_camera_during_initial_load` | `unit` | updateCamera can be called while initial load is in progress. | Mock `/config` fetch to never resolve (pending). Mock PUT `/config/camera` to resolve with valid config. | Call `updateCamera` immediately. | PUT request is sent. `runtimeConfig` updates from PUT response even though initial GET hasn't resolved. |
