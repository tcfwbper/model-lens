# Test Specification: `test/model_lens/test_detection_pipeline.md`

## Source File Under Test

`src/model_lens/detection_pipeline.py`

## Test File

`test/model_lens/test_detection_pipeline.py`

## Imports Required

```python
import dataclasses
import queue
import threading
import time
from unittest.mock import MagicMock, call, patch

import numpy as np
import pytest

from model_lens.detection_pipeline import DetectionPipeline, PipelineResult
from model_lens.entities import (
    DetectionResult,
    Frame,
    LocalCameraConfig,
    RtspCameraConfig,
    RuntimeConfig,
)
from model_lens.exceptions import DeviceNotFoundError, OperationError, ParseError
```

---

## Fixtures

The following fixtures are shared across all test sections. They are defined once here and
referenced by Test ID rows below.

```python
@pytest.fixture
def mock_engine(mocker):
    """A mock InferenceEngine that returns an empty detection list by default."""
    engine = mocker.MagicMock()
    engine.detect.return_value = []
    return engine

@pytest.fixture
def default_config():
    """A RuntimeConfig using the default LocalCameraConfig."""
    return RuntimeConfig()

@pytest.fixture
def mock_camera(mocker):
    """A mock CameraCapture instance that returns a valid Frame by default."""
    camera = mocker.MagicMock()
    camera.read.return_value = Frame(
        data=np.zeros((480, 640, 3), dtype=np.uint8),
        timestamp=1748000400.0,
        source="local:0",
    )
    return camera

@pytest.fixture
def pipeline(mock_engine, default_config, mock_camera, mocker):
    """
    A fully constructed DetectionPipeline with the initial CameraCapture
    replaced by mock_camera. The background thread is NOT started.
    """
    mocker.patch(
        "model_lens.detection_pipeline.LocalCamera",
        return_value=mock_camera,
    )
    p = DetectionPipeline(engine=mock_engine, initial_config=default_config)
    return p
```

---

## 1. `PipelineResult`

### 1.1 Happy Path — Construction

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_pipeline_result_stores_jpeg_bytes` | `jpeg_bytes` field is stored correctly | `PipelineResult(jpeg_bytes=b"\xff\xd8\xff", timestamp=1.0, source="local:0", detections=[])` | `instance.jpeg_bytes == b"\xff\xd8\xff"` |
| `test_pipeline_result_stores_timestamp` | `timestamp` field is stored correctly | `timestamp=1748000400.123` | `instance.timestamp == 1748000400.123` |
| `test_pipeline_result_stores_source` | `source` field is stored correctly | `source="rtsp://192.168.1.10/stream"` | `instance.source == "rtsp://192.168.1.10/stream"` |
| `test_pipeline_result_stores_detections` | `detections` list is stored correctly | `detections=[DetectionResult(label="cat", confidence=0.9, bounding_box=(0.1, 0.2, 0.4, 0.6), is_target=True)]` | `instance.detections[0].label == "cat"` |
| `test_pipeline_result_stores_empty_detections` | Empty `detections` list is stored correctly | `detections=[]` | `instance.detections == []` |

### 1.2 Immutability

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_pipeline_result_is_frozen` | Assigning to any field after construction raises `FrozenInstanceError` | `instance.jpeg_bytes = b""` on a constructed instance | raises `dataclasses.FrozenInstanceError` (or `AttributeError`) |

---

## 2. `DetectionPipeline.__init__`

