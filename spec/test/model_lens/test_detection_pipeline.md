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

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_pipeline_result_stores_jpeg_bytes` | `unit` | `jpeg_bytes` field is stored correctly | `PipelineResult(jpeg_bytes=b"\xff\xd8\xff", timestamp=1.0, source="local:0", detections=[])` | `instance.jpeg_bytes == b"\xff\xd8\xff"` |
| `test_pipeline_result_stores_timestamp` | `unit` | `timestamp` field is stored correctly | `timestamp=1748000400.123` | `instance.timestamp == 1748000400.123` |
| `test_pipeline_result_stores_source` | `unit` | `source` field is stored correctly | `source="rtsp://192.168.1.10/stream"` | `instance.source == "rtsp://192.168.1.10/stream"` |
| `test_pipeline_result_stores_detections` | `unit` | `detections` list is stored correctly | `detections=[DetectionResult(label="cat", confidence=0.9, bounding_box=(0.1, 0.2, 0.4, 0.6), is_target=True)]` | `instance.detections[0].label == "cat"` |
| `test_pipeline_result_stores_empty_detections` | `unit` | Empty `detections` list is stored correctly | `detections=[]` | `instance.detections == []` |

### 1.2 Immutability

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_pipeline_result_is_frozen` | `unit` | Assigning to any field after construction raises `FrozenInstanceError` | `instance.jpeg_bytes = b""` on a constructed instance | raises `dataclasses.FrozenInstanceError` (or `AttributeError`) |

---

## 2. `DetectionPipeline.__init__`

### 2.1 Happy Path — Construction

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_pipeline_init_stores_engine` | `unit` | `engine` is stored on the instance | `DetectionPipeline(engine=mock_engine, initial_config=default_config)` with `LocalCamera` patched | `pipeline._engine is mock_engine` |
| `test_pipeline_init_stores_initial_config` | `unit` | `initial_config` is stored as the current `RuntimeConfig` | same as above | `pipeline._config is default_config` (or equivalent attribute name) |
| `test_pipeline_init_constructs_local_camera` | `unit` | `LocalCamera` is constructed from `LocalCameraConfig` | `initial_config.camera` is `LocalCameraConfig(device_index=0)` | `LocalCamera` constructor called once with the `LocalCameraConfig` instance |
| `test_pipeline_init_constructs_rtsp_camera` | `unit` | `RtspCamera` is constructed from `RtspCameraConfig` | `initial_config.camera` is `RtspCameraConfig(rtsp_url="rtsp://x")` with `RtspCamera` patched | `RtspCamera` constructor called once with the `RtspCameraConfig` instance |
| `test_pipeline_init_queue_maxsize_is_five` | `unit` | Result queue is initialised with `maxsize=5` | constructed `pipeline` | `pipeline.get_queue().maxsize == 5` |
| `test_pipeline_init_started_flag_is_false` | `unit` | `_started` flag is `False` after construction | constructed `pipeline` | `pipeline._started is False` |
| `test_pipeline_init_stop_event_is_clear` | `unit` | `_stop_event` is not set after construction | constructed `pipeline` | `pipeline._stop_event.is_set() is False` |
| `test_pipeline_init_camera_changed_event_is_clear` | `unit` | `_camera_changed_event` is not set after construction | constructed `pipeline` | `pipeline._camera_changed_event.is_set() is False` |
| `test_pipeline_init_lock_is_created` | `unit` | A `threading.Lock` is initialised for protecting the `RuntimeConfig` slot | constructed `pipeline` | `pipeline._config_lock` (or equivalent attribute) is an instance of `threading.Lock` |

> **Note:** The background thread is stored as `pipeline._thread` (a `threading.Thread` instance). Tests in Sections 3 and 4 reference this attribute directly to check liveness.

### 2.2 Error Propagation

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_pipeline_init_device_not_found_sets_camera_to_none` | `unit` | If `LocalCamera` raises `DeviceNotFoundError`, the internal camera reference is set to `None` | `LocalCamera` patched to raise `DeviceNotFoundError("not found")` | internal camera attribute is `None`; no exception propagates from `__init__` |
| `test_pipeline_init_device_not_found_logs_error` | `unit` | `DeviceNotFoundError` at construction is logged at `ERROR` level | same as above | `logging.error` (or equivalent) called at least once |

---

## 3. `DetectionPipeline.start`

