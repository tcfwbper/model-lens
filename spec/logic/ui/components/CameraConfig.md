# CameraConfig Component Specification

## Core Principle

`CameraConfig.tsx` displays the current camera configuration and provides controls for the
user to modify it. Changes are only sent to the backend when the user explicitly clicks the
update button.

---

## Module Location

`src/ui/components/CameraConfig.tsx`

---

## Props

| Prop | Type | Description |
|---|---|---|
| `camera` | `CameraConfigData \| null` | Current camera config from `GET /config`. `null` if initial load failed. |
| `onUpdate` | `(camera: CameraConfigData) => Promise<void>` | Callback to send `PUT /config/camera`. Returns a promise that resolves on success or rejects on error. |

`CameraConfigData` type:

```ts
type CameraConfigData =
  | { source_type: "local"; device_index: number }
  | { source_type: "rtsp"; rtsp_url: string };
```

---

## Internal State

| State | Type | Initial Value |
|---|---|---|
| `selectedType` | `"local" \| "rtsp"` | From `props.camera.source_type`, or `"local"` if `camera` is `null` |
| `deviceIndex` | `string` | From `props.camera.device_index` (as string), or `""` if `null` |
| `rtspUrl` | `string` | From `props.camera.rtsp_url`, or `""` if `null` |
| `dirty` | `boolean` | `false` — becomes `true` when any field differs from `props.camera` |

When `props.camera` changes (i.e. after a successful update from the parent), internal state
resyncs to match the new prop values and `dirty` resets to `false`.

---

## Rendering

### Source Type Dropdown

A `<select>` dropdown with two options:
- `"local"` — displayed as **"Local Camera"**
- `"rtsp"` — displayed as **"RTSP"**

Default selection mirrors `props.camera.source_type`.

### Conditional Input Field

- When `selectedType` is `"local"`: a numeric input field labelled **"Device Index"**,
  bound to `deviceIndex`.
- When `selectedType` is `"rtsp"`: a text input field labelled **"RTSP URL"** with
  placeholder `rtsp://...`, bound to `rtspUrl`.

Switching `selectedType` clears the field that is being hidden (e.g. switching from local to
rtsp clears `deviceIndex`).

### Update Button

- Label: **"Update Camera"**
- Disabled when `dirty` is `false` (no changes from current config).
- On click: calls `props.onUpdate()` with the assembled `CameraConfigData` object.
  - For `"local"`: `{ source_type: "local", device_index: parseInt(deviceIndex) }`
  - For `"rtsp"`: `{ source_type: "rtsp", rtsp_url: rtspUrl }`
- While the request is in flight, the button shows a loading state (disabled, text changes
  to **"Updating..."**).
- On success: parent updates `props.camera`, which resyncs internal state.
- On error: parent handles `alert()`. Internal state is **not** reset (user can retry).

---

## Dirty Detection

`dirty` is `true` when any of the following hold:

- `selectedType` differs from `props.camera.source_type`.
- When `selectedType` is `"local"`: `deviceIndex` (parsed as int) differs from
  `props.camera.device_index`.
- When `selectedType` is `"rtsp"`: `rtspUrl` differs from `props.camera.rtsp_url`.
- `props.camera` is `null` and any field has a non-empty value.
