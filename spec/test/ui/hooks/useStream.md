# Test Specification: `useStream.test.ts`

## Source File Under Test
`src/ui/src/hooks/useStream.ts`

## Test File
`src/ui/src/hooks/useStream.test.ts`

---

## `useStream`

### Happy Path — Connection Lifecycle

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `opens_event_source_when_active_true` | `unit` | Creates EventSource to /stream when active becomes true. | Mock `EventSource` constructor globally. | Render hook with `active=true`. | `new EventSource("/stream")` called. |
| `closes_event_source_when_active_false` | `unit` | Closes EventSource when active becomes false. | Mock `EventSource` with a `close` spy. Render hook with `active=true`. | Re-render with `active=false`. | `close()` called on the EventSource instance. |
| `no_event_source_when_initially_inactive` | `unit` | No EventSource created when active starts as false. | Mock `EventSource` constructor. | Render hook with `active=false`. | `EventSource` constructor never called. |
| `closes_event_source_on_unmount` | `unit` | Closes EventSource on component unmount (cleanup). | Mock `EventSource` with a `close` spy. Render hook with `active=true`. | Unmount the hook. | `close()` called on the EventSource instance. |
| `rapid_toggle_closes_before_reopening` | `unit` | Rapid true→false→true closes old connection before opening new one. | Mock `EventSource` with `close` spy. Render with `active=true`. | Re-render `active=false`, then re-render `active=true`. | First instance's `close()` called. A new `EventSource` instance created. |

### Happy Path — Frame Processing

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `parses_frame_from_message_event` | `unit` | Sets frame state from parsed JSON message event. | Mock `EventSource`. Render hook with `active=true`. | Simulate `message` event with `data: '{"jpeg_b64":"abc","timestamp":1,"source":"cam","detections":[]}'`. | `result.current.frame` equals `{ jpeg_b64: "abc", timestamp: 1, source: "cam", detections: [] }`. |
| `replaces_frame_on_new_message` | `unit` | Each new message replaces the previous frame entirely. | Mock `EventSource`. Render with `active=true`. Simulate first message. | Simulate second message with different data. | `result.current.frame` equals the second message's parsed data. |

### State Transitions

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `frame_null_when_inactive` | `unit` | frame is null when active is false. | Mock `EventSource`. | Render hook with `active=false`. | `result.current.frame` is `null`. |
| `frame_reset_to_null_on_deactivation` | `unit` | frame resets to null when active changes to false. | Mock `EventSource`. Render with `active=true`. Simulate a message to set frame. | Re-render with `active=false`. | `result.current.frame` is `null`. |
| `frame_retains_value_on_connection_error` | `unit` | frame retains last value when EventSource error event fires. | Mock `EventSource`. Render with `active=true`. Simulate message to set frame. | Simulate `error` event on EventSource. | `result.current.frame` still equals the previously parsed frame. |

### Error Propagation

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `malformed_json_does_not_update_frame` | `unit` | Malformed JSON in message does not update frame state. | Mock `EventSource`. Render with `active=true`. Simulate valid message first. | Simulate message with `data: 'not json'`. | `result.current.frame` retains previous valid value. No error thrown from hook (error goes to console). |
| `error_listener_does_nothing` | `unit` | Error event listener is attached but performs no action. | Mock `EventSource` with `addEventListener` spy. Render with `active=true`. | Simulate `error` event. | No state change. No alert. No error thrown. |

### Resource Cleanup

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `only_one_event_source_exists_at_a_time` | `unit` | At most one EventSource instance exists at any given time. | Mock `EventSource` tracking all instances. Render with `active=true`. | Re-render `active=false` then `active=true`. | First instance closed before second created. Only one unclosed instance at any time. |
