# Test Specification: `detection_pipeline`

## Source File Under Test
`src/model_lens/detection_pipeline.py`

## Test File
`tests/model_lens/test_detection_pipeline.py`

---

## `PipelineResult`

### Immutability

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_pipeline_result_is_frozen` | `unit` | Assigning to a field on PipelineResult raises. | Create a `PipelineResult` instance with valid fields. | Attempt `result.jpeg_bytes = b"new"` | Raises `FrozenInstanceError` (or `dataclasses.FrozenInstanceError`) |

### Happy Path — Construction

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_pipeline_result_stores_all_fields` | `unit` | All fields are stored correctly on construction. | | `PipelineResult(jpeg_bytes=b"\xff\xd8", timestamp=1.0, source="local:0", detections=[])` | `result.jpeg_bytes == b"\xff\xd8"`, `result.timestamp == 1.0`, `result.source == "local:0"`, `result.detections == []` |
| `test_pipeline_result_stores_detections_list` | `unit` | Detections list with items is preserved. | Create a mock `DetectionResult` instance. | `PipelineResult(jpeg_bytes=b"img", timestamp=2.0, source="rtsp:x", detections=[mock_detection])` | `result.detections == [mock_detection]` |

---

## `DetectionPipeline`

### Happy Path — Construction

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_construction_stores_engine_reference` | `unit` | Engine reference is stored. | Create a mock `InferenceEngine`. Create a valid `RuntimeConfig` with `LocalCameraConfig`. Mock `LocalCamera` constructor to return a fake camera. | `DetectionPipeline(engine=mock_engine, initial_config=config)` | `pipeline._engine is mock_engine` |
| `test_construction_stores_initial_config` | `unit` | Initial config is stored as current config. | Create a mock `InferenceEngine`. Create a valid `RuntimeConfig`. Mock camera construction to succeed. | `DetectionPipeline(engine=mock_engine, initial_config=config)` | `pipeline.get_config() is config` |
| `test_construction_creates_queue_with_maxsize_5` | `unit` | Result queue is created with maxsize=5. | Create a mock `InferenceEngine`. Create a valid `RuntimeConfig`. Mock camera construction to succeed. | `DetectionPipeline(engine=mock_engine, initial_config=config)` | `pipeline.get_queue().maxsize == 5` |
| `test_construction_thread_is_daemon` | `unit` | Background thread is created as daemon. | Create a mock `InferenceEngine`. Create a valid `RuntimeConfig`. Mock camera construction to succeed. | `DetectionPipeline(engine=mock_engine, initial_config=config)` | `pipeline._thread.daemon is True` |
| `test_construction_thread_not_started` | `unit` | Thread is not started during construction. | Create a mock `InferenceEngine`. Create a valid `RuntimeConfig`. Mock camera construction to succeed. | `DetectionPipeline(engine=mock_engine, initial_config=config)` | `pipeline._thread.is_alive() is False` |
| `test_construction_builds_local_camera` | `unit` | LocalCamera is constructed when config has LocalCameraConfig. | Create a mock `InferenceEngine`. Create `RuntimeConfig` with `LocalCameraConfig`. Mock `LocalCamera` constructor to return a fake camera. | `DetectionPipeline(engine=mock_engine, initial_config=config)` | `LocalCamera` called with the `LocalCameraConfig` instance; `pipeline._camera` is the fake camera |
| `test_construction_builds_rtsp_camera` | `unit` | RtspCamera is constructed when config has RtspCameraConfig. | Create a mock `InferenceEngine`. Create `RuntimeConfig` with `RtspCameraConfig`. Mock `RtspCamera` constructor to return a fake camera. | `DetectionPipeline(engine=mock_engine, initial_config=config)` | `RtspCamera` called with the `RtspCameraConfig` instance; `pipeline._camera` is the fake camera |
| `test_construction_camera_unavailable_sets_none` | `unit` | DeviceNotFoundError during camera build leaves _camera as None. | Create a mock `InferenceEngine`. Create a valid `RuntimeConfig` with `LocalCameraConfig`. Mock `LocalCamera` constructor to raise `DeviceNotFoundError`. | `DetectionPipeline(engine=mock_engine, initial_config=config)` | Pipeline constructed without error; `pipeline._camera is None` |
| `test_construction_unrecognised_camera_type_sets_none` | `unit` | Unrecognised camera config type leaves _camera as None. | Create a mock `InferenceEngine`. Create `RuntimeConfig` with camera field set to an unsupported type (e.g., a plain object). | `DetectionPipeline(engine=mock_engine, initial_config=config)` | Pipeline constructed without error; `pipeline._camera is None` |

### Happy Path — start

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_start_spawns_thread` | `unit` | start() begins the background thread. | Construct pipeline with mock engine and config. Mock camera construction to succeed. Patch `_run` to set `_stop_event` immediately (so thread exits quickly). | `pipeline.start()` | Thread is alive (or was alive); no exception raised |

