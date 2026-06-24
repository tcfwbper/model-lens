# useConfig

## Overview

Custom React hook that encapsulates all communication with the Config API (`/config` endpoints). Provides the current runtime configuration, available valid labels, loading state, and mutation functions for camera and label updates. Surfaces all errors via `window.alert()`.

## Boundaries

- Owns: fetching initial config and labels on mount; updating config via PUT requests; managing `runtimeConfig` and `validLabels` state; surfacing errors via `alert()`.
- Delegates: rendering and form logic to consuming components.
- Must not: render any UI.
- Must not: manage SSE connections or frame data.
- Must not: perform client-side validation of config values beyond what the API returns.

## Dependencies

| Collaborator | Role | Allowed Interaction | Forbidden Interaction |
|---|---|---|---|
| `GET /config` | Initial config fetch | `fetch("/config")` | — |
| `GET /config/labels` | Valid labels fetch | `fetch("/config/labels")` | — |
| `PUT /config/camera` | Camera update | `fetch("/config/camera", { method: "PUT", ... })` | — |
| `PUT /config/labels` | Labels update | `fetch("/config/labels", { method: "PUT", ... })` | — |
| `window.alert` | Error display | Called with formatted error message | — |

Construction constraint: Must be a React hook (function prefixed with `use`). Uses `useState`, `useEffect`, `useCallback` from React.

## Behavior

### Exported Types

```ts
type CameraConfigData =
  | { source_type: "local"; device_index: number }
  | { source_type: "rtsp"; rtsp_url: string };

interface RuntimeConfig {
  camera: CameraConfigData;
  confidence_threshold: number;
  target_labels: string[];
}
```

### Return Value

```ts
{
  runtimeConfig: RuntimeConfig | null;
  validLabels: string[];
  loading: boolean;
  updateCamera: (camera: CameraConfigData) => Promise<void>;
  updateLabels: (labels: string[]) => Promise<void>;
}
```

### Initialization (on mount)

1. Sets `loading` to `true`.
2. Fires two independent fetch requests in parallel:
   - `GET /config` — on success, sets `runtimeConfig` to the parsed `RuntimeConfig` JSON.
   - `GET /config/labels` — on success, sets `validLabels` from the response's `valid_labels` field.
3. Each request handles errors independently:
   - On non-OK HTTP response: calls `alert()` with `"Error {status}: {response body text}"`. Sets corresponding state to fallback (`null` for config, `[]` for labels).
   - On network error (`TypeError` from fetch): calls `alert()` with `"Error 404: Server unreachable"`. Sets corresponding state to fallback.
4. After both requests settle (regardless of success/failure), sets `loading` to `false`.

### `updateCamera(camera: CameraConfigData)`

1. Sends `PUT /config/camera` with JSON body `{ camera }` and `Content-Type: application/json` header.
2. On success (response OK): parses response body as `RuntimeConfig`, updates `runtimeConfig` state.
3. On non-OK response: calls `alert()` with `"Error {status}: {response body text}"`. Throws the error (promise rejects).
4. On network error (`TypeError`): calls `alert()` with `"Error 404: Server unreachable"`. Re-throws the error.

### `updateLabels(labels: string[])`

1. Sends `PUT /config/labels` with JSON body `{ target_labels: labels }` and `Content-Type: application/json` header.
2. On success (response OK): parses response body as `RuntimeConfig`, updates `runtimeConfig` state.
3. On non-OK response: same error handling as `updateCamera`.
4. On network error: same error handling as `updateCamera`.

### Error Handling Helpers

- `handleResponse(response)`: reads response body as text, calls `alert("Error {status}: {message}")`, throws an `Error`.
- `handleNetworkError(error)`: if error is `TypeError`, calls `alert("Error 404: Server unreachable")` and throws. Otherwise re-throws the original error.

## Inputs

| Field | Type | Constraints | Required |
|---|---|---|---|
| (none — hook takes no parameters) | — | — | — |

## Outputs

| Field | Type | Description |
|---|---|---|
| `runtimeConfig` | `RuntimeConfig \| null` | Current config; `null` before load or on load failure |
| `validLabels` | `string[]` | All valid label strings; `[]` on failure |
| `loading` | `boolean` | `true` until initial fetches settle |
| `updateCamera` | `(camera: CameraConfigData) => Promise<void>` | Stable callback (useCallback) |
| `updateLabels` | `(labels: string[]) => Promise<void>` | Stable callback (useCallback) |

## Invariants

- `updateCamera` and `updateLabels` are referentially stable (wrapped in `useCallback` with empty deps).
- On mutation success, `runtimeConfig` is always updated to the full server response (not a local merge).
- On mutation failure, `runtimeConfig` is not modified.
- All fetch calls use relative paths (e.g. `/config`), relying on same-origin or dev server proxy.
- Errors are always surfaced via `window.alert()`; no inline error state is exposed.

## Edge Cases

- Condition: Both initial requests fail (server unreachable).
  Expected: Two separate `alert()` calls. `runtimeConfig` stays `null`, `validLabels` stays `[]`, `loading` becomes `false`.

- Condition: `updateCamera` called while initial load is still in progress.
  Expected: Proceeds independently; the PUT response updates `runtimeConfig` regardless of initial load state.

- Condition: Server returns non-JSON error body.
  Expected: `response.text()` returns whatever the server sent; displayed in alert as-is.

## Related

- [App](../App.md): sole consumer of this hook.
- [ARCHITECTURE.md](../../../ARCHITECTURE.md): Config API description.
