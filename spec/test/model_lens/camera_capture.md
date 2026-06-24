# Test Specification: `camera_capture`

## Source File Under Test
`src/model_lens/camera_capture.py`

## Test File
`tests/model_lens/test_camera_capture.py`

---

## `CameraCapture`

### Type Hierarchy

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_camera_capture_is_abstract` | `unit` | CameraCapture cannot be instantiated directly. | | `CameraCapture()` | Raises `TypeError` |
| `test_local_camera_is_subclass_of_camera_capture` | `unit` | LocalCamera inherits from CameraCapture. | | | `issubclass(LocalCamera, CameraCapture)` is `True` |
| `test_rtsp_camera_is_subclass_of_camera_capture` | `unit` | RtspCamera inherits from CameraCapture. | | | `issubclass(RtspCamera, CameraCapture)` is `True` |

---

## `LocalCamera`

### Happy Path — Construction

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_local_camera_opens_device` | `unit` | Construction opens the cv2.VideoCapture with the given device index. | Mock `cv2.VideoCapture` to return a handle where `isOpened()` returns `True`. | `LocalCameraConfig(device_index=0)` | `cv2.VideoCapture` called with `0`; instance created without error |
| `test_local_camera_sets_source_string` | `unit` | Source is set to the format "local:{device_index}". | Mock `cv2.VideoCapture` to return an opened handle. | `LocalCameraConfig(device_index=2)` | Instance source is `"local:2"` |

### Validation Failures

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_local_camera_device_not_found` | `unit` | Raises DeviceNotFoundError when device is unreachable. | Mock `cv2.VideoCapture` to return a handle where `isOpened()` returns `False`. | `LocalCameraConfig(device_index=99)` | Raises `DeviceNotFoundError` |

### Happy Path — read

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_local_camera_read_returns_frame` | `unit` | Successful read returns a Frame with copied data, timestamp, and source. | Mock `cv2.VideoCapture` with `isOpened()` returning `True` and `read()` returning `(True, fake_bgr_array)`. Patch `time.time` to return a fixed value. | Call `camera.read()` | Returns `Frame` with `.data` equal to fake array (copy), `.timestamp` equal to patched time value, `.source` equal to `"local:0"` |
| `test_local_camera_read_copies_buffer` | `unit` | Frame data is a copy of the raw buffer, not the original reference. | Mock `cv2.VideoCapture.read()` to return `(True, numpy_array)`. | Call `camera.read()` | `frame.data is not original_array` (different object) |

### Mock / Dependency Interaction

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_local_camera_read_acquires_lock` | `unit` | read() acquires the per-instance lock during cap.read(). | Mock `cv2.VideoCapture` with successful read. Spy on lock acquire/release. | Call `camera.read()` | Lock acquired before `cap.read()` and released after |
| `test_local_camera_reopen_creates_fresh_handle` | `unit` | _reopen() creates a new VideoCapture and stores it. | Mock `cv2.VideoCapture` with `isOpened()=True`. Construct LocalCamera. Mock a new `cv2.VideoCapture` return for the reopen call. | Invoke `camera._reopen()` | New `cv2.VideoCapture(device_index)` called; result stored on `camera._cap` |

### Resource Cleanup

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_local_camera_close_releases_handle` | `unit` | close() releases the underlying cv2 handle. | Mock `cv2.VideoCapture` with `isOpened()=True`. Construct LocalCamera. | Call `camera.close()` | `cap.release()` called |
| `test_local_camera_close_idempotent` | `unit` | Calling close() multiple times does not raise or release again. | Mock `cv2.VideoCapture` with `isOpened()=True`. Construct LocalCamera. Call `close()` once. | Call `camera.close()` a second time | No exception; `cap.release()` called only once total |
| `test_local_camera_context_manager_calls_close` | `unit` | Exiting the context manager calls close(). | Mock `cv2.VideoCapture` with `isOpened()=True`. | Use `with LocalCamera(config) as cam: pass` | `cap.release()` called on exit |

---

## `RtspCamera`

### Happy Path — Construction

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_rtsp_camera_opens_url` | `unit` | Construction opens cv2.VideoCapture with the RTSP URL. | Mock `cv2.VideoCapture` to return a handle where `isOpened()` returns `True`. | `RtspCameraConfig(rtsp_url="rtsp://192.168.1.1/stream")` | `cv2.VideoCapture` called with `"rtsp://192.168.1.1/stream"`; instance created without error |
| `test_rtsp_camera_sets_source_to_url` | `unit` | Source is set to the full RTSP URL string. | Mock `cv2.VideoCapture` to return an opened handle. | `RtspCameraConfig(rtsp_url="rtsp://host/path")` | Instance source is `"rtsp://host/path"` |

### Validation Failures

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_rtsp_camera_invalid_url_prefix` | `unit` | Raises ValidationError when URL does not start with "rtsp://". | | `RtspCameraConfig(rtsp_url="http://example.com/stream")` | Raises `ValidationError` |
| `test_rtsp_camera_rtsps_url_rejected` | `unit` | Raises ValidationError when URL uses rtsps:// scheme. | | `RtspCameraConfig(rtsp_url="rtsps://secure.host/stream")` | Raises `ValidationError` |
| `test_rtsp_camera_device_not_found` | `unit` | Raises DeviceNotFoundError when URL is unreachable. | Mock `cv2.VideoCapture` to return a handle where `isOpened()` returns `False`. | `RtspCameraConfig(rtsp_url="rtsp://unreachable/stream")` | Raises `DeviceNotFoundError` |