### 2.1 Happy Path — Construction

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_pipeline_init_stores_engine` | `engine` is stored on the instance | `DetectionPipeline(engine=mock_engine, initial_config=default_config)` with `LocalCamera` patched | `pipeline._engine is mock_engine` |
| `test_pipeline_init_stores_initial_config` | `initial_config` is stored as the current `RuntimeConfig` | same as above | `pipeline._config is default_config` (or equivalent attribute name) |
| `test_pipeline_init_constructs_local_camera` | `LocalCamera` is constructed from `LocalCameraConfig` | `initial_config.camera` is `LocalCameraConfig(device_index=0)` | `LocalCamera` constructor called once with the `LocalCameraConfig` instance |
| `test_pipeline_init_constructs_rtsp_camera` | `RtspCamera` is constructed from `RtspCameraConfig` | `initial_config.camera` is `RtspCameraConfig(rtsp_url="rtsp://x")` with `RtspCamera` patched | `RtspCamera` constructor called once with the `RtspCameraConfig` instance |
| `test_pipeline_init_queue_maxsize_is_five` | Result queue is initialised with `maxsize=5` | constructed `pipeline` | `pipeline.get_queue().maxsize == 5` |
| `test_pipeline_init_started_flag_is_false` | `_started` flag is `False` after construction | constructed `pipeline` | `pipeline._started is False` |
| `test_pipeline_init_stop_event_is_clear` | `_stop_event` is not set after construction | constructed `pipeline` | `pipeline._stop_event.is_set() is False` |
| `test_pipeline_init_camera_changed_event_is_clear` | `_camera_changed_event` is not set after construction | constructed `pipeline` | `pipeline._camera_changed_event.is_set() is False` |

### 2.2 `DeviceNotFoundError` at Construction

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_pipeline_init_device_not_found_sets_camera_to_none` | If `LocalCamera` raises `DeviceNotFoundError`, the internal camera reference is set to `None` | `LocalCamera` patched to raise `DeviceNotFoundError("not found")` | internal camera attribute is `None`; no exception propagates from `__init__` |
| `test_pipeline_init_device_not_found_logs_error` | `DeviceNotFoundError` at construction is logged at `ERROR` level | same as above | `logging.error` (or equivalent) called at least once |

---

## 3. `DetectionPipeline.start`

### 3.1 Happy Path

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_pipeline_start_sets_started_flag` | `_started` is `True` after `start()` | call `pipeline.start()` then immediately `pipeline.stop()` | `pipeline._started is True` |
| `test_pipeline_start_spawns_thread` | A background thread is alive after `start()` | call `pipeline.start()` | `pipeline._thread.is_alive() is True`; then call `pipeline.stop()` to clean up |

### 3.2 Double-Start Guard

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_pipeline_start_raises_on_double_start` | Calling `start()` a second time raises `RuntimeError` | call `pipeline.start()` twice | second call raises `RuntimeError` with message `"Pipeline is already running"`; then call `pipeline.stop()` to clean up |
| `test_pipeline_start_no_thread_spawned_on_double_start` | No additional thread is spawned when `RuntimeError` is raised | call `pipeline.start()` twice (catching the error) | only one background thread exists; then call `pipeline.stop()` to clean up |

---

## 4. `DetectionPipeline.stop`

### 4.1 Happy Path

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_pipeline_stop_sets_stop_event` | `_stop_event` is set after `stop()` | call `pipeline.start()` then `pipeline.stop()` | `pipeline._stop_event.is_set() is True` |
| `test_pipeline_stop_joins_thread` | Background thread is no longer alive after `stop()` | call `pipeline.start()` then `pipeline.stop()` | `pipeline._thread.is_alive() is False` |
| `test_pipeline_stop_closes_camera` | Active `CameraCapture` instance has `close()` called during `stop()` | call `pipeline.start()` then `pipeline.stop()` | `mock_camera.close.call_count >= 1` |

### 4.2 Idempotency

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_pipeline_stop_is_idempotent` | Calling `stop()` twice does not raise | call `pipeline.start()` then `pipeline.stop()` twice | no exception raised on either call |

### 4.3 Stop with No Active Camera

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_pipeline_stop_with_no_camera_does_not_raise` | `stop()` does not raise when internal camera is `None` | construct pipeline with `LocalCamera` raising `DeviceNotFoundError`; call `start()` then `stop()` | no exception raised |

---

## 5. `DetectionPipeline.update_config`

### 5.1 Happy Path

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_update_config_replaces_runtime_config` | The stored `RuntimeConfig` is replaced with the new one | call `pipeline.update_config(new_config)` | internal config attribute is `new_config` |
| `test_update_config_sets_camera_changed_event` | `_camera_changed_event` is set after `update_config` | call `pipeline.update_config(new_config)` | `pipeline._camera_changed_event.is_set() is True` |
| `test_update_config_returns_immediately` | `update_config` returns without blocking | call `pipeline.update_config(new_config)` | returns in under 50 ms (assert using `time.monotonic` before and after) |

---

## 6. `DetectionPipeline.get_queue`

