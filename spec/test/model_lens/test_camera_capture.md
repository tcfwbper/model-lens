# Test Specification: `test/model_lens/test_camera_capture.md`

## Source File Under Test

`src/model_lens/camera_capture.py`

## Test File

`test/model_lens/test_camera_capture.py`

## Imports Required

```python
import threading
import time
from unittest.mock import MagicMock, call, patch

import numpy as np
import pytest

from model_lens.camera_capture import CameraCapture, LocalCamera, RtspCamera
from model_lens.entities import Frame, LocalCameraConfig, RtspCameraConfig
from model_lens.exceptions import DeviceNotFoundError, OperationError, ValidationError
```

---

## 1. `LocalCamera`

### 1.1 Happy Path — Construction

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_local_camera_opens_capture_on_init` | `unit` | `cv2.VideoCapture` is called with the device index on construction | `LocalCamera(LocalCameraConfig(device_index=2))` with `cv2.VideoCapture` patched to return an opened mock | `cv2.VideoCapture` was called with `2` |
| `test_local_camera_source_string` | `unit` | `source` is set to `"local:<device_index>"` | `LocalCamera(LocalCameraConfig(device_index=2))` with mock capture | `instance.source == "local:2"` |
| `test_local_camera_source_string_zero` | `unit` | `source` is set to `"local:0"` for default device index | `LocalCamera(LocalCameraConfig(device_index=0))` with mock capture | `instance.source == "local:0"` |

### 1.2 Validation Failures

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_local_camera_device_not_found_on_init` | `unit` | `DeviceNotFoundError` is raised immediately when `cap.isOpened()` returns `False` | `LocalCamera(LocalCameraConfig(device_index=0))` with mock `isOpened()` returning `False` | raises `DeviceNotFoundError` |

### 1.3 Happy Path — `read()`

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_local_camera_read_returns_frame` | `unit` | A successful `read()` returns a `Frame` with correct `data`, `timestamp`, and `source` | Mock `cap.read()` returns `(True, np.zeros((480, 640, 3), dtype=np.uint8))`; `time.time` patched to return `1748000400.123456` | `frame.data.shape == (480, 640, 3)`, `frame.data.dtype == np.uint8`, `frame.timestamp == 1748000400.123456`, `frame.source == "local:0"` |
| `test_local_camera_read_timestamp_within_bounds` | `unit` | `frame.timestamp` is between `start_time` and `end_time` recorded around the `read()` call | Mock `cap.read()` returns a valid frame; `time.time` is **not** patched | Record `start_time = time.time()` before `read()`; call `read()`; record `end_time = time.time()`; assert `start_time <= frame.timestamp <= end_time` |
| `test_local_camera_read_data_is_copy` | `unit` | `Frame.data` is independent of the buffer returned by `cap.read()` | Mock `cap.read()` returns `(True, arr)` where `arr` is a known array; mutate `arr` after `read()` returns | `frame.data` is unchanged after `arr` is mutated |

### 1.4 Error Propagation

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_local_camera_read_retries_on_failure_then_succeeds` | `unit` | When the first `cap.read()` fails, a new handle is opened and the second attempt succeeds | First `cap.read()` returns `(False, None)`; second `cap.read()` returns a valid frame; `time.sleep` and `random.uniform` patched | Returns a valid `Frame`; `cv2.VideoCapture` was called twice; `time.sleep` was called once with `1.0 + fixed_jitter` |
| `test_local_camera_read_retries_sleep_arguments` | `unit` | Sleep durations follow the base wait schedule with fixed jitter on each retry | First two `cap.read()` calls fail; third succeeds; `random.uniform` patched to return `0.5` | `time.sleep` call args are `call(1.5)` then `call(2.5)` |
| `test_local_camera_read_raises_after_all_retries_exhausted` | `unit` | `OperationError` is raised when all 3 attempts fail | All three `cap.read()` calls return `(False, None)`; `time.sleep` and `random.uniform` patched to return `0.5` | raises `OperationError`; `cv2.VideoCapture` was called 3 times total; `time.sleep` was called 3 times with `call(1.5)`, `call(2.5)`, `call(4.5)` |
| `test_local_camera_read_all_retries_exhausted_sleep_arguments` | `unit` | All three sleep durations (1 s, 2 s, 4 s base) are used in order when all attempts are exhausted | All three `cap.read()` calls return `(False, None)`; `random.uniform` patched to return `0.5` | `time.sleep` call args are exactly `call(1.5)`, `call(2.5)`, `call(4.5)` in that order |
| `test_local_camera_read_retry_reopens_handle` | `unit` | On each retry, the old handle is released and a new `cv2.VideoCapture` is opened | Two failures then one success; `time.sleep` and `random.uniform` patched | `cap.release()` was called twice (once per failed attempt before re-open) |

