# Test Specification: `test/ui/hooks/test_useStream.md`

## Source File Under Test

`src/ui/hooks/useStream.ts`

## Test File

`test/ui/hooks/useStream.test.ts`

## Imports Required

```tsx
import { renderHook, act } from "@testing-library/react";
import { useStream } from "../../../src/ui/hooks/useStream";
```

> **Note:** `EventSource` is mocked globally. The mock provides `addEventListener`, `close`,
> and the ability to dispatch `message` and `error` events programmatically.

---

## 1. `useStream`

### 1.1 Happy Path — Connection Lifecycle

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_use_stream_opens_event_source_when_active` | `unit` | Setting `active=true` creates an `EventSource` to `/stream` | render hook with `active=true` | `EventSource` constructor called with `/stream` |
| `test_use_stream_does_not_open_when_inactive` | `unit` | Setting `active=false` does not create an `EventSource` | render hook with `active=false` | `EventSource` constructor not called |
| `test_use_stream_closes_on_deactivate` | `unit` | Transitioning `active` from `true` to `false` closes the `EventSource` | rerender hook with `active=false` | `eventSource.close()` called |
| `test_use_stream_closes_on_unmount` | `unit` | Unmounting the hook closes an open `EventSource` | render with `active=true`; unmount | `eventSource.close()` called |
| `test_use_stream_reopens_on_reactivate` | `unit` | Transitioning `active` from `false` back to `true` opens a new `EventSource` | deactivate then reactivate | new `EventSource` constructor called |

### 1.2 Happy Path — Frame Processing

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_use_stream_parses_frame_from_message` | `unit` | An SSE `message` event is parsed into a `FrameData` object | dispatch message with JSON `{ jpeg_b64: "abc", timestamp: 1.0, source: "local:0", detections: [] }` | `result.current.frame` matches the parsed object |
| `test_use_stream_replaces_frame_on_new_message` | `unit` | Each new message replaces the previous frame | dispatch two messages | `result.current.frame` is the second frame |
| `test_use_stream_frame_null_when_inactive` | `unit` | `frame` is `null` when `active` is `false` | render with `active=false` | `result.current.frame === null` |
| `test_use_stream_frame_reset_on_deactivate` | `unit` | `frame` resets to `null` when transitioning to `active=false` | receive a frame; then rerender with `active=false` | `result.current.frame === null` |

### 1.3 Happy Path — Detection Data

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_use_stream_parses_detections` | `unit` | Detections array in the frame is correctly parsed | message with `detections: [{ label: "cat", confidence: 0.87, bounding_box: [0.1, 0.2, 0.4, 0.6], is_target: true }]` | `result.current.frame.detections[0]` matches the detection object |
| `test_use_stream_empty_detections` | `unit` | Frame with empty detections array is handled | message with `detections: []` | `result.current.frame.detections` is `[]` |

### 1.4 Error Propagation

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_use_stream_error_does_not_alert` | `unit` | `EventSource` error event does not trigger `window.alert` | dispatch `error` event | `window.alert` not called |
| `test_use_stream_error_does_not_clear_frame` | `unit` | `EventSource` error event does not clear the current frame | receive a frame; dispatch `error` event | `result.current.frame` is still the last received frame |

### 1.5 Resource Cleanup

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_use_stream_close_called_once_on_deactivate` | `unit` | `close()` is called exactly once when deactivating | activate then deactivate | `eventSource.close()` called once |
| `test_use_stream_no_close_if_never_activated` | `unit` | Unmounting without ever activating does not call `close()` | render with `active=false`; unmount | `eventSource.close()` not called |

---

## Summary Table

| Entity | Test Count (approx.) | unit | e2e | race | Key Concerns |
|---|---|---|---|---|---|
| `useStream` | 16 | 16 | 0 | 0 | EventSource lifecycle, frame parsing, frame replacement, detection data, silent error handling, cleanup on deactivate/unmount |