### 6.1 Happy Path

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_get_queue_returns_queue_instance` | `get_queue()` returns a `queue.Queue` instance | call `pipeline.get_queue()` | `isinstance(result, queue.Queue) is True` |
| `test_get_queue_returns_same_object` | Repeated calls return the same queue object | call `pipeline.get_queue()` twice | both calls return `is`-identical object |

---

## 7. `DetectionPipeline._run_one_iteration`

> **Note:** All tests in this section call `_run_one_iteration()` directly on a constructed
> (but not started) `DetectionPipeline` instance. The background thread is never spawned.
> `cv2.imencode` is patched to return `(True, mock_buffer)` by default unless stated otherwise.
> `mock_buffer.tobytes()` returns `b"\xff\xd8\xff"` by default.

### 7.1 Happy Path — Full Iteration

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_run_one_iteration_reads_frame` | `camera.read()` is called once per iteration | call `_run_one_iteration()` with active camera | `mock_camera.read.call_count == 1` |
| `test_run_one_iteration_publishes_pipeline_result` | A `PipelineResult` is placed on the queue | call `_run_one_iteration()` | `pipeline.get_queue().qsize() == 1` |
| `test_run_one_iteration_result_jpeg_bytes` | Published result contains the JPEG bytes from `cv2.imencode` | call `_run_one_iteration()` | `result.jpeg_bytes == b"\xff\xd8\xff"` |
| `test_run_one_iteration_result_timestamp` | Published result copies `timestamp` from `Frame` | `mock_camera.read()` returns `Frame(timestamp=1748000400.0, ...)` | `result.timestamp == 1748000400.0` |
| `test_run_one_iteration_result_source` | Published result copies `source` from `Frame` | `mock_camera.read()` returns `Frame(source="local:0", ...)` | `result.source == "local:0"` |
| `test_run_one_iteration_result_detections` | Published result contains detections from `engine.detect()` | `engine.detect()` returns `[DetectionResult(...)]` | `result.detections == [DetectionResult(...)]` |
| `test_run_one_iteration_calls_detect_with_frame_data` | `engine.detect()` is called with `frame.data` (BGR array) | call `_run_one_iteration()` | first positional arg to `engine.detect` is the original `frame.data` array |
| `test_run_one_iteration_calls_detect_with_target_labels` | `engine.detect()` is called with `target_labels` from current `RuntimeConfig` | `RuntimeConfig(target_labels=["cat"])` | second positional arg to `engine.detect` is `["cat"]` |

### 7.2 BGR → RGB Conversion

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_run_one_iteration_converts_bgr_to_rgb` | `cv2.imencode` receives an RGB array (channels reversed), not the original BGR | patch `cv2.imencode` to capture its argument | the array passed to `cv2.imencode` has channels reversed relative to `frame.data`; specifically `np.array_equal(arg[:, :, 0], frame.data[:, :, 2])` |
| `test_run_one_iteration_does_not_modify_frame_data` | The original `frame.data` array is not modified by the BGR→RGB conversion | construct `frame.data` with known channel values; call `_run_one_iteration()` | `frame.data[:, :, 0]` is unchanged after the iteration |

### 7.3 JPEG Encoding Failure

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_run_one_iteration_skips_frame_on_encode_failure` | If `cv2.imencode` returns `(False, ...)`, no result is published | patch `cv2.imencode` to return `(False, None)` | `pipeline.get_queue().qsize() == 0` |
| `test_run_one_iteration_logs_warning_on_encode_failure` | A `WARNING` is logged when `cv2.imencode` returns `False` | same as above | `logging.warning` (or equivalent) called at least once |

### 7.4 Inference Errors

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_run_one_iteration_skips_frame_on_operation_error` | `OperationError` from `engine.detect()` causes the frame to be skipped | `engine.detect.side_effect = OperationError("fail")` | `pipeline.get_queue().qsize() == 0` |
| `test_run_one_iteration_logs_error_on_operation_error` | `OperationError` from `engine.detect()` is logged at `ERROR` level | same as above | `logging.error` (or equivalent) called at least once |
| `test_run_one_iteration_exits_on_parse_error` | `ParseError` from `engine.detect()` causes `sys.exit(1)` | `engine.detect.side_effect = ParseError("mismatch")` | raises `SystemExit` with code `1` |
| `test_run_one_iteration_logs_critical_on_parse_error` | `ParseError` from `engine.detect()` is logged at `CRITICAL` level | same as above | `logging.critical` (or equivalent) called at least once |

### 7.5 Camera Read Error

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_run_one_iteration_clears_camera_on_operation_error` | `OperationError` from `camera.read()` sets internal camera to `None` | `mock_camera.read.side_effect = OperationError("fail")` | internal camera attribute is `None` after the iteration |
| `test_run_one_iteration_closes_camera_on_operation_error` | `OperationError` from `camera.read()` calls `close()` on the camera | same as above | `mock_camera.close.call_count == 1` |
| `test_run_one_iteration_logs_error_on_camera_operation_error` | `OperationError` from `camera.read()` is logged at `ERROR` level | same as above | `logging.error` (or equivalent) called at least once |
| `test_run_one_iteration_skips_publish_on_camera_operation_error` | No result is published when `camera.read()` raises `OperationError` | same as above | `pipeline.get_queue().qsize() == 0` |