### 1.5 Resource Cleanup

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_local_camera_close_releases_capture` | `unit` | `close()` calls `cap.release()` on the underlying handle | Constructed `LocalCamera` with mock capture; call `close()` | `cap.release()` was called once |
| `test_local_camera_close_is_idempotent` | `unit` | Calling `close()` twice does not raise and does not call `cap.release()` a second time | Call `close()` twice | No exception raised; `cap.release()` was called exactly once |
| `test_local_camera_context_manager_enter_returns_self` | `unit` | `__enter__` returns the `LocalCamera` instance itself | `with LocalCamera(...) as cam:` | `cam is instance` |
| `test_local_camera_context_manager_exit_calls_close` | `unit` | `__exit__` calls `close()`, releasing the capture handle | Use `LocalCamera` as a context manager; exit the block | `cap.release()` was called once |
| `test_local_camera_context_manager_exit_calls_close_on_exception` | `unit` | `__exit__` calls `close()` even when the body raises an exception | Raise an arbitrary exception inside the `with` block | `cap.release()` was called once; the exception propagates |

### 1.6 Concurrent Behaviour

| Test ID | Category | Description | Expected |
|---|---|---|---|
| `test_local_camera_concurrent_read_and_close_no_crash` | `race` | Calling `read()` and `close()` concurrently from two threads does not raise an unhandled exception | Spawn one thread calling `read()` (with mock that sleeps briefly) and another calling `close()`; join both; assert no exception was raised by either thread |
| `test_local_camera_close_blocks_until_read_completes` | `race` | `close()` blocks while `read()` holds the lock; `close()` completes only after `read()` returns | Use a `threading.Event` to detect ordering: `read()` sets an event after acquiring the lock; `close()` is called from a second thread; assert `close()` completes after `read()` releases the lock |

---

## 2. `RtspCamera`

### 2.1 Happy Path — Construction

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_rtsp_camera_opens_capture_on_init_domain` | `unit` | `cv2.VideoCapture` is called with a domain-name RTSP URL | `RtspCamera(RtspCameraConfig(rtsp_url="rtsp://example.com/stream"))` with mock capture | `cv2.VideoCapture` was called with `"rtsp://example.com/stream"` |
| `test_rtsp_camera_opens_capture_on_init_ip_port` | `unit` | `cv2.VideoCapture` is called with an IP+port RTSP URL | `RtspCamera(RtspCameraConfig(rtsp_url="rtsp://192.168.1.10:554/stream"))` with mock capture | `cv2.VideoCapture` was called with `"rtsp://192.168.1.10:554/stream"` |
| `test_rtsp_camera_opens_capture_on_init_ip_port_route` | `unit` | `cv2.VideoCapture` is called with an IP+port+route RTSP URL | `RtspCamera(RtspCameraConfig(rtsp_url="rtsp://192.168.1.10:554/live/channel1"))` with mock capture | `cv2.VideoCapture` was called with `"rtsp://192.168.1.10:554/live/channel1"` |
| `test_rtsp_camera_source_string` | `unit` | `source` is set to the full RTSP URL | `RtspCamera(RtspCameraConfig(rtsp_url="rtsp://192.168.1.10/stream"))` with mock capture | `instance.source == "rtsp://192.168.1.10/stream"` |

### 2.2 Validation Failures

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_rtsp_camera_invalid_url_no_scheme` | `unit` | URL without `rtsp://` scheme raises `ValidationError` | `RtspCamera(RtspCameraConfig(rtsp_url="http://192.168.1.10/stream"))` | raises `ValidationError` |
| `test_rtsp_camera_invalid_url_rtsps_scheme` | `unit` | `rtsps://` (TLS) URL raises `ValidationError` | `RtspCamera(RtspCameraConfig(rtsp_url="rtsps://192.168.1.10/stream"))` | raises `ValidationError` |
| `test_rtsp_camera_device_not_found_on_init` | `unit` | `DeviceNotFoundError` is raised immediately when `cap.isOpened()` returns `False` | `RtspCamera(RtspCameraConfig(rtsp_url="rtsp://192.168.1.10/stream"))` with mock `isOpened()` returning `False` | raises `DeviceNotFoundError` |

