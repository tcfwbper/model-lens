# useStream

## Overview

Custom React hook that manages an SSE (Server-Sent Events) connection to `/stream` and provides the latest frame data for rendering. Does not render any UI or handle errors visibly — relies on `EventSource` built-in reconnection.

## Boundaries

- Owns: opening and closing the `EventSource` connection; parsing incoming frame JSON; holding the latest `frame` state.
- Delegates: rendering of frame data to consuming components.
- Must not: render any UI.
- Must not: call `alert()` or surface errors to the user.
- Must not: implement custom reconnection logic (relies on `EventSource` native behavior).
- Must not: buffer or queue frames.

## Dependencies

| Collaborator | Role | Allowed Interaction | Forbidden Interaction |
|---|---|---|---|
| `EventSource` (browser API) | SSE connection | `new EventSource("/stream")`, `.close()`, `.addEventListener()` | — |
| `/stream` endpoint | Frame data source | Consumed via EventSource | Must not call via `fetch()` |

Construction constraint: Must be a React hook. Uses `useState`, `useEffect`, `useRef` from React.

## Behavior

### Exported Types

```ts
interface Detection {
  label: string;
  confidence: number;
  bounding_box: [number, number, number, number]; // [x1, y1, x2, y2] normalised 0–1
  is_target: boolean;
}

interface FrameData {
  jpeg_b64: string;
  timestamp: number;
  source: string;
  detections: Detection[];
}
```

### Signature

```ts
function useStream(active: boolean): { frame: FrameData | null }
```

### Connection Lifecycle

1. When `active` changes to `true`: creates a new `EventSource("/stream")` and stores it in a ref.
2. Attaches a `"message"` event listener that parses `event.data` as JSON and sets `frame` state.
3. Attaches an `"error"` event listener that does nothing (silent — EventSource reconnects automatically).
4. When `active` changes to `false`: closes the current `EventSource` (if any), nulls the ref, and sets `frame` to `null`.
5. On component unmount (cleanup function): closes the `EventSource` if open, nulls the ref.

### Frame Processing

- On each `"message"` event: `JSON.parse(event.data)` as `FrameData`, replaces `frame` state entirely.
- Only the latest frame is retained; no history or buffering.

## Inputs

| Field | Type | Constraints | Required |
|---|---|---|---|
| `active` | `boolean` | — | Yes |

## Outputs

| Field | Type | Description |
|---|---|---|
| `frame` | `FrameData \| null` | Latest parsed frame; `null` when inactive or no frame received yet |

## Invariants

- When `active` is `false`, no `EventSource` connection exists and `frame` is `null`.
- At most one `EventSource` instance exists at any time.
- `EventSource` is always closed on cleanup (both deactivation and unmount).
- No error is surfaced to the user; reconnection is handled natively by `EventSource`.

## Edge Cases

- Condition: `active` toggles rapidly (true → false → true).
  Expected: Previous EventSource is closed before a new one is opened. No duplicate connections.

- Condition: Server drops the SSE connection.
  Expected: `EventSource` reconnects automatically. Hook does not intervene. `frame` retains the last received value until a new message arrives or `active` becomes `false`.

- Condition: `event.data` is malformed JSON.
  Expected: `JSON.parse` throws; the error propagates to the browser console. `frame` retains its previous value.

## Related

- [StreamViewer](../components/StreamViewer.md): primary consumer of this hook.
- [ARCHITECTURE.md](../../../ARCHITECTURE.md): Stream API description.