### 3.1 Happy Path

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_pipeline_start_sets_started_flag` | `e2e` | `_started` is `True` after `start()` | call `pipeline.start()` then immediately `pipeline.stop()` | `pipeline._started is True` |
| `test_pipeline_start_spawns_thread` | `e2e` | A background thread is alive after `start()` | call `pipeline.start()` | `pipeline._thread.is_alive() is True`; then call `pipeline.stop()` to clean up |

### 3.2 Validation Failures

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_pipeline_start_raises_on_double_start` | `e2e` | Calling `start()` a second time raises `RuntimeError` | call `pipeline.start()` twice | second call raises `RuntimeError` with message `"Pipeline is already running"`; then call `pipeline.stop()` to clean up |
| `test_pipeline_start_raises_exact_message` | `e2e` | The `RuntimeError` raised on double-start carries the exact message `"Pipeline is already running"` | call `pipeline.start()` twice; catch the second `RuntimeError` | `str(exc) == "Pipeline is already running"`; then call `pipeline.stop()` to clean up |
| `test_pipeline_start_no_thread_spawned_on_double_start` | `e2e` | No additional thread is spawned when `RuntimeError` is raised | call `pipeline.start()` twice (catching the error) | only one background thread exists; then call `pipeline.stop()` to clean up |

---

## 4. `DetectionPipeline.stop`

### 4.1 Happy Path

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_pipeline_stop_sets_stop_event` | `e2e` | `_stop_event` is set after `stop()` | call `pipeline.start()` then `pipeline.stop()` | `pipeline._stop_event.is_set() is True` |
| `test_pipeline_stop_joins_thread` | `e2e` | Background thread is no longer alive after `stop()` | call `pipeline.start()` then `pipeline.stop()` | `pipeline._thread.is_alive() is False` |
| `test_pipeline_stop_closes_camera` | `e2e` | Active `CameraCapture` instance has `close()` called during `stop()` | call `pipeline.start()` then `pipeline.stop()` | `mock_camera.close.call_count >= 1` |
| `test_pipeline_stop_closes_camera_after_join` | `e2e` | `camera.close()` is called only after the background thread has exited | instrument `mock_camera.close` to record whether `pipeline._thread.is_alive()` is `False` at the moment of the call | `pipeline._thread.is_alive() is False` when `mock_camera.close()` is invoked |
| `test_pipeline_stop_does_not_close_engine` | `e2e` | `stop()` never calls any close/teardown method on the `InferenceEngine` | call `pipeline.start()` then `pipeline.stop()` | `mock_engine.close.call_count == 0` (and no other teardown method called) |

### 4.2 Idempotency

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_pipeline_stop_is_idempotent` | `e2e` | Calling `stop()` twice does not raise | call `pipeline.start()` then `pipeline.stop()` twice | no exception raised on either call |

### 4.3 None / Empty Input

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_pipeline_stop_with_no_camera_does_not_raise` | `e2e` | `stop()` does not raise when internal camera is `None` | construct pipeline with `LocalCamera` raising `DeviceNotFoundError`; call `start()` then `stop()` | no exception raised |

---

## 5. `DetectionPipeline.update_config`

### 5.1 Happy Path

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_update_config_replaces_runtime_config` | `unit` | The stored `RuntimeConfig` is replaced with the new one | call `pipeline.update_config(new_config)` | internal config attribute is `new_config` |
| `test_update_config_sets_camera_changed_event` | `unit` | `_camera_changed_event` is set after `update_config` | call `pipeline.update_config(new_config)` | `pipeline._camera_changed_event.is_set() is True` |
| `test_update_config_returns_immediately` | `unit` | `update_config` returns without blocking | call `pipeline.update_config(new_config)` | returns in under 50 ms (assert using `time.monotonic` before and after) |

---

## 6. `DetectionPipeline.get_queue`

