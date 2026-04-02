# Test Specification: `test/ui/hooks/test_useConfig.md`

## Source File Under Test

`src/ui/hooks/useConfig.ts`

## Test File

`test/ui/hooks/useConfig.test.ts`

## Imports Required

```tsx
import { renderHook, act, waitFor } from "@testing-library/react";
import { useConfig } from "../../../src/ui/hooks/useConfig";
```

> **Note:** `global.fetch` is mocked. `window.alert` is mocked via `vi.spyOn` (or `jest.spyOn`).

---

## 1. `useConfig`

### 1.1 Happy Path — Initialisation

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_use_config_loading_true_initially` | `unit` | `loading` is `true` before requests settle | render hook | `result.current.loading === true` |
| `test_use_config_loading_false_after_fetch` | `unit` | `loading` is `false` after both requests settle | mock both `GET` endpoints return `200` | `result.current.loading === false` |
| `test_use_config_fetches_runtime_config` | `unit` | `runtimeConfig` is populated from `GET /config` response | mock `/config` returns `{ camera: { source_type: "local", device_index: 0 }, confidence_threshold: 0.5, target_labels: ["cat"] }` | `result.current.runtimeConfig` matches the mock response |
| `test_use_config_fetches_valid_labels` | `unit` | `validLabels` is populated from `GET /config/labels` response | mock `/config/labels` returns `{ valid_labels: ["cat", "dog"] }` | `result.current.validLabels` is `["cat", "dog"]` |
| `test_use_config_parallel_fetch` | `unit` | Both endpoints are fetched before either resolves | render hook | `fetch` called twice before either promise resolves |

### 1.2 Error Propagation — Initialisation

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_use_config_get_config_error_alerts` | `unit` | `GET /config` failure triggers `alert()` | mock `/config` returns `500` with body `"Internal Server Error"` | `window.alert` called with `"Error 500: Internal Server Error"` |
| `test_use_config_get_config_error_sets_null` | `unit` | `GET /config` failure sets `runtimeConfig` to `null` | mock `/config` returns `500` | `result.current.runtimeConfig === null` |
| `test_use_config_get_labels_error_alerts` | `unit` | `GET /config/labels` failure triggers `alert()` | mock `/config/labels` returns `422` | `window.alert` called with error message |
| `test_use_config_get_labels_error_sets_empty` | `unit` | `GET /config/labels` failure sets `validLabels` to `[]` | mock `/config/labels` returns `422` | `result.current.validLabels` is `[]` |
| `test_use_config_network_error_alerts_404` | `unit` | Network error (fetch throws `TypeError`) triggers alert with 404 | mock `fetch` throws `TypeError` | `window.alert` called with `"Error 404: Server unreachable"` |
| `test_use_config_partial_failure_config_succeeds` | `unit` | If `/config/labels` fails, `/config` result is still used | mock `/config` succeeds, `/config/labels` fails | `runtimeConfig` is populated; `validLabels` is `[]` |
| `test_use_config_partial_failure_labels_succeeds` | `unit` | If `/config` fails, `/config/labels` result is still used | mock `/config` fails, `/config/labels` succeeds | `runtimeConfig` is `null`; `validLabels` is populated |
| `test_use_config_loading_false_after_failure` | `unit` | `loading` becomes `false` even when requests fail | mock both endpoints return errors | `result.current.loading === false` |

### 1.3 Happy Path — `updateCamera`

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_use_config_update_camera_sends_put` | `unit` | `updateCamera` sends `PUT /config/camera` with correct body | call `updateCamera({ source_type: "local", device_index: 1 })` | `fetch` called with `PUT /config/camera` and body `{ camera: { source_type: "local", device_index: 1 } }` |
| `test_use_config_update_camera_success_updates_state` | `unit` | On `200`, `runtimeConfig` is updated from response | mock `PUT` returns updated config | `result.current.runtimeConfig` matches the response |
| `test_use_config_update_camera_success_resolves` | `unit` | On `200`, the returned promise resolves | mock `PUT` returns `200` | `await updateCamera(...)` does not throw |

### 1.4 Error Propagation — `updateCamera`

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_use_config_update_camera_422_alerts` | `unit` | `PUT /config/camera` returning `422` triggers `alert()` | mock `PUT` returns `422` | `window.alert` called with `"Error 422: ..."` |
| `test_use_config_update_camera_error_preserves_state` | `unit` | On error, `runtimeConfig` is not modified | mock `PUT` returns `422` | `runtimeConfig` is unchanged from before the call |
| `test_use_config_update_camera_error_rejects` | `unit` | On error, the returned promise rejects | mock `PUT` returns `400` | `await updateCamera(...)` throws |
| `test_use_config_update_camera_network_error` | `unit` | Network error during `PUT` triggers alert with 404 | mock `fetch` throws `TypeError` | `window.alert` called with `"Error 404: Server unreachable"` |

### 1.5 Happy Path — `updateLabels`

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_use_config_update_labels_sends_put` | `unit` | `updateLabels` sends `PUT /config/labels` with correct body | call `updateLabels(["cat", "dog"])` | `fetch` called with `PUT /config/labels` and body `{ target_labels: ["cat", "dog"] }` |
| `test_use_config_update_labels_success_updates_state` | `unit` | On `200`, `runtimeConfig` is updated from response | mock `PUT` returns updated config | `result.current.runtimeConfig` matches the response |
| `test_use_config_update_labels_empty_array` | `unit` | `updateLabels([])` sends an empty array | call `updateLabels([])` | `fetch` body is `{ target_labels: [] }` |

### 1.6 Error Propagation — `updateLabels`

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_use_config_update_labels_422_alerts` | `unit` | `PUT /config/labels` returning `422` triggers `alert()` | mock `PUT` returns `422` | `window.alert` called with error message |
| `test_use_config_update_labels_error_preserves_state` | `unit` | On error, `runtimeConfig` is not modified | mock `PUT` returns `422` | `runtimeConfig` is unchanged |
| `test_use_config_update_labels_error_rejects` | `unit` | On error, the returned promise rejects | mock `PUT` returns `400` | `await updateLabels(...)` throws |

---

## Summary Table

| Entity | Test Count (approx.) | unit | e2e | race | Key Concerns |
|---|---|---|---|---|---|
| `useConfig` | 26 | 26 | 0 | 0 | init loading, parallel fetch, runtime config population, valid labels, error alerts, null/empty fallbacks, updateCamera PUT/success/error, updateLabels PUT/success/error, network errors |