### 7.6 No Active Camera

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_run_one_iteration_does_not_read_when_no_camera` | `camera.read()` is never called when internal camera is `None` | set internal camera to `None` before calling `_run_one_iteration()` | `mock_camera.read.call_count == 0` |
| `test_run_one_iteration_does_not_publish_when_no_camera` | No result is published when internal camera is `None` | same as above | `pipeline.get_queue().qsize() == 0` |

### 7.7 Camera Changed Event — Camera Recreation

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_run_one_iteration_recreates_local_camera_on_event` | When `_camera_changed_event` is set and new config has `LocalCameraConfig`, `LocalCamera` is constructed | set `_camera_changed_event`; set config to `RuntimeConfig(camera=LocalCameraConfig(device_index=1))` | `LocalCamera` constructor called with the new `LocalCameraConfig` |
| `test_run_one_iteration_recreates_rtsp_camera_on_event` | When `_camera_changed_event` is set and new config has `RtspCameraConfig`, `RtspCamera` is constructed | set `_camera_changed_event`; set config to `RuntimeConfig(camera=RtspCameraConfig(rtsp_url="rtsp://new"))` | `RtspCamera` constructor called with the new `RtspCameraConfig` |
| `test_run_one_iteration_closes_old_camera_before_recreating` | The old `CameraCapture` is closed before the new one is constructed | set `_camera_changed_event` with an existing active camera | `old_camera.close.call_count == 1` before new camera is constructed |
| `test_run_one_iteration_clears_camera_changed_event_after_handling` | `_camera_changed_event` is cleared after being handled | set `_camera_changed_event`; call `_run_one_iteration()` | `pipeline._camera_changed_event.is_set() is False` after the call |
| `test_run_one_iteration_sets_camera_to_none_on_device_not_found` | If new `CameraCapture` raises `DeviceNotFoundError`, internal camera is set to `None` | set `_camera_changed_event`; patch `LocalCamera` to raise `DeviceNotFoundError` | internal camera attribute is `None` |
| `test_run_one_iteration_logs_error_on_device_not_found_in_loop` | `DeviceNotFoundError` during camera recreation is logged at `ERROR` level | same as above | `logging.error` (or equivalent) called at least once |

### 7.8 Queue — Drop Oldest When Full

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_run_one_iteration_drops_oldest_when_queue_full` | When the queue is full, the oldest item is discarded before the new result is put | fill the queue to `maxsize=5` with sentinel values; call `_run_one_iteration()` | queue still has `5` items; the oldest sentinel is gone; the newest `PipelineResult` is present |
| `test_run_one_iteration_logs_debug_on_drop` | A `DEBUG` message is logged when a frame is dropped due to a full queue | same as above | `logging.debug` (or equivalent) called at least once |

### 7.9 FPS Throttle

> **Note:** In all throttle tests, `time.monotonic` is patched to control elapsed time.
> `_stop_event.wait` is patched (or spied upon) to capture the `timeout` argument without
> actually blocking. `_last_frame_time` is set directly on the instance before calling
> `_run_one_iteration()`.

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_run_one_iteration_throttle_waits_when_too_fast` | When elapsed time since last frame is less than `1/30` s, `_stop_event.wait` is called with a positive timeout | patch `time.monotonic` to return `_last_frame_time + 0.010` (10 ms elapsed, min is ~33.3 ms) | `_stop_event.wait` called with `timeout` approximately equal to `1/30 - 0.010` (within 1 ms tolerance) |
| `test_run_one_iteration_throttle_timeout_is_remaining_interval` | The timeout passed to `_stop_event.wait` is the remaining interval, not the full interval | patch `time.monotonic` to return `_last_frame_time + 0.020` | `_stop_event.wait` called with `timeout` approximately `1/30 - 0.020` (within 1 ms tolerance) |
| `test_run_one_iteration_no_throttle_when_slow_source` | When elapsed time exceeds `1/30` s, `_stop_event.wait` is NOT called for throttling | patch `time.monotonic` to return `_last_frame_time + 0.050` (50 ms elapsed) | `_stop_event.wait` not called (or called zero times for throttle purposes) |
| `test_run_one_iteration_updates_last_frame_time_after_publish` | `_last_frame_time` is updated to the current monotonic time after a successful publish | patch `time.monotonic` to return a known value `T` at publish time | `pipeline._last_frame_time == T` after the iteration |