### 6.1 Happy Path

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_get_queue_returns_queue_instance` | `unit` | `get_queue()` returns a `queue.Queue` instance | call `pipeline.get_queue()` | `isinstance(result, queue.Queue) is True` |
| `test_get_queue_returns_same_object` | `unit` | Repeated calls return the same queue object | call `pipeline.get_queue()` twice | both calls return `is`-identical object |

---

## 7. `DetectionPipeline._run_one_iteration`

> **Note:** All tests in this section call `_run_one_iteration()` directly on a constructed
> (but not started) `DetectionPipeline` instance. The background thread is never spawned.
> `cv2.imencode` is patched to return `(True, mock_buffer)` by default unless stated otherwise.
> `mock_buffer.tobytes()` returns `b"\xff\xd8\xff"` by default.

### 7.1 Happy Path — Full Iteration

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_run_one_iteration_reads_frame` | `unit` | `camera.read()` is called once per iteration | call `_run_one_iteration()` with active camera | `mock_camera.read.call_count == 1` |
| `test_run_one_iteration_publishes_pipeline_result` | `unit` | A `PipelineResult` is placed on the queue | call `_run_one_iteration()` | `pipeline.get_queue().qsize() == 1` |
| `test_run_one_iteration_result_jpeg_bytes` | `unit` | Published result contains the JPEG bytes from `cv2.imencode` | call `_run_one_iteration()` | `result.jpeg_bytes == b"\xff\xd8\xff"` |
| `test_run_one_iteration_result_timestamp` | `unit` | Published result copies `timestamp` from `Frame` | `mock_camera.read()` returns `Frame(timestamp=1748000400.0, ...)` | `result.timestamp == 1748000400.0` |
| `test_run_one_iteration_result_source` | `unit` | Published result copies `source` from `Frame` | `mock_camera.read()` returns `Frame(source="local:0", ...)` | `result.source == "local:0"` |
| `test_run_one_iteration_result_detections` | `unit` | Published result contains detections from `engine.detect()` | `engine.detect()` returns `[DetectionResult(...)]` | `result.detections == [DetectionResult(...)]` |
| `test_run_one_iteration_calls_detect_with_frame_data` | `unit` | `engine.detect()` is called with `frame.data` (BGR array) | call `_run_one_iteration()` | first positional arg to `engine.detect` is the original `frame.data` array |
| `test_run_one_iteration_calls_detect_with_target_labels` | `unit` | `engine.detect()` is called with `target_labels` from current `RuntimeConfig` | `RuntimeConfig(target_labels=["cat"])` | second positional arg to `engine.detect` is `["cat"]` |

### 7.2 Happy Path — BGR→RGB Conversion

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_run_one_iteration_converts_bgr_to_rgb` | `unit` | `cv2.imencode` receives an RGB array (channels reversed), not the original BGR | patch `cv2.imencode` to capture its argument | the array passed to `cv2.imencode` has channels reversed relative to `frame.data`; specifically `np.array_equal(arg[:, :, 0], frame.data[:, :, 2])` |
| `test_run_one_iteration_does_not_modify_frame_data` | `unit` | The original `frame.data` array is not modified by the BGR→RGB conversion | construct `frame.data` with known channel values; call `_run_one_iteration()` | `frame.data[:, :, 0]` is unchanged after the iteration |

### 7.3 Error Propagation — JPEG Encoding

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_run_one_iteration_skips_frame_on_encode_failure` | `unit` | If `cv2.imencode` returns `(False, ...)`, no result is published | patch `cv2.imencode` to return `(False, None)` | `pipeline.get_queue().qsize() == 0` |
| `test_run_one_iteration_logs_warning_on_encode_failure` | `unit` | A `WARNING` is logged when `cv2.imencode` returns `False` | same as above | `logging.warning` (or equivalent) called at least once |

### 7.4 Error Propagation — Inference Engine

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_run_one_iteration_skips_frame_on_operation_error` | `unit` | `OperationError` from `engine.detect()` causes the frame to be skipped | `engine.detect.side_effect = OperationError("fail")` | `pipeline.get_queue().qsize() == 0` |
| `test_run_one_iteration_logs_error_on_operation_error` | `unit` | `OperationError` from `engine.detect()` is logged at `ERROR` level | same as above | `logging.error` (or equivalent) called at least once |
| `test_run_one_iteration_exits_on_parse_error` | `unit` | `ParseError` from `engine.detect()` causes `sys.exit(1)` | `engine.detect.side_effect = ParseError("mismatch")` | raises `SystemExit` with code `1` |
| `test_run_one_iteration_logs_critical_on_parse_error` | `unit` | `ParseError` from `engine.detect()` is logged at `CRITICAL` level | same as above | `logging.critical` (or equivalent) called at least once |

### 7.5 Error Propagation — Camera Capture

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_run_one_iteration_clears_camera_on_operation_error` | `unit` | `OperationError` from `camera.read()` sets internal camera to `None` | `mock_camera.read.side_effect = OperationError("fail")` | internal camera attribute is `None` after the iteration |
| `test_run_one_iteration_closes_camera_on_operation_error` | `unit` | `OperationError` from `camera.read()` calls `close()` on the camera | same as above | `mock_camera.close.call_count == 1` |
| `test_run_one_iteration_logs_error_on_camera_operation_error` | `unit` | `OperationError` from `camera.read()` is logged at `ERROR` level | same as above | `logging.error` (or equivalent) called at least once |
| `test_run_one_iteration_skips_publish_on_camera_operation_error` | `unit` | No result is published when `camera.read()` raises `OperationError` | same as above | `pipeline.get_queue().qsize() == 0` |
| `test_run_one_iteration_camera_cleared_no_retry` | `unit` | After `OperationError` from `camera.read()`, a subsequent call to `_run_one_iteration()` does not attempt `camera.read()` again | call `_run_one_iteration()` once (raises `OperationError`); call it again | `mock_camera.read.call_count == 1` total across both calls |