### 2.3 Happy Path — `read()`

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_rtsp_camera_read_returns_frame` | `unit` | A successful `read()` returns a `Frame` with correct `data`, `timestamp`, and `source` | Mock `cap.read()` returns `(True, np.zeros((480, 640, 3), dtype=np.uint8))`; `time.time` patched to return `1748000400.123456` | `frame.data.shape == (480, 640, 3)`, `frame.data.dtype == np.uint8`, `frame.timestamp == 1748000400.123456`, `frame.source == "rtsp://192.168.1.10/stream"` |
| `test_rtsp_camera_read_timestamp_within_bounds` | `unit` | `frame.timestamp` is between `start_time` and `end_time` recorded around the `read()` call | Mock `cap.read()` returns a valid frame; `time.time` is **not** patched | Record `start_time = time.time()` before `read()`; call `read()`; record `end_time = time.time()`; assert `start_time <= frame.timestamp <= end_time` |
| `test_rtsp_camera_read_data_is_copy` | `unit` | `Frame.data` is independent of the buffer returned by `cap.read()` | Mock `cap.read()` returns `(True, arr)` where `arr` is a known array; mutate `arr` after `read()` returns | `frame.data` is unchanged after `arr` is mutated |

### 2.4 Error Propagation

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_rtsp_camera_read_retries_on_failure_then_succeeds` | `unit` | When the first `cap.read()` fails, a new handle is opened and the second attempt succeeds | First `cap.read()` returns `(False, None)`; second `cap.read()` returns a valid frame; `time.sleep` and `random.uniform` patched | Returns a valid `Frame`; `cv2.VideoCapture` was called twice; `time.sleep` was called once with `1.0 + fixed_jitter` |
| `test_rtsp_camera_read_retries_sleep_arguments` | `unit` | Sleep durations follow the base wait schedule with fixed jitter on each retry | First two `cap.read()` calls fail; third succeeds; `random.uniform` patched to return `0.5` | `time.sleep` call args are `call(1.5)` then `call(2.5)` |
| `test_rtsp_camera_read_raises_after_all_retries_exhausted` | `unit` | `OperationError` is raised when all 3 attempts fail | All three `cap.read()` calls return `(False, None)`; `time.sleep` and `random.uniform` patched to return `0.5` | raises `OperationError`; `cv2.VideoCapture` was called 3 times total; `time.sleep` was called 3 times with `call(1.5)`, `call(2.5)`, `call(4.5)` |
| `test_rtsp_camera_read_all_retries_exhausted_sleep_arguments` | `unit` | All three sleep durations (1 s, 2 s, 4 s base) are used in order when all attempts are exhausted | All three `cap.read()` calls return `(False, None)`; `random.uniform` patched to return `0.5` | `time.sleep` call args are exactly `call(1.5)`, `call(2.5)`, `call(4.5)` in that order |
| `test_rtsp_camera_read_retry_reopens_handle` | `unit` | On each retry, the old handle is released and a new `cv2.VideoCapture` is opened | Two failures then one success; `time.sleep` and `random.uniform` patched | `cap.release()` was called twice (once per failed attempt before re-open) |

### 2.5 Resource Cleanup

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_rtsp_camera_close_releases_capture` | `unit` | `close()` calls `cap.release()` on the underlying handle | Constructed `RtspCamera` with mock capture; call `close()` | `cap.release()` was called once |
| `test_rtsp_camera_close_is_idempotent` | `unit` | Calling `close()` twice does not raise and does not call `cap.release()` a second time | Call `close()` twice | No exception raised; `cap.release()` was called exactly once |
| `test_rtsp_camera_context_manager_enter_returns_self` | `unit` | `__enter__` returns the `RtspCamera` instance itself | `with RtspCamera(...) as cam:` | `cam is instance` |
| `test_rtsp_camera_context_manager_exit_calls_close` | `unit` | `__exit__` calls `close()`, releasing the capture handle | Use `RtspCamera` as a context manager; exit the block | `cap.release()` was called once |
| `test_rtsp_camera_context_manager_exit_calls_close_on_exception` | `unit` | `__exit__` calls `close()` even when the body raises an exception | Raise an arbitrary exception inside the `with` block | `cap.release()` was called once; the exception propagates |

### 2.6 Concurrent Behaviour

| Test ID | Category | Description | Expected |
|---|---|---|---|
| `test_rtsp_camera_concurrent_read_and_close_no_crash` | `race` | Calling `read()` and `close()` concurrently from two threads does not raise an unhandled exception | Spawn one thread calling `read()` (with mock that sleeps briefly) and another calling `close()`; join both; assert no exception was raised by either thread |
| `test_rtsp_camera_close_blocks_until_read_completes` | `race` | `close()` blocks while `read()` holds the lock; `close()` completes only after `read()` returns | Use a `threading.Event` to detect ordering: `read()` sets an event after acquiring the lock; `close()` is called from a second thread; assert `close()` completes after `read()` releases the lock |

---

## Summary Table

| Entity | Test Count (approx.) | unit | e2e | race | Key Concerns |
|---|---|---|---|---|---|
| `LocalCamera` | 19 | 17 | 0 | 2 | construction, source string, device-not-found, read frame fields, timestamp bounds, data copy, error propagation (retry schedule, sleep args, exhausted retries, handle re-open), resource cleanup (close idempotency, context manager enter/exit/exception), concurrent read+close no-crash, close-blocks-read |
| `RtspCamera` | 22 | 20 | 0 | 2 | construction (domain, IP+port, IP+port+route), source string, invalid URL (no scheme, rtsps), device-not-found, read frame fields, timestamp bounds, data copy, error propagation (retry schedule, sleep args, exhausted retries, handle re-open), resource cleanup (close idempotency, context manager enter/exit/exception), concurrent read+close no-crash, close-blocks-read |