### Happy Path — read

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_rtsp_camera_read_returns_frame` | `unit` | Successful read returns a Frame with correct fields. | Mock `cv2.VideoCapture` with `isOpened()=True` and `read()` returning `(True, fake_bgr_array)`. Patch `time.time` to return a fixed value. | Call `camera.read()` | Returns `Frame` with `.data` copy of array, `.timestamp` matching patched time, `.source` matching RTSP URL |

### Resource Cleanup

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_rtsp_camera_close_releases_handle` | `unit` | close() releases the underlying cv2 handle. | Mock `cv2.VideoCapture` with `isOpened()=True`. Construct RtspCamera. | Call `camera.close()` | `cap.release()` called |
| `test_rtsp_camera_close_idempotent` | `unit` | Calling close() multiple times does not raise or release again. | Mock `cv2.VideoCapture` with `isOpened()=True`. Construct RtspCamera. Call `close()` once. | Call `camera.close()` a second time | No exception; `cap.release()` called only once total |

---

## `_retry_read`

### Happy Path — _retry_read

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_retry_read_succeeds_first_attempt` | `unit` | Returns Frame on first successful read without retrying. | Mock `cap.read()` to return `(True, array)`. Patch `time.time` to return fixed timestamp. Provide a mock lock and reopen_fn. | `_retry_read(cap, reopen_fn, "local:0", lock)` | Returns `Frame` with copied data and timestamp; `reopen_fn` not called; `time.sleep` not called |
| `test_retry_read_succeeds_second_attempt` | `unit` | Returns Frame after one failure and one retry. | Mock `cap.read()` to return `(False, None)` then `(True, array)`. Patch `time.sleep` to no-op. Patch `random.uniform` to return `0.5`. Provide mock lock and reopen_fn returning fresh cap. | `_retry_read(cap, reopen_fn, "local:0", lock)` | Returns `Frame`; `time.sleep` called once with `1.5` (1.0 + 0.5 jitter); `reopen_fn` called once |
| `test_retry_read_succeeds_third_attempt` | `unit` | Returns Frame after two failures. | Mock `cap.read()` to fail twice then succeed. Patch `time.sleep` to no-op. Patch `random.uniform` to return `0.0`. Provide mock lock and reopen_fn. | `_retry_read(cap, reopen_fn, "local:0", lock)` | Returns `Frame`; `time.sleep` called twice with `1.0` and `2.0`; `reopen_fn` called twice |

### Error Propagation

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_retry_read_all_attempts_fail_raises_operation_error` | `unit` | Raises OperationError after all 3 attempts are exhausted. | Mock `cap.read()` to always return `(False, None)`. Patch `time.sleep` to no-op. Patch `random.uniform` to return `0.0`. Provide mock lock and reopen_fn. | `_retry_read(cap, reopen_fn, "source", lock)` | Raises `OperationError` |

### Mock / Dependency Interaction

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_retry_read_releases_cap_on_failure` | `unit` | Each failed attempt releases the cap under the lock. | Mock `cap.read()` to return `(False, None)` then `(True, array)`. Patch `time.sleep` to no-op. Provide mock lock and reopen_fn. | `_retry_read(cap, reopen_fn, "source", lock)` | `cap.release()` called once (for the first failed attempt) |
| `test_retry_read_calls_reopen_between_retries` | `unit` | reopen_fn is called between failed attempts to get a fresh handle. | Mock `cap.read()` to fail all 3 times. Patch `time.sleep` to no-op. Provide mock lock and reopen_fn. | `_retry_read(cap, reopen_fn, "source", lock)` | `reopen_fn` called twice (after attempt 1 and attempt 2, not after final attempt); raises `OperationError` |
| `test_retry_read_sleep_outside_lock` | `unit` | Sleep occurs after releasing the lock, not while holding it. | Mock `cap.read()` to fail then succeed. Spy on lock and `time.sleep`. Patch `random.uniform`. | `_retry_read(cap, reopen_fn, "source", lock)` | Lock is not held when `time.sleep` is called |
| `test_retry_read_wait_schedule` | `unit` | Wait durations follow the exponential backoff schedule plus jitter. | Mock `cap.read()` to fail all 3 times. Patch `time.sleep` to no-op. Patch `random.uniform` to return `0.25`. | `_retry_read(cap, reopen_fn, "source", lock)` | `time.sleep` called with `1.25`, `2.25`, `4.25` (base waits 1, 2, 4 plus 0.25 jitter) |
| `test_retry_read_timestamp_captured_after_read` | `unit` | time.time() is called after cap.read() succeeds, not before. | Mock `cap.read()` to succeed. Track call order of `cap.read` and `time.time`. | `_retry_read(cap, reopen_fn, "source", lock)` | `time.time` called after `cap.read` |