### 7.6 None / Empty Input

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_run_one_iteration_does_not_read_when_no_camera` | `unit` | `camera.read()` is never called when internal camera is `None` | set internal camera to `None` before calling `_run_one_iteration()` | `mock_camera.read.call_count == 0` |
| `test_run_one_iteration_does_not_publish_when_no_camera` | `unit` | No result is published when internal camera is `None` | same as above | `pipeline.get_queue().qsize() == 0` |
| `test_run_one_iteration_waits_on_camera_changed_event_when_no_camera` | `unit` | When internal camera is `None`, the loop calls `_camera_changed_event.wait(timeout=1.0)` | set internal camera to `None`; patch `_camera_changed_event.wait` | `_camera_changed_event.wait` called with `timeout=1.0` |

### 7.7 State Transitions

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_run_one_iteration_recreates_local_camera_on_event` | `unit` | When `_camera_changed_event` is set and new config has `LocalCameraConfig`, `LocalCamera` is constructed | set `_camera_changed_event`; set config to `RuntimeConfig(camera=LocalCameraConfig(device_index=1))` | `LocalCamera` constructor called with the new `LocalCameraConfig` |
| `test_run_one_iteration_recreates_rtsp_camera_on_event` | `unit` | When `_camera_changed_event` is set and new config has `RtspCameraConfig`, `RtspCamera` is constructed | set `_camera_changed_event`; set config to `RuntimeConfig(camera=RtspCameraConfig(rtsp_url="rtsp://new"))` | `RtspCamera` constructor called with the new `RtspCameraConfig` |
| `test_run_one_iteration_closes_old_camera_before_recreating` | `unit` | The old `CameraCapture` is closed before the new one is constructed | set `_camera_changed_event` with an existing active camera | `old_camera.close.call_count == 1` before new camera is constructed |
| `test_run_one_iteration_clears_camera_changed_event_after_handling` | `unit` | `_camera_changed_event` is cleared after being handled | set `_camera_changed_event`; call `_run_one_iteration()` | `pipeline._camera_changed_event.is_set() is False` after the call |
| `test_run_one_iteration_sets_camera_to_none_on_device_not_found` | `unit` | If new `CameraCapture` raises `DeviceNotFoundError`, internal camera is set to `None` | set `_camera_changed_event`; patch `LocalCamera` to raise `DeviceNotFoundError` | internal camera attribute is `None` |
| `test_run_one_iteration_logs_error_on_device_not_found_in_loop` | `unit` | `DeviceNotFoundError` during camera recreation is logged at `ERROR` level | same as above | `logging.error` (or equivalent) called at least once |

### 7.8 Boundary Values — queue capacity

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_run_one_iteration_drops_oldest_when_queue_full` | `unit` | When the queue is full, the oldest item is discarded before the new result is put | fill the queue to `maxsize=5` with sentinel values; call `_run_one_iteration()` | queue still has `5` items; the oldest sentinel is gone; the newest `PipelineResult` is present |
| `test_run_one_iteration_logs_debug_on_drop` | `unit` | A `DEBUG` message is logged when a frame is dropped due to a full queue | same as above | `logging.debug` (or equivalent) called at least once |
| `test_run_one_iteration_publishes_when_queue_drained_between_full_check_and_get` | `race` | TOCTOU race: `full()` returns `True` but consumers drain the queue before `get_nowait()` executes, causing `queue.Empty` — the result must still be published | patch `queue.full` to return `True` on the first call while the underlying queue is actually empty; call `_run_one_iteration()` | no exception raised; `pipeline.get_queue().qsize() == 1` and the item is a `PipelineResult` |

### 7.9 Boundary Values — FPS throttle

> **Note:** In all throttle tests, `time.monotonic` is patched to control elapsed time.
> `_stop_event.wait` is patched (or spied upon) to capture the `timeout` argument without
> actually blocking. `_last_frame_time` is set directly on the instance before calling
> `_run_one_iteration()`.

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_run_one_iteration_throttle_waits_when_too_fast` | `unit` | When interval is less than 1/30s, compute remaining time and trigger interruptible wait to cap output at 30 FPS | `elapsed = 10ms` | `_stop_event.wait` called with `timeout == pytest.approx(1/30 - 0.010, abs=5e-3)` |
| `test_run_one_iteration_no_wait_when_already_slow` | `unit` | When capture or processing already exceeds 1/30s, do not wait further (boundary condition) | `elapsed = 40ms` | `_stop_event.wait` not called (or called with timeout 0) |
| `test_run_one_iteration_no_throttle_on_first_frame` | `unit` | First iteration (no previous time record) does not trigger throttle wait | `_last_frame_time = 0` | `_stop_event.wait` not called |
| `test_run_one_iteration_updates_last_frame_time_after_publish` | `unit` | After successful publish, update `_last_frame_time` as the baseline for the next throttle check | patch `time.monotonic` | `pipeline._last_frame_time` updated to current monotonic time |

