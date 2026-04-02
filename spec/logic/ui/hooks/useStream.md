# useStream Hook Specification

## Core Principle

`useStream.ts` manages the SSE connection to `GET /stream` and provides the latest frame
data to the StreamViewer component for rendering.

---

## Module Location

`src/ui/hooks/useStream.ts`

---

## Signature

```ts
function useStream(active: boolean): {
  frame: FrameData | null;
};
```

---

## Types

```ts
interface Detection {
  label: string;
  confidence: number;
  bounding_box: [number, number, number, number]; // [x1, y1, x2, y2] normalised
  is_target: boolean;
}

interface FrameData {
  jpeg_b64: string;
  timestamp: number;
  source: string;
  detections: Detection[];
}
```

---

## Behaviour

### Connection Lifecycle

The hook is controlled by the `active` parameter:

- When `active` transitions from `false` → `true`: opens a new `EventSource` to `/stream`.
- When `active` transitions from `true` → `false`: closes the `EventSource`. Sets `frame`
  to `null`.
- On component unmount: closes the `EventSource` if open.

### Frame Processing

On each SSE `message` event:

1. Parse the `event.data` JSON string into a `FrameData` object.
2. Update the `frame` state with the new object (replacing the previous frame entirely).

Only the **latest frame** is retained; there is no frame buffer or queue.

### Automatic Reconnection

`EventSource` natively reconnects when the connection drops (including the server's 30-second
idle timeout). This hook relies on that built-in behaviour and does **not** implement custom
reconnection logic.

No user-visible notification is shown on reconnect. The stream simply resumes when new frames
arrive.

### Error Handling

If the `EventSource` fires an `error` event:

- Do **not** call `alert()`. Reconnection is silent.
- Optionally log to `console.warn` for debugging.

The hook does not surface connection errors to the user because `EventSource` handles
reconnection automatically.

---

## Cleanup

When the `EventSource` is closed (either by the user stopping the stream or on unmount),
the hook calls `eventSource.close()` and sets `frame` to `null`.