### Validation Failures

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_start_called_twice_raises_runtime_error` | `unit` | Double start raises RuntimeError. | Construct pipeline. Patch `_run` to exit immediately. Call `pipeline.start()` once. | `pipeline.start()` (second call) | Raises `RuntimeError` with message containing "already running" |

### Happy Path — stop

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_stop_sets_stop_event` | `unit` | stop() sets the stop event. | Construct pipeline. Patch `_run` to wait on `_stop_event`. Call `pipeline.start()`. | `pipeline.stop()` | `pipeline._stop_event.is_set() is True` |
| `test_stop_joins_thread` | `unit` | stop() joins the background thread. | Construct pipeline. Patch `_run` to exit when `_stop_event` is set. Call `pipeline.start()`. | `pipeline.stop()` | `pipeline._thread.is_alive() is False` |
| `test_stop_closes_camera` | `unit` | stop() closes the camera after thread exits. | Construct pipeline with mock camera. Patch `_run` to exit when `_stop_event` is set. Call `pipeline.start()`. | `pipeline.stop()` | `mock_camera.close()` called once |
| `test_stop_does_not_call_engine_teardown` | `unit` | stop() never calls engine.teardown(). | Construct pipeline with mock engine. Patch `_run` to exit when `_stop_event` is set. Call `pipeline.start()`. | `pipeline.stop()` | `mock_engine.teardown` not called |

### Idempotency

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_stop_idempotent` | `unit` | Calling stop() multiple times does not raise. | Construct pipeline. Patch `_run` to exit when `_stop_event` is set. Call `pipeline.start()`. Call `pipeline.stop()` once. | `pipeline.stop()` (second call) | No exception raised |
| `test_stop_with_no_camera_does_not_raise` | `unit` | stop() with _camera=None does not raise. | Construct pipeline with camera construction failing (`DeviceNotFoundError`). Patch `_run` to exit when `_stop_event` is set. Call `pipeline.start()`. | `pipeline.stop()` | No exception raised |

### Happy Path — update_config

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_update_config_replaces_config` | `unit` | update_config stores new config. | Construct pipeline with initial config A. | `pipeline.update_config(config_b)` | `pipeline.get_config() is config_b` |
| `test_update_config_sets_camera_changed_event` | `unit` | update_config signals camera change. | Construct pipeline. | `pipeline.update_config(new_config)` | `pipeline._camera_changed_event.is_set() is True` |
| `test_update_config_returns_immediately` | `unit` | update_config does not block on camera recreation. | Construct pipeline. Do not start the thread. | `pipeline.update_config(new_config)` | Returns without blocking; `pipeline._camera` unchanged until loop runs |

### Happy Path — get_config

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_get_config_returns_current_config` | `unit` | get_config returns stored config. | Construct pipeline with config. | `pipeline.get_config()` | Returns the same config object stored during construction |

### Happy Path — get_queue

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_get_queue_returns_queue_instance` | `unit` | get_queue returns the internal queue. | Construct pipeline. | `pipeline.get_queue()` | Returns a `queue.Queue` instance with `maxsize == 5` |