### 7.10 Concurrent Behaviour

> **Note:** These tests verify that the `RuntimeConfig` lock is used correctly in the frame loop. `_run_one_iteration()` is called directly. The lock is inspected via `unittest.mock` to confirm acquire/release ordering relative to `engine.detect()`.

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_run_one_iteration_releases_lock_before_detect` | `race` | The `RuntimeConfig` lock is released before `engine.detect()` is called | patch the lock's `release` method and `engine.detect` to record call order | `lock.release` is called before `engine.detect` in the call sequence |
| `test_run_one_iteration_detect_called_without_lock` | `race` | `engine.detect()` is not called while the lock is held | patch `engine.detect` to assert `lock.locked() is False` at call time | no `AssertionError` raised inside `engine.detect` |

### 7.11 Happy Path — queue method calls

> **Note:** `queue.Queue.get_nowait` and `queue.Queue.put_nowait` are patched to verify the pipeline uses non-blocking calls exclusively when publishing results.

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_run_one_iteration_uses_put_nowait` | `unit` | The pipeline publishes results via `put_nowait`, not `put` | patch `queue.Queue.put_nowait` and `queue.Queue.put` on the pipeline's queue | `put_nowait` called once; `put` never called |
| `test_run_one_iteration_uses_get_nowait_on_full_queue` | `unit` | When the queue is full, the oldest item is discarded via `get_nowait`, not `get` | fill queue to `maxsize=5`; patch `queue.Queue.get_nowait` and `queue.Queue.get` | `get_nowait` called once; `get` never called |

---

## 8. End-to-End — FPS Cap

> **Note:** These tests start the real background thread via `pipeline.start()`. The mock
> camera's `read()` returns frames immediately (no sleep) to simulate a source faster than
> 30 FPS. The result queue is drained periodically by a consumer thread to prevent it from
> filling up and blocking measurement. `pipeline.stop()` is always called in a `finally`
> block.

### 8.1 Boundary Values — output rate

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_fps_cap_output_rate_does_not_exceed_30` | `e2e` | When the source delivers frames faster than 30 FPS, the pipeline's actual output rate measured over a 1-second window does not exceed 30 FPS | mock camera `read()` returns instantly; run pipeline for 1 second; count `PipelineResult` objects published to the queue | total results published ≤ 32 (30 FPS × 1s plus 2-frame tolerance for timing imprecision) |

---

## 9. Concurrency — `update_config` Stress Test

> **Note:** These tests start the real background thread via `pipeline.start()` and use
> real `threading.Thread` objects to call `update_config()` concurrently. The pipeline's
> `CameraCapture` is mocked so no hardware is accessed. `pipeline.stop()` is always called
> in a `finally` block to ensure clean teardown.

### 9.1 Concurrent Behaviour

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_update_config_concurrent_no_exception` | `race` | Multiple threads calling `update_config()` simultaneously do not raise any exception | spawn 20 threads each calling `update_config(RuntimeConfig(target_labels=[f"label_{i}"]))` concurrently; join all threads | no exception raised by any thread |
| `test_update_config_concurrent_final_config_is_valid` | `race` | After all concurrent `update_config()` calls complete, the stored config is one of the submitted values | same as above; collect all submitted `RuntimeConfig` instances | the pipeline's internal config is `is`-identical to one of the submitted instances |
| `test_update_config_concurrent_camera_changed_event_set` | `race` | After all concurrent `update_config()` calls complete, `_camera_changed_event` is set | same as above | `pipeline._camera_changed_event.is_set() is True` immediately after all threads join |