---

## 8. Concurrency — `update_config` Stress Test

> **Note:** These tests start the real background thread via `pipeline.start()` and use
> real `threading.Thread` objects to call `update_config()` concurrently. The pipeline's
> `CameraCapture` is mocked so no hardware is accessed. `pipeline.stop()` is always called
> in a `finally` block to ensure clean teardown.

### 8.1 Simultaneous `update_config` Calls

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_update_config_concurrent_no_exception` | Multiple threads calling `update_config()` simultaneously do not raise any exception | spawn 20 threads each calling `update_config(RuntimeConfig(target_labels=[f"label_{i}"]))` concurrently; join all threads | no exception raised by any thread |
| `test_update_config_concurrent_final_config_is_valid` | After all concurrent `update_config()` calls complete, the stored config is one of the submitted values | same as above; collect all submitted `RuntimeConfig` instances | the pipeline's internal config is `is`-identical to one of the submitted instances |
| `test_update_config_concurrent_camera_changed_event_set` | After all concurrent `update_config()` calls complete, `_camera_changed_event` is set | same as above | `pipeline._camera_changed_event.is_set() is True` immediately after all threads join |

---

## 9. Concurrency — `stop()` Interrupts Frame Loop

> **Note:** These tests start the real background thread via `pipeline.start()`. The mock
> camera's `read()` is configured to block briefly (using `time.sleep(0.05)`) to simulate
> a slow source, giving the stop signal time to arrive mid-iteration. `pipeline.stop()` is
> always called in a `finally` block.

### 9.1 Clean Shutdown Under Load

| Test ID | Description | Input | Expected |
|---|---|---|---|
| `test_stop_from_separate_thread_joins_cleanly` | `stop()` called from a separate thread while the frame loop is running causes the background thread to exit cleanly | start pipeline; after 100 ms, call `stop()` from a new thread; join the stop thread with a 2-second timeout | stop thread joins within 2 seconds; `pipeline._thread.is_alive() is False` |
| `test_stop_interrupts_fps_throttle_wait` | `stop()` interrupts an in-progress FPS throttle wait without waiting for the full interval | configure `_last_frame_time` so the throttle wait would be ~1 second; start pipeline; call `stop()` immediately | `pipeline._thread` joins in well under 1 second (assert join completes within 200 ms) |

---

## Summary Table

| Entity / Behaviour | Test Count (approx.) | Key Concerns |
|---|---|---|
| `PipelineResult` | 6 | all fields stored, frozen |
| `DetectionPipeline.__init__` | 10 | engine/config stored, camera constructed, queue size, flags/events cleared, `DeviceNotFoundError` handled |
| `DetectionPipeline.start` | 4 | `_started` flag, thread spawned, double-start guard, no extra thread on double-start |
| `DetectionPipeline.stop` | 5 | `_stop_event` set, thread joined, camera closed, idempotent, safe with no camera |
| `DetectionPipeline.update_config` | 3 | config replaced, event set, returns immediately |
| `DetectionPipeline.get_queue` | 2 | returns `queue.Queue`, same object each call |
| `_run_one_iteration` — happy path | 8 | frame read, result published, all fields correct, detect args |
| `_run_one_iteration` — BGR→RGB | 2 | channels reversed, original not modified |
| `_run_one_iteration` — JPEG failure | 2 | frame skipped, warning logged |
| `_run_one_iteration` — inference errors | 4 | `OperationError` skips, `ParseError` exits with code 1, both logged |
| `_run_one_iteration` — camera read error | 4 | camera cleared, closed, error logged, no publish |
| `_run_one_iteration` — no camera | 2 | no read, no publish |
| `_run_one_iteration` — camera recreation | 6 | local/RTSP recreated, old closed, event cleared, `DeviceNotFoundError` handled |
| `_run_one_iteration` — queue drop | 2 | oldest dropped, debug logged |
| `_run_one_iteration` — FPS throttle | 4 | wait called with correct timeout, no wait when slow, `_last_frame_time` updated |
| Concurrency — `update_config` | 3 | no exception, final config valid, event set |
| Concurrency — `stop()` | 2 | clean join, throttle wait interrupted |