### Happy Path — _build_camera

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_build_camera_local_config` | `unit` | Builds LocalCamera for LocalCameraConfig. | Mock `LocalCamera` constructor. Create `RuntimeConfig` with `LocalCameraConfig`. | Call `pipeline._build_camera(config)` | `LocalCamera` called with `config.camera`; returns the camera instance |
| `test_build_camera_rtsp_config` | `unit` | Builds RtspCamera for RtspCameraConfig. | Mock `RtspCamera` constructor. Create `RuntimeConfig` with `RtspCameraConfig`. | Call `pipeline._build_camera(config)` | `RtspCamera` called with `config.camera`; returns the camera instance |
| `test_build_camera_unrecognised_type_returns_none` | `unit` | Returns None for unrecognised camera config. | Create `RuntimeConfig` with an unsupported camera config type. | Call `pipeline._build_camera(config)` | Returns `None` |
| `test_build_camera_device_not_found_returns_none` | `unit` | Returns None when DeviceNotFoundError raised. | Mock `LocalCamera` constructor to raise `DeviceNotFoundError`. Create `RuntimeConfig` with `LocalCameraConfig`. | Call `pipeline._build_camera(config)` | Returns `None` |

### Happy Path — _run_one_iteration

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_iteration_reads_frame_and_publishes_result` | `unit` | Full happy-path iteration produces a PipelineResult on the queue. | Construct pipeline with mock camera and mock engine. Mock `camera.read()` to return a `Frame(data=numpy_bgr, timestamp=1.0, source="local:0")`. Mock `cv2.imencode` to return `(True, numpy_buffer)` where `numpy_buffer.tobytes()` returns `b"\xff\xd8"`. Mock `engine.detect()` to return `[mock_detection]`. Patch `time.monotonic` to return a fixed value. | Call `pipeline._run_one_iteration()` | Queue contains one `PipelineResult` with `jpeg_bytes == b"\xff\xd8"`, `timestamp == 1.0`, `source == "local:0"`, `detections == [mock_detection]` |
| `test_iteration_calls_detect_with_frame_data_and_target_labels` | `unit` | Inference is called with frame.data and target_labels from config. | Construct pipeline with config containing `target_labels=["person", "car"]`. Mock camera to return a frame. Mock `cv2.imencode` to succeed. | Call `pipeline._run_one_iteration()` | `engine.detect` called with `(frame.data, ["person", "car"])` |

### State Transitions

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_camera_changed_event_triggers_rebuild` | `unit` | When camera_changed_event is set, existing camera is closed and new one built. | Construct pipeline with mock camera (camera_A). Set `_camera_changed_event`. Update config to a new config (camera_B config). Mock camera constructors to return camera_B. | Call `pipeline._run_one_iteration()` | `camera_A.close()` called; new camera constructed; `pipeline._camera` is camera_B |
| `test_no_camera_waits_for_event` | `unit` | When _camera is None, iteration waits on _camera_changed_event. | Construct pipeline with `_camera = None`. Mock `_camera_changed_event.wait` to track the call. | Call `pipeline._run_one_iteration()` | `_camera_changed_event.wait(timeout=1.0)` called; iteration returns without publishing |

### Error Propagation

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_camera_read_operation_error_closes_camera` | `unit` | OperationError from camera.read() closes and discards camera. | Construct pipeline with mock camera. Mock `camera.read()` to raise `OperationError`. | Call `pipeline._run_one_iteration()` | `camera.close()` called; `pipeline._camera is None`; no item on queue |
| `test_imencode_failure_skips_frame` | `unit` | cv2.imencode returning False skips the frame. | Construct pipeline with mock camera returning a valid frame. Mock `cv2.imencode` to return `(False, None)`. | Call `pipeline._run_one_iteration()` | No item on queue; `engine.detect` not called |
| `test_detect_operation_error_skips_frame` | `unit` | OperationError from engine.detect() skips the frame. | Construct pipeline with mock camera returning a frame. Mock `cv2.imencode` to succeed. Mock `engine.detect()` to raise `OperationError`. | Call `pipeline._run_one_iteration()` | No item on queue; camera NOT closed |
| `test_detect_parse_error_triggers_shutdown` | `unit` | ParseError from engine.detect() sets stop event and sends SIGINT. | Construct pipeline with mock camera returning a frame. Mock `cv2.imencode` to succeed. Mock `engine.detect()` to raise `ParseError`. Patch `os.kill` to record calls. Patch `os.getpid` to return a known PID. | Call `pipeline._run_one_iteration()` | `pipeline._stop_event.is_set() is True`; `os.kill` called with `(known_pid, signal.SIGINT)` |
| `test_detect_parse_error_does_not_call_engine_teardown` | `unit` | ParseError handling does not call engine.teardown(). | Same setup as `test_detect_parse_error_triggers_shutdown`. | Call `pipeline._run_one_iteration()` | `mock_engine.teardown` not called |

