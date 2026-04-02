# useConfig Hook Specification

## Core Principle

`useConfig.ts` encapsulates all communication with the Config API (`/config` endpoints).
It provides the current runtime configuration, available labels, and mutation functions to
the App component.

---

## Module Location

`src/ui/hooks/useConfig.ts`

---

## Signature

```ts
function useConfig(): {
  runtimeConfig: RuntimeConfig | null;
  validLabels: string[];
  loading: boolean;
  updateCamera: (camera: CameraConfigData) => Promise<void>;
  updateLabels: (labels: string[]) => Promise<void>;
};
```

---

## Types

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

---

## Behaviour

### Initialisation (on mount)

Fires two requests in parallel:

1. `GET /config` → sets `runtimeConfig`.
2. `GET /config/labels` → sets `validLabels` from the `valid_labels` field.

`loading` is `true` until both requests settle (success or failure). Each request is
independent: if one fails, the other's result is still used.

**Error handling:** On failure of either request, call `alert()` with the error message
(see App.md error format). Set the corresponding state to its fallback:
- `runtimeConfig` → `null`
- `validLabels` → `[]`

For network errors (fetch throws `TypeError` or response is not received), use status `404`
and message `"Server unreachable"`.

### `updateCamera(camera)`

1. Sends `PUT /config/camera` with body `{ camera }`.
2. On `200 OK`: updates `runtimeConfig` with the full `RuntimeConfig` from the response body.
3. On error (`400`, `422`, network): calls `alert()` with the error. Does **not** modify
   `runtimeConfig`. The promise rejects so the calling component knows the update failed.

### `updateLabels(labels)`

1. Sends `PUT /config/labels` with body `{ target_labels: labels }`.
2. On `200 OK`: updates `runtimeConfig` with the full `RuntimeConfig` from the response body.
3. On error: same handling as `updateCamera`.

---

## API Base URL

All fetch calls target relative paths (e.g. `/config`), relying on the dev server proxy or
same-origin deployment to reach the FastAPI backend.