---

## 10. Concurrency — `stop()` Interrupts Frame Loop

> **Note:** These tests start the real background thread via `pipeline.start()`. The mock
> camera's `read()` is configured to block briefly (using `time.sleep(0.05)`) to simulate
> a slow source, giving the stop signal time to arrive mid-iteration. `pipeline.stop()` is
> always called in a `finally` block.

### 10.1 Concurrent Behaviour

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_stop_from_separate_thread_joins_cleanly` | `race` | `stop()` called from a separate thread while the frame loop is running causes the background thread to exit cleanly | start pipeline; after 100 ms, call `stop()` from a new thread; join the stop thread with a 2-second timeout | stop thread joins within 2 seconds; `pipeline._thread.is_alive() is False` |
| `test_stop_interrupts_fps_throttle_wait` | `race` | `stop()` interrupts an in-progress FPS throttle wait without waiting for the full interval | configure `_last_frame_time` so the throttle wait would be ~1 second; start pipeline; call `stop()` immediately | `pipeline._thread` joins in well under 1 second (assert join completes within 200 ms) |

---

## 11. End-to-End — Recovery from Initial `DeviceNotFoundError`

> **Note:** These tests start the real background thread via `pipeline.start()`. The pipeline is
> constructed with `LocalCamera` patched to raise `DeviceNotFoundError`, so `_camera` is `None`
> at startup and the loop immediately enters the `_camera_changed_event.wait` path. The mock is
> then reconfigured to succeed before `update_config` is called. `pipeline.stop()` is always
> called in a `finally` block.

### 11.1 State Transitions

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_recovery_from_init_failure_produces_results` | `e2e` | When the pipeline starts with no camera (due to `DeviceNotFoundError` at init), calling `update_config()` with a working config causes the loop to recreate the camera and eventually publish a `PipelineResult` | construct pipeline with `LocalCamera` patched to raise `DeviceNotFoundError`; call `start()`; reconfigure the mock so `LocalCamera` succeeds and returns `mock_camera`; call `update_config(RuntimeConfig())`; drain the queue | `pipeline.get_queue().get(timeout=2)` returns a `PipelineResult` without raising `queue.Empty` |
| `test_recovery_from_init_failure_camera_changed_event_cleared` | `e2e` | After successful recovery the `_camera_changed_event` is no longer set | same setup; wait until at least one result is received | `pipeline._camera_changed_event.is_set() is False` after the first result appears on the queue |

---

## Summary Table

| Entity | Test Count (approx.) | unit | e2e | race | Key Concerns |
|---|---|---|---|---|---|
| `PipelineResult` | 6 | 6 | 0 | 0 | all fields stored, frozen |
| `DetectionPipeline.__init__` | 11 | 11 | 0 | 0 | engine/config stored, camera constructed, queue size, flags/events cleared, lock initialised, `DeviceNotFoundError` handled |
| `DetectionPipeline.start` | 5 | 0 | 5 | 0 | `_started` flag, thread spawned, double-start guard, exact error message, no extra thread on double-start |
| `DetectionPipeline.stop` | 7 | 0 | 7 | 0 | `_stop_event` set, thread joined, camera closed after join, engine not closed, idempotent, safe with no camera |
| `DetectionPipeline.update_config` | 3 | 3 | 0 | 0 | config replaced, event set, returns immediately |
| `DetectionPipeline.get_queue` | 2 | 2 | 0 | 0 | returns `queue.Queue`, same object each call |
| `DetectionPipeline._run_one_iteration` | 41 | 38 | 0 | 3 | BGR→RGB conversion, JPEG encoding failure, inference errors, camera read errors, FPS throttle boundary, queue drop-oldest, TOCTOU race on full-then-empty queue, lock/detect ordering, non-blocking queue methods |
| End-to-End — FPS cap | 1 | 0 | 1 | 0 | actual output rate ≤ 30 FPS over 1-second window |
| Concurrency — `update_config` | 3 | 0 | 0 | 3 | no exception under concurrent writes, final config is one of the submitted values, event set |
| Concurrency — `stop()` | 2 | 0 | 0 | 2 | clean join from separate thread, throttle wait interrupted by stop signal |
| End-to-End — init-failure recovery | 2 | 0 | 2 | 0 | result published after `update_config` recovery, `_camera_changed_event` cleared after first result |