### Happy Path — Queue Publish

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_publish_drops_oldest_when_queue_full` | `unit` | When queue is full, oldest item is dropped before new publish. | Construct pipeline. Fill queue to capacity (5 items). Mock camera, imencode, and engine to produce a new result. Patch `time.monotonic`. | Call `pipeline._run_one_iteration()` | Queue still has 5 items; the oldest item is no longer present; the new result is the newest item |
| `test_publish_updates_last_frame_time` | `unit` | _last_frame_time is updated after successful publish. | Construct pipeline. Mock camera, imencode, and engine to produce a result. Patch `time.monotonic` to return `99.5`. | Call `pipeline._run_one_iteration()` | `pipeline._last_frame_time == 99.5` |
| `test_skipped_frame_does_not_update_last_frame_time` | `unit` | _last_frame_time is NOT updated when frame is skipped. | Construct pipeline with `_last_frame_time = 10.0`. Mock `cv2.imencode` to return `(False, None)`. | Call `pipeline._run_one_iteration()` | `pipeline._last_frame_time == 10.0` (unchanged) |

### Happy Path — FPS Throttle

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_first_frame_not_throttled` | `unit` | First frame is never throttled (_last_frame_time == 0.0). | Construct pipeline with `_last_frame_time = 0.0`. Mock camera, imencode, engine to produce a result. Patch `time.monotonic` to return `100.0`. Spy on `_stop_event.wait`. | Call `pipeline._run_one_iteration()` | `_stop_event.wait` NOT called with a throttle timeout; result published |
| `test_throttle_waits_when_frames_too_fast` | `unit` | Throttle applies interruptible wait when elapsed < 1/30. | Construct pipeline with `_last_frame_time = 100.0`. Patch `time.monotonic` to return `100.01` (only 10ms elapsed, less than ~33.3ms). Mock camera, imencode, engine to produce a result. Spy on `_stop_event.wait`. | Call `pipeline._run_one_iteration()` | `_stop_event.wait` called with timeout approximately `0.0233` (1/30 - 0.01) |
| `test_throttle_skipped_when_frames_slow` | `unit` | No throttle when elapsed >= 1/30. | Construct pipeline with `_last_frame_time = 100.0`. Patch `time.monotonic` to return `100.05` (50ms elapsed, more than ~33.3ms). Mock camera, imencode, engine to produce a result. Spy on `_stop_event.wait`. | Call `pipeline._run_one_iteration()` | `_stop_event.wait` NOT called for throttle; result published |
| `test_throttle_interrupted_by_stop_event` | `unit` | If stop_event set during throttle wait, iteration returns without reading. | Construct pipeline with `_last_frame_time = 100.0`. Patch `time.monotonic` to return `100.01`. Configure `_stop_event.wait` to set `_stop_event` (simulating stop during wait). | Call `pipeline._run_one_iteration()` | Returns without calling `camera.read()`; no item on queue |

### Concurrent Behaviour

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_update_config_thread_safe` | `unit` | Concurrent update_config and get_config do not corrupt state. | Construct pipeline. Launch multiple threads: some calling `update_config(config_N)`, others calling `get_config()`. Use a `threading.Barrier` to synchronise start. | Run all threads concurrently | No exceptions raised; `get_config()` always returns a valid `RuntimeConfig` instance |
| `test_update_config_unblocks_camera_wait` | `unit` | update_config unblocks _camera_changed_event.wait in the loop. | Construct pipeline with `_camera = None`. Start the pipeline. After a brief moment, call `update_config(new_config)` with a valid camera config. Mock camera construction to succeed. | `pipeline.update_config(new_config)` from another thread | Pipeline picks up new config and builds camera; subsequent iteration publishes a result |

### Mock / Dependency Interaction

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_camera_close_called_on_config_change` | `unit` | Old camera is closed when camera_changed_event fires. | Construct pipeline with mock camera_A. Set `_camera_changed_event`. Provide new config. Mock new camera construction. | Call `pipeline._run_one_iteration()` | `camera_A.close()` called exactly once |
| `test_imencode_called_with_jpg_and_frame_data` | `unit` | cv2.imencode is called with ".jpg" and the frame data. | Construct pipeline with mock camera returning `Frame(data=fake_bgr)`. Mock `cv2.imencode`. | Call `pipeline._run_one_iteration()` | `cv2.imencode` called with `(".jpg", fake_bgr)` |
| `test_engine_detect_not_called_when_imencode_fails` | `unit` | Engine.detect is not called if imencode fails. | Construct pipeline. Mock `cv2.imencode` to return `(False, None)`. | Call `pipeline._run_one_iteration()` | `engine.detect` not called |
| `test_stop_event_set_before_sigint_on_parse_error` | `unit` | _stop_event is set before os.kill is called on ParseError. | Construct pipeline. Mock `engine.detect()` to raise `ParseError`. Patch `os.kill` to record call order relative to `_stop_event.is_set()`. | Call `pipeline._run_one_iteration()` | At the time `os.kill` is called, `_stop_event.is_set()` is already `True` |
