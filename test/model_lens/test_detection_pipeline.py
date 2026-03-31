# Copyright 2025 ModelLens Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for the DetectionPipeline class."""

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


# ---------------------------------------------------------------------------
# Fixtures (imported via conftest; defined in fixtures/detection_pipeline.py)
# ---------------------------------------------------------------------------


# ===========================================================================
# Section 1 — PipelineResult
# ===========================================================================


class TestPipelineResultHappyPath:
    """1.1 Happy Path — Construction."""

    @pytest.mark.unit
    def test_pipeline_result_stores_jpeg_bytes(self) -> None:
        result = PipelineResult(jpeg_bytes=b"\xff\xd8\xff", timestamp=1.0, source="local:0", detections=[])
        assert result.jpeg_bytes == b"\xff\xd8\xff"

    @pytest.mark.unit
    def test_pipeline_result_stores_timestamp(self) -> None:
        result = PipelineResult(jpeg_bytes=b"", timestamp=1748000400.123, source="local:0", detections=[])
        assert result.timestamp == 1748000400.123

    @pytest.mark.unit
    def test_pipeline_result_stores_source(self) -> None:
        result = PipelineResult(
            jpeg_bytes=b"",
            timestamp=1.0,
            source="rtsp://192.168.1.10/stream",
            detections=[],
        )
        assert result.source == "rtsp://192.168.1.10/stream"

    @pytest.mark.unit
    def test_pipeline_result_stores_detections(self) -> None:
        det = DetectionResult(label="cat", confidence=0.9, bounding_box=(0.1, 0.2, 0.4, 0.6), is_target=True)
        result = PipelineResult(jpeg_bytes=b"", timestamp=1.0, source="local:0", detections=[det])
        assert result.detections[0].label == "cat"

    @pytest.mark.unit
    def test_pipeline_result_stores_empty_detections(self) -> None:
        result = PipelineResult(jpeg_bytes=b"", timestamp=1.0, source="local:0", detections=[])
        assert result.detections == []


class TestPipelineResultImmutability:
    """1.2 Immutability."""

    @pytest.mark.unit
    def test_pipeline_result_is_frozen(self) -> None:
        result = PipelineResult(jpeg_bytes=b"\xff\xd8\xff", timestamp=1.0, source="local:0", detections=[])
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            result.jpeg_bytes = b""  # type: ignore[misc]


# ===========================================================================
# Section 2 — DetectionPipeline.__init__
# ===========================================================================


class TestPipelineInitHappyPath:
    """2.1 Happy Path — Construction."""

    @pytest.mark.unit
    def test_pipeline_init_stores_engine(self, pipeline: DetectionPipeline, mock_engine: MagicMock) -> None:
        assert pipeline._engine is mock_engine

    @pytest.mark.unit
    def test_pipeline_init_stores_initial_config(
        self, pipeline: DetectionPipeline, default_config: RuntimeConfig
    ) -> None:
        assert pipeline._config is default_config

    @pytest.mark.unit
    def test_pipeline_init_constructs_local_camera(
        self, mock_engine: MagicMock, default_config: RuntimeConfig, mock_camera: MagicMock, mocker
    ) -> None:
        local_cam_cls = mocker.patch(
            "model_lens.detection_pipeline.LocalCamera",
            return_value=mock_camera,
        )
        DetectionPipeline(engine=mock_engine, initial_config=default_config)
        local_cam_cls.assert_called_once_with(default_config.camera)

    @pytest.mark.unit
    def test_pipeline_init_constructs_rtsp_camera(
        self, mock_engine: MagicMock, mock_camera: MagicMock, mocker
    ) -> None:
        rtsp_config = RuntimeConfig(camera=RtspCameraConfig(rtsp_url="rtsp://x"))
        rtsp_cam_cls = mocker.patch(
            "model_lens.detection_pipeline.RtspCamera",
            return_value=mock_camera,
        )
        DetectionPipeline(engine=mock_engine, initial_config=rtsp_config)
        rtsp_cam_cls.assert_called_once_with(rtsp_config.camera)

    @pytest.mark.unit
    def test_pipeline_init_queue_maxsize_is_five(self, pipeline: DetectionPipeline) -> None:
        assert pipeline.get_queue().maxsize == 5

    @pytest.mark.unit
    def test_pipeline_init_started_flag_is_false(self, pipeline: DetectionPipeline) -> None:
        assert pipeline._started is False

    @pytest.mark.unit
    def test_pipeline_init_stop_event_is_clear(self, pipeline: DetectionPipeline) -> None:
        assert pipeline._stop_event.is_set() is False

    @pytest.mark.unit
    def test_pipeline_init_camera_changed_event_is_clear(self, pipeline: DetectionPipeline) -> None:
        assert pipeline._camera_changed_event.is_set() is False

    @pytest.mark.unit
    def test_pipeline_init_lock_is_created(self, pipeline: DetectionPipeline) -> None:
        assert isinstance(pipeline._config_lock, type(threading.Lock()))


class TestPipelineInitErrorPropagation:
    """2.2 Error Propagation."""

    @pytest.mark.unit
    def test_pipeline_init_device_not_found_sets_camera_to_none(
        self, mock_engine: MagicMock, default_config: RuntimeConfig, mocker
    ) -> None:
        mocker.patch(
            "model_lens.detection_pipeline.LocalCamera",
            side_effect=DeviceNotFoundError("not found"),
        )
        p = DetectionPipeline(engine=mock_engine, initial_config=default_config)
        assert p._camera is None

    @pytest.mark.unit
    def test_pipeline_init_device_not_found_logs_error(
        self, mock_engine: MagicMock, default_config: RuntimeConfig, mocker
    ) -> None:
        mocker.patch(
            "model_lens.detection_pipeline.LocalCamera",
            side_effect=DeviceNotFoundError("not found"),
        )
        with patch("model_lens.detection_pipeline.logger") as mock_logger:
            DetectionPipeline(engine=mock_engine, initial_config=default_config)
        mock_logger.error.assert_called()


# ===========================================================================
# Section 3 — DetectionPipeline.start
# ===========================================================================


class TestPipelineStartHappyPath:
    """3.1 Happy Path."""

    @pytest.mark.e2e
    def test_pipeline_start_sets_started_flag(self, pipeline: DetectionPipeline) -> None:
        try:
            pipeline.start()
            assert pipeline._started is True
        finally:
            pipeline.stop()

    @pytest.mark.e2e
    def test_pipeline_start_spawns_thread(self, pipeline: DetectionPipeline) -> None:
        try:
            pipeline.start()
            assert pipeline._thread.is_alive() is True
        finally:
            pipeline.stop()


class TestPipelineStartValidationFailures:
    """3.2 Validation Failures."""

    @pytest.mark.e2e
    def test_pipeline_start_raises_on_double_start(self, pipeline: DetectionPipeline) -> None:
        try:
            pipeline.start()
            with pytest.raises(RuntimeError):
                pipeline.start()
        finally:
            pipeline.stop()

    @pytest.mark.e2e
    def test_pipeline_start_raises_exact_message(self, pipeline: DetectionPipeline) -> None:
        try:
            pipeline.start()
            with pytest.raises(RuntimeError) as exc_info:
                pipeline.start()
            assert str(exc_info.value) == "Pipeline is already running"
        finally:
            pipeline.stop()

    @pytest.mark.e2e
    def test_pipeline_start_no_thread_spawned_on_double_start(self, pipeline: DetectionPipeline) -> None:
        try:
            pipeline.start()
            with pytest.raises(RuntimeError):
                pipeline.start()
            # Only one background thread should exist; _thread is the single one
            assert pipeline._thread.is_alive() is True
        finally:
            pipeline.stop()


# ===========================================================================
# Section 4 — DetectionPipeline.stop
# ===========================================================================


class TestPipelineStopHappyPath:
    """4.1 Happy Path."""

    @pytest.mark.e2e
    def test_pipeline_stop_sets_stop_event(self, pipeline: DetectionPipeline) -> None:
        pipeline.start()
        pipeline.stop()
        assert pipeline._stop_event.is_set() is True

    @pytest.mark.e2e
    def test_pipeline_stop_joins_thread(self, pipeline: DetectionPipeline) -> None:
        pipeline.start()
        pipeline.stop()
        assert pipeline._thread.is_alive() is False

    @pytest.mark.e2e
    def test_pipeline_stop_closes_camera(
        self, pipeline: DetectionPipeline, mock_camera: MagicMock
    ) -> None:
        pipeline.start()
        pipeline.stop()
        assert mock_camera.close.call_count >= 1

    @pytest.mark.e2e
    def test_pipeline_stop_closes_camera_after_join(
        self, pipeline: DetectionPipeline, mock_camera: MagicMock
    ) -> None:
        thread_alive_at_close: list[bool] = []

        original_close = mock_camera.close.side_effect

        def recording_close(*args, **kwargs):
            thread_alive_at_close.append(pipeline._thread.is_alive())
            if original_close:
                return original_close(*args, **kwargs)

        mock_camera.close.side_effect = recording_close

        pipeline.start()
        pipeline.stop()

        assert len(thread_alive_at_close) >= 1
        assert all(alive is False for alive in thread_alive_at_close)

    @pytest.mark.e2e
    def test_pipeline_stop_does_not_close_engine(
        self, pipeline: DetectionPipeline, mock_engine: MagicMock
    ) -> None:
        pipeline.start()
        pipeline.stop()
        assert mock_engine.close.call_count == 0


class TestPipelineStopIdempotency:
    """4.2 Idempotency."""

    @pytest.mark.e2e
    def test_pipeline_stop_is_idempotent(self, pipeline: DetectionPipeline) -> None:
        pipeline.start()
        pipeline.stop()
        pipeline.stop()  # should not raise


class TestPipelineStopNoneCamera:
    """4.3 None / Empty Input."""

    @pytest.mark.e2e
    def test_pipeline_stop_with_no_camera_does_not_raise(
        self, mock_engine: MagicMock, default_config: RuntimeConfig, mocker
    ) -> None:
        mocker.patch(
            "model_lens.detection_pipeline.LocalCamera",
            side_effect=DeviceNotFoundError("not found"),
        )
        p = DetectionPipeline(engine=mock_engine, initial_config=default_config)
        p.start()
        p.stop()  # should not raise


# ===========================================================================
# Section 5 — DetectionPipeline.update_config
# ===========================================================================


class TestUpdateConfigHappyPath:
    """5.1 Happy Path."""

    @pytest.mark.unit
    def test_update_config_replaces_runtime_config(self, pipeline: DetectionPipeline) -> None:
        new_config = RuntimeConfig(target_labels=["dog"])
        pipeline.update_config(new_config)
        assert pipeline._config is new_config

    @pytest.mark.unit
    def test_update_config_sets_camera_changed_event(self, pipeline: DetectionPipeline) -> None:
        new_config = RuntimeConfig(target_labels=["dog"])
        pipeline.update_config(new_config)
        assert pipeline._camera_changed_event.is_set() is True

    @pytest.mark.unit
    def test_update_config_returns_immediately(self, pipeline: DetectionPipeline) -> None:
        new_config = RuntimeConfig(target_labels=["dog"])
        start = time.monotonic()
        pipeline.update_config(new_config)
        elapsed = time.monotonic() - start
        assert elapsed < 0.05


# ===========================================================================
# Section 6 — DetectionPipeline.get_queue
# ===========================================================================


class TestGetQueueHappyPath:
    """6.1 Happy Path."""

    @pytest.mark.unit
    def test_get_queue_returns_queue_instance(self, pipeline: DetectionPipeline) -> None:
        assert isinstance(pipeline.get_queue(), queue.Queue)

    @pytest.mark.unit
    def test_get_queue_returns_same_object(self, pipeline: DetectionPipeline) -> None:
        q1 = pipeline.get_queue()
        q2 = pipeline.get_queue()
        assert q1 is q2


# ===========================================================================
# Section 7 — DetectionPipeline._run_one_iteration
# ===========================================================================


def _make_mock_buffer() -> MagicMock:
    buf = MagicMock()
    buf.tobytes.return_value = b"\xff\xd8\xff"
    return buf


class TestRunOneIterationHappyPath:
    """7.1 Happy Path — Full Iteration."""

    @pytest.mark.unit
    def test_run_one_iteration_reads_frame(
        self, pipeline: DetectionPipeline, mock_camera: MagicMock
    ) -> None:
        with patch("cv2.imencode", return_value=(True, _make_mock_buffer())):
            pipeline._run_one_iteration()
        assert mock_camera.read.call_count == 1

    @pytest.mark.unit
    def test_run_one_iteration_publishes_pipeline_result(self, pipeline: DetectionPipeline) -> None:
        with patch("cv2.imencode", return_value=(True, _make_mock_buffer())):
            pipeline._run_one_iteration()
        assert pipeline.get_queue().qsize() == 1

    @pytest.mark.unit
    def test_run_one_iteration_result_jpeg_bytes(self, pipeline: DetectionPipeline) -> None:
        with patch("cv2.imencode", return_value=(True, _make_mock_buffer())):
            pipeline._run_one_iteration()
        result: PipelineResult = pipeline.get_queue().get_nowait()
        assert result.jpeg_bytes == b"\xff\xd8\xff"

    @pytest.mark.unit
    def test_run_one_iteration_result_timestamp(
        self, pipeline: DetectionPipeline, mock_camera: MagicMock
    ) -> None:
        mock_camera.read.return_value = Frame(
            data=np.zeros((480, 640, 3), dtype=np.uint8),
            timestamp=1748000400.0,
            source="local:0",
        )
        with patch("cv2.imencode", return_value=(True, _make_mock_buffer())):
            pipeline._run_one_iteration()
        result: PipelineResult = pipeline.get_queue().get_nowait()
        assert result.timestamp == 1748000400.0

    @pytest.mark.unit
    def test_run_one_iteration_result_source(
        self, pipeline: DetectionPipeline, mock_camera: MagicMock
    ) -> None:
        mock_camera.read.return_value = Frame(
            data=np.zeros((480, 640, 3), dtype=np.uint8),
            timestamp=1748000400.0,
            source="local:0",
        )
        with patch("cv2.imencode", return_value=(True, _make_mock_buffer())):
            pipeline._run_one_iteration()
        result: PipelineResult = pipeline.get_queue().get_nowait()
        assert result.source == "local:0"

    @pytest.mark.unit
    def test_run_one_iteration_result_detections(
        self, pipeline: DetectionPipeline, mock_engine: MagicMock
    ) -> None:
        det = DetectionResult(label="cat", confidence=0.9, bounding_box=(0.1, 0.2, 0.4, 0.6), is_target=True)
        mock_engine.detect.return_value = [det]
        with patch("cv2.imencode", return_value=(True, _make_mock_buffer())):
            pipeline._run_one_iteration()
        result: PipelineResult = pipeline.get_queue().get_nowait()
        assert result.detections == [det]

    @pytest.mark.unit
    def test_run_one_iteration_calls_detect_with_frame_data(
        self, pipeline: DetectionPipeline, mock_engine: MagicMock, mock_camera: MagicMock
    ) -> None:
        frame = mock_camera.read.return_value
        with patch("cv2.imencode", return_value=(True, _make_mock_buffer())):
            pipeline._run_one_iteration()
        args, _ = mock_engine.detect.call_args
        assert np.array_equal(args[0], frame.data)

    @pytest.mark.unit
    def test_run_one_iteration_calls_detect_with_target_labels(
        self, mock_engine: MagicMock, mock_camera: MagicMock, mocker
    ) -> None:
        config = RuntimeConfig(target_labels=["cat"])
        mocker.patch("model_lens.detection_pipeline.LocalCamera", return_value=mock_camera)
        p = DetectionPipeline(engine=mock_engine, initial_config=config)
        with patch("cv2.imencode", return_value=(True, _make_mock_buffer())):
            p._run_one_iteration()
        args, _ = mock_engine.detect.call_args
        assert args[1] == ["cat"]


class TestRunOneIterationBgrToRgb:
    """7.2 Happy Path — BGR→RGB Conversion."""

    @pytest.mark.unit
    def test_run_one_iteration_converts_bgr_to_rgb(
        self, pipeline: DetectionPipeline, mock_camera: MagicMock
    ) -> None:
        bgr_data = np.zeros((480, 640, 3), dtype=np.uint8)
        bgr_data[:, :, 0] = 10  # B channel
        bgr_data[:, :, 1] = 20  # G channel
        bgr_data[:, :, 2] = 30  # R channel
        mock_camera.read.return_value = Frame(
            data=bgr_data,
            timestamp=1748000400.0,
            source="local:0",
        )

        captured_args: list = []

        def fake_imencode(ext, img, *args, **kwargs):
            captured_args.append(img)
            return (True, _make_mock_buffer())

        with patch("cv2.imencode", side_effect=fake_imencode):
            pipeline._run_one_iteration()

        assert len(captured_args) == 1
        encoded_img = captured_args[0]
        # Channel 0 of the encoded image should equal channel 2 of the original BGR
        assert np.array_equal(encoded_img[:, :, 0], bgr_data[:, :, 2])

    @pytest.mark.unit
    def test_run_one_iteration_does_not_modify_frame_data(
        self, pipeline: DetectionPipeline, mock_camera: MagicMock
    ) -> None:
        bgr_data = np.zeros((480, 640, 3), dtype=np.uint8)
        bgr_data[:, :, 0] = 10
        original_channel_0 = bgr_data[:, :, 0].copy()
        mock_camera.read.return_value = Frame(
            data=bgr_data,
            timestamp=1748000400.0,
            source="local:0",
        )
        with patch("cv2.imencode", return_value=(True, _make_mock_buffer())):
            pipeline._run_one_iteration()
        assert np.array_equal(bgr_data[:, :, 0], original_channel_0)


class TestRunOneIterationEncodeFailure:
    """7.3 Error Propagation — JPEG Encoding."""

    @pytest.mark.unit
    def test_run_one_iteration_skips_frame_on_encode_failure(self, pipeline: DetectionPipeline) -> None:
        with patch("cv2.imencode", return_value=(False, None)):
            pipeline._run_one_iteration()
        assert pipeline.get_queue().qsize() == 0

    @pytest.mark.unit
    def test_run_one_iteration_logs_warning_on_encode_failure(self, pipeline: DetectionPipeline) -> None:
        with patch("cv2.imencode", return_value=(False, None)):
            with patch("model_lens.detection_pipeline.logger") as mock_logger:
                pipeline._run_one_iteration()
        mock_logger.warning.assert_called()


class TestRunOneIterationInferenceErrors:
    """7.4 Error Propagation — Inference Engine."""

    @pytest.mark.unit
    def test_run_one_iteration_skips_frame_on_operation_error(
        self, pipeline: DetectionPipeline, mock_engine: MagicMock
    ) -> None:
        mock_engine.detect.side_effect = OperationError("fail")
        with patch("cv2.imencode", return_value=(True, _make_mock_buffer())):
            pipeline._run_one_iteration()
        assert pipeline.get_queue().qsize() == 0

    @pytest.mark.unit
    def test_run_one_iteration_logs_error_on_operation_error(
        self, pipeline: DetectionPipeline, mock_engine: MagicMock
    ) -> None:
        mock_engine.detect.side_effect = OperationError("fail")
        with patch("cv2.imencode", return_value=(True, _make_mock_buffer())):
            with patch("model_lens.detection_pipeline.logger") as mock_logger:
                pipeline._run_one_iteration()
        mock_logger.error.assert_called()

    @pytest.mark.unit
    def test_run_one_iteration_exits_on_parse_error(
        self, pipeline: DetectionPipeline, mock_engine: MagicMock
    ) -> None:
        mock_engine.detect.side_effect = ParseError("mismatch")
        with patch("cv2.imencode", return_value=(True, _make_mock_buffer())):
            with pytest.raises(SystemExit) as exc_info:
                pipeline._run_one_iteration()
        assert exc_info.value.code == 1

    @pytest.mark.unit
    def test_run_one_iteration_logs_critical_on_parse_error(
        self, pipeline: DetectionPipeline, mock_engine: MagicMock
    ) -> None:
        mock_engine.detect.side_effect = ParseError("mismatch")
        with patch("cv2.imencode", return_value=(True, _make_mock_buffer())):
            with patch("model_lens.detection_pipeline.logger") as mock_logger:
                with pytest.raises(SystemExit):
                    pipeline._run_one_iteration()
        mock_logger.critical.assert_called()


class TestRunOneIterationCameraErrors:
    """7.5 Error Propagation — Camera Capture."""

    @pytest.mark.unit
    def test_run_one_iteration_clears_camera_on_operation_error(
        self, pipeline: DetectionPipeline, mock_camera: MagicMock
    ) -> None:
        mock_camera.read.side_effect = OperationError("fail")
        pipeline._run_one_iteration()
        assert pipeline._camera is None

    @pytest.mark.unit
    def test_run_one_iteration_closes_camera_on_operation_error(
        self, pipeline: DetectionPipeline, mock_camera: MagicMock
    ) -> None:
        mock_camera.read.side_effect = OperationError("fail")
        pipeline._run_one_iteration()
        assert mock_camera.close.call_count == 1

    @pytest.mark.unit
    def test_run_one_iteration_logs_error_on_camera_operation_error(
        self, pipeline: DetectionPipeline, mock_camera: MagicMock
    ) -> None:
        mock_camera.read.side_effect = OperationError("fail")
        with patch("model_lens.detection_pipeline.logger") as mock_logger:
            pipeline._run_one_iteration()
        mock_logger.error.assert_called()

    @pytest.mark.unit
    def test_run_one_iteration_skips_publish_on_camera_operation_error(
        self, pipeline: DetectionPipeline, mock_camera: MagicMock
    ) -> None:
        mock_camera.read.side_effect = OperationError("fail")
        pipeline._run_one_iteration()
        assert pipeline.get_queue().qsize() == 0

    @pytest.mark.unit
    def test_run_one_iteration_camera_cleared_no_retry(
        self, pipeline: DetectionPipeline, mock_camera: MagicMock
    ) -> None:
        mock_camera.read.side_effect = OperationError("fail")
        # First call — raises OperationError, clears camera
        pipeline._run_one_iteration()
        # Second call — camera is None, should not attempt read
        pipeline._camera_changed_event.clear()  # ensure no camera recreation
        pipeline._run_one_iteration()
        assert mock_camera.read.call_count == 1


class TestRunOneIterationNoneCamera:
    """7.6 None / Empty Input."""

    @pytest.mark.unit
    def test_run_one_iteration_does_not_read_when_no_camera(
        self, pipeline: DetectionPipeline, mock_camera: MagicMock
    ) -> None:
        pipeline._camera = None
        pipeline._camera_changed_event.clear()
        with patch.object(pipeline._camera_changed_event, "wait"):
            pipeline._run_one_iteration()
        assert mock_camera.read.call_count == 0

    @pytest.mark.unit
    def test_run_one_iteration_does_not_publish_when_no_camera(
        self, pipeline: DetectionPipeline, mock_camera: MagicMock
    ) -> None:
        pipeline._camera = None
        pipeline._camera_changed_event.clear()
        with patch.object(pipeline._camera_changed_event, "wait"):
            pipeline._run_one_iteration()
        assert pipeline.get_queue().qsize() == 0

    @pytest.mark.unit
    def test_run_one_iteration_waits_on_camera_changed_event_when_no_camera(
        self, pipeline: DetectionPipeline
    ) -> None:
        pipeline._camera = None
        pipeline._camera_changed_event.clear()
        with patch.object(pipeline._camera_changed_event, "wait") as mock_wait:
            pipeline._run_one_iteration()
        mock_wait.assert_called_once_with(timeout=1.0)


class TestRunOneIterationStateTransitions:
    """7.7 State Transitions."""

    @pytest.mark.unit
    def test_run_one_iteration_recreates_local_camera_on_event(
        self, pipeline: DetectionPipeline, mock_camera: MagicMock, mocker
    ) -> None:
        new_config = RuntimeConfig(camera=LocalCameraConfig(device_index=1))
        pipeline._config = new_config
        pipeline._camera_changed_event.set()

        new_local_cam_cls = mocker.patch(
            "model_lens.detection_pipeline.LocalCamera",
            return_value=mock_camera,
        )
        with patch("cv2.imencode", return_value=(True, _make_mock_buffer())):
            pipeline._run_one_iteration()

        new_local_cam_cls.assert_called_once_with(new_config.camera)

    @pytest.mark.unit
    def test_run_one_iteration_recreates_rtsp_camera_on_event(
        self, pipeline: DetectionPipeline, mock_camera: MagicMock, mocker
    ) -> None:
        new_config = RuntimeConfig(camera=RtspCameraConfig(rtsp_url="rtsp://new"))
        pipeline._config = new_config
        pipeline._camera_changed_event.set()

        new_rtsp_cam_cls = mocker.patch(
            "model_lens.detection_pipeline.RtspCamera",
            return_value=mock_camera,
        )
        with patch("cv2.imencode", return_value=(True, _make_mock_buffer())):
            pipeline._run_one_iteration()

        new_rtsp_cam_cls.assert_called_once_with(new_config.camera)

    @pytest.mark.unit
    def test_run_one_iteration_closes_old_camera_before_recreating(
        self, pipeline: DetectionPipeline, mock_camera: MagicMock, mocker
    ) -> None:
        old_camera = MagicMock()
        pipeline._camera = old_camera

        new_config = RuntimeConfig(camera=LocalCameraConfig(device_index=1))
        pipeline._config = new_config
        pipeline._camera_changed_event.set()

        call_order: list[str] = []
        old_camera.close.side_effect = lambda: call_order.append("close")

        new_cam = MagicMock()
        new_cam.read.return_value = Frame(
            data=np.zeros((480, 640, 3), dtype=np.uint8),
            timestamp=1748000400.0,
            source="local:1",
        )

        def fake_local_camera(cfg):
            call_order.append("construct")
            return new_cam

        mocker.patch("model_lens.detection_pipeline.LocalCamera", side_effect=fake_local_camera)
        with patch("cv2.imencode", return_value=(True, _make_mock_buffer())):
            pipeline._run_one_iteration()

        assert call_order.index("close") < call_order.index("construct")

    @pytest.mark.unit
    def test_run_one_iteration_clears_camera_changed_event_after_handling(
        self, pipeline: DetectionPipeline, mock_camera: MagicMock, mocker
    ) -> None:
        pipeline._camera_changed_event.set()
        mocker.patch("model_lens.detection_pipeline.LocalCamera", return_value=mock_camera)
        with patch("cv2.imencode", return_value=(True, _make_mock_buffer())):
            pipeline._run_one_iteration()
        assert pipeline._camera_changed_event.is_set() is False

    @pytest.mark.unit
    def test_run_one_iteration_sets_camera_to_none_on_device_not_found(
        self, pipeline: DetectionPipeline, mocker
    ) -> None:
        pipeline._camera_changed_event.set()
        mocker.patch(
            "model_lens.detection_pipeline.LocalCamera",
            side_effect=DeviceNotFoundError("gone"),
        )
        pipeline._run_one_iteration()
        assert pipeline._camera is None

    @pytest.mark.unit
    def test_run_one_iteration_logs_error_on_device_not_found_in_loop(
        self, pipeline: DetectionPipeline, mocker
    ) -> None:
        pipeline._camera_changed_event.set()
        mocker.patch(
            "model_lens.detection_pipeline.LocalCamera",
            side_effect=DeviceNotFoundError("gone"),
        )
        with patch("model_lens.detection_pipeline.logger") as mock_logger:
            pipeline._run_one_iteration()
        mock_logger.error.assert_called()


class TestRunOneIterationQueueCapacity:
    """7.8 Boundary Values — queue capacity."""

    @pytest.mark.unit
    def test_run_one_iteration_drops_oldest_when_queue_full(
        self, pipeline: DetectionPipeline
    ) -> None:
        q = pipeline.get_queue()
        sentinel = object()
        for _ in range(5):
            q.put_nowait(sentinel)

        with patch("cv2.imencode", return_value=(True, _make_mock_buffer())):
            pipeline._run_one_iteration()

        assert q.qsize() == 5
        items = []
        while not q.empty():
            items.append(q.get_nowait())
        # The oldest sentinel should have been dropped; the newest item is a PipelineResult
        assert isinstance(items[-1], PipelineResult)
        # At most 4 sentinels remain (one was dropped)
        sentinel_count = sum(1 for i in items if i is sentinel)
        assert sentinel_count == 4

    @pytest.mark.unit
    def test_run_one_iteration_logs_debug_on_drop(self, pipeline: DetectionPipeline) -> None:
        q = pipeline.get_queue()
        for _ in range(5):
            q.put_nowait(object())

        with patch("cv2.imencode", return_value=(True, _make_mock_buffer())):
            with patch("model_lens.detection_pipeline.logger") as mock_logger:
                pipeline._run_one_iteration()
        mock_logger.debug.assert_called()

    @pytest.mark.race
    def test_run_one_iteration_publishes_when_queue_drained_between_full_check_and_get(
        self, pipeline: DetectionPipeline
    ) -> None:
        q = pipeline.get_queue()
        # Queue is actually empty, but full() reports True (TOCTOU race).
        with patch.object(q, "full", side_effect=[True, False]):
            with patch("cv2.imencode", return_value=(True, _make_mock_buffer())):
                pipeline._run_one_iteration()

        assert q.qsize() == 1
        assert isinstance(q.get_nowait(), PipelineResult)


class TestRunOneIterationFpsThrottle:
    """7.9 Boundary Values — FPS throttle."""

    @pytest.mark.unit
    def test_run_one_iteration_throttle_waits_when_too_fast(
        self, pipeline: DetectionPipeline
    ) -> None:
        elapsed_s = 0.010  # 10 ms
        now = 1000.0
        pipeline._last_frame_time = now - elapsed_s

        with patch("time.monotonic", return_value=now):
            with patch.object(pipeline._stop_event, "wait") as mock_wait:
                with patch("cv2.imencode", return_value=(True, _make_mock_buffer())):
                    pipeline._run_one_iteration()

        expected_timeout = 1 / 30 - elapsed_s
        mock_wait.assert_called_once()
        actual_timeout = mock_wait.call_args[1].get("timeout") or mock_wait.call_args[0][0]
        assert actual_timeout == pytest.approx(expected_timeout, abs=5e-3)

    @pytest.mark.unit
    def test_run_one_iteration_no_wait_when_already_slow(
        self, pipeline: DetectionPipeline
    ) -> None:
        elapsed_s = 0.040  # 40 ms > 1/30 s
        now = 1000.0
        pipeline._last_frame_time = now - elapsed_s

        with patch("time.monotonic", return_value=now):
            with patch.object(pipeline._stop_event, "wait") as mock_wait:
                with patch("cv2.imencode", return_value=(True, _make_mock_buffer())):
                    pipeline._run_one_iteration()

        # Either not called, or called with timeout <= 0
        if mock_wait.called:
            actual_timeout = mock_wait.call_args[1].get("timeout") or mock_wait.call_args[0][0]
            assert actual_timeout <= 0

    @pytest.mark.unit
    def test_run_one_iteration_no_throttle_on_first_frame(
        self, pipeline: DetectionPipeline
    ) -> None:
        pipeline._last_frame_time = 0

        with patch.object(pipeline._stop_event, "wait") as mock_wait:
            with patch("cv2.imencode", return_value=(True, _make_mock_buffer())):
                pipeline._run_one_iteration()

        mock_wait.assert_not_called()

    @pytest.mark.unit
    def test_run_one_iteration_updates_last_frame_time_after_publish(
        self, pipeline: DetectionPipeline
    ) -> None:
        fixed_time = 9999.0
        with patch("time.monotonic", return_value=fixed_time):
            with patch("cv2.imencode", return_value=(True, _make_mock_buffer())):
                pipeline._run_one_iteration()
        assert pipeline._last_frame_time == fixed_time


class TestRunOneIterationConcurrentLock:
    """7.10 Concurrent Behaviour — lock acquisition."""

    @pytest.mark.race
    def test_run_one_iteration_releases_lock_before_detect(
        self, pipeline: DetectionPipeline, mock_engine: MagicMock
    ) -> None:
        call_order: list[str] = []

        # threading.Lock is a C extension type whose methods are read-only,
        # so we replace the entire lock with a MagicMock that wraps it.
        real_lock = pipeline._config_lock
        mock_lock = MagicMock(wraps=real_lock)
        mock_lock.release = MagicMock(side_effect=lambda: (call_order.append("release"), real_lock.release())[-1])
        mock_lock.acquire = MagicMock(side_effect=lambda *a, **kw: real_lock.acquire(*a, **kw))
        mock_lock.__enter__ = MagicMock(side_effect=lambda: real_lock.__enter__())
        mock_lock.__exit__ = MagicMock(side_effect=lambda *a: (call_order.append("release"), real_lock.__exit__(*a))[-1])
        pipeline._config_lock = mock_lock

        mock_engine.detect.side_effect = lambda *a, **kw: call_order.append("detect") or []

        with patch("cv2.imencode", return_value=(True, _make_mock_buffer())):
            pipeline._run_one_iteration()

        assert "release" in call_order
        assert "detect" in call_order
        assert call_order.index("release") < call_order.index("detect")

    @pytest.mark.race
    def test_run_one_iteration_detect_called_without_lock(
        self, pipeline: DetectionPipeline, mock_engine: MagicMock
    ) -> None:
        lock = pipeline._config_lock

        def assert_not_locked(*args, **kwargs):
            assert not lock.locked(), "Lock must not be held during engine.detect()"
            return []

        mock_engine.detect.side_effect = assert_not_locked

        with patch("cv2.imencode", return_value=(True, _make_mock_buffer())):
            pipeline._run_one_iteration()


class TestRunOneIterationNonBlockingQueue:
    """7.11 Happy Path — queue method calls."""

    @pytest.mark.unit
    def test_run_one_iteration_uses_put_nowait(self, pipeline: DetectionPipeline) -> None:
        q = pipeline.get_queue()
        # Note: Queue.put_nowait() internally delegates to put(), so we cannot
        # mock put() without breaking put_nowait(). Instead, just verify that
        # put_nowait was the entry point used by the production code.
        with patch.object(q, "put_nowait", wraps=q.put_nowait) as mock_put_nowait:
            with patch("cv2.imencode", return_value=(True, _make_mock_buffer())):
                pipeline._run_one_iteration()
        mock_put_nowait.assert_called_once()

    @pytest.mark.unit
    def test_run_one_iteration_uses_get_nowait_on_full_queue(self, pipeline: DetectionPipeline) -> None:
        q = pipeline.get_queue()
        for _ in range(5):
            q.put_nowait(object())

        # Note: Queue.get_nowait() internally delegates to get(), so we cannot
        # mock get() without preventing actual item removal (causing queue.Full).
        # Instead, just verify that get_nowait was the entry point used.
        with patch.object(q, "get_nowait", wraps=q.get_nowait) as mock_get_nowait:
            with patch("cv2.imencode", return_value=(True, _make_mock_buffer())):
                pipeline._run_one_iteration()
        mock_get_nowait.assert_called_once()


# ===========================================================================
# Section 8 — End-to-End: FPS Cap
# ===========================================================================


class TestFpsCap:
    """8.1 Boundary Values — output rate."""

    @pytest.mark.e2e
    def test_fps_cap_output_rate_does_not_exceed_30(
        self, pipeline: DetectionPipeline
    ) -> None:
        results_received: list[PipelineResult] = []
        stop_consumer = threading.Event()

        def consumer() -> None:
            q = pipeline.get_queue()
            while not stop_consumer.is_set():
                try:
                    item = q.get(timeout=0.05)
                    results_received.append(item)
                except queue.Empty:
                    pass

        consumer_thread = threading.Thread(target=consumer, daemon=True)
        consumer_thread.start()

        try:
            pipeline.start()
            time.sleep(1.0)
        finally:
            pipeline.stop()
            stop_consumer.set()
            consumer_thread.join(timeout=2.0)

        assert len(results_received) <= 32


# ===========================================================================
# Section 9 — Concurrency: update_config Stress Test
# ===========================================================================


class TestUpdateConfigConcurrent:
    """9.1 Concurrent Behaviour."""

    @pytest.mark.race
    def test_update_config_concurrent_no_exception(self, pipeline: DetectionPipeline) -> None:
        configs = [RuntimeConfig(target_labels=[f"label_{i}"]) for i in range(20)]
        exceptions: list[Exception] = []

        def worker(cfg: RuntimeConfig) -> None:
            try:
                pipeline.update_config(cfg)
            except Exception as exc:  # noqa: BLE001
                exceptions.append(exc)

        try:
            pipeline.start()
            threads = [threading.Thread(target=worker, args=(cfg,)) for cfg in configs]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=5.0)
        finally:
            pipeline.stop()

        assert exceptions == []

    @pytest.mark.race
    def test_update_config_concurrent_final_config_is_valid(self, pipeline: DetectionPipeline) -> None:
        configs = [RuntimeConfig(target_labels=[f"label_{i}"]) for i in range(20)]

        def worker(cfg: RuntimeConfig) -> None:
            pipeline.update_config(cfg)

        try:
            pipeline.start()
            threads = [threading.Thread(target=worker, args=(cfg,)) for cfg in configs]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=5.0)
        finally:
            pipeline.stop()

        assert any(pipeline._config is cfg for cfg in configs)

    @pytest.mark.race
    def test_update_config_concurrent_camera_changed_event_set(
        self, pipeline: DetectionPipeline
    ) -> None:
        configs = [RuntimeConfig(target_labels=[f"label_{i}"]) for i in range(20)]

        def worker(cfg: RuntimeConfig) -> None:
            pipeline.update_config(cfg)

        try:
            pipeline.start()
            threads = [threading.Thread(target=worker, args=(cfg,)) for cfg in configs]
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=5.0)
        finally:
            pipeline.stop()

        assert pipeline._camera_changed_event.is_set() is True


# ===========================================================================
# Section 10 — Concurrency: stop() Interrupts Frame Loop
# ===========================================================================


class TestStopInterruptsFrameLoop:
    """10.1 Concurrent Behaviour."""

    @pytest.mark.race
    def test_stop_from_separate_thread_joins_cleanly(self, pipeline: DetectionPipeline) -> None:
        pipeline.start()
        time.sleep(0.1)

        stop_thread = threading.Thread(target=pipeline.stop)
        stop_thread.start()
        stop_thread.join(timeout=2.0)

        assert not stop_thread.is_alive()
        assert pipeline._thread.is_alive() is False

    @pytest.mark.race
    def test_stop_interrupts_fps_throttle_wait(
        self, pipeline: DetectionPipeline, mock_camera: MagicMock
    ) -> None:
        # Make camera read block briefly to simulate slow source
        original_read = mock_camera.read.side_effect

        def slow_read():
            time.sleep(0.05)
            return Frame(
                data=np.zeros((480, 640, 3), dtype=np.uint8),
                timestamp=time.monotonic(),
                source="local:0",
            )

        mock_camera.read.side_effect = slow_read

        # Set _last_frame_time so the throttle wait would be ~1 second
        pipeline._last_frame_time = time.monotonic()

        with patch("cv2.imencode", return_value=(True, _make_mock_buffer())):
            pipeline.start()
            start = time.monotonic()
            pipeline.stop()
            elapsed = time.monotonic() - start

        assert elapsed < 0.2


# ===========================================================================
# Section 11 — End-to-End: Recovery from Initial DeviceNotFoundError
# ===========================================================================


class TestRecoveryFromInitFailure:
    """11.1 State Transitions."""

    @pytest.mark.e2e
    def test_recovery_from_init_failure_produces_results(
        self, mock_engine: MagicMock, default_config: RuntimeConfig, mocker
    ) -> None:
        mock_camera = mocker.MagicMock()
        mock_camera.read.return_value = Frame(
            data=np.zeros((480, 640, 3), dtype=np.uint8),
            timestamp=1748000400.0,
            source="local:0",
        )

        local_cam_cls = mocker.patch(
            "model_lens.detection_pipeline.LocalCamera",
            side_effect=DeviceNotFoundError("not found"),
        )

        p = DetectionPipeline(engine=mock_engine, initial_config=default_config)
        assert p._camera is None

        # Reconfigure mock so LocalCamera now succeeds
        local_cam_cls.side_effect = None
        local_cam_cls.return_value = mock_camera

        try:
            p.start()
            with patch("cv2.imencode", return_value=(True, _make_mock_buffer())):
                p.update_config(RuntimeConfig())
                result = p.get_queue().get(timeout=2.0)
        finally:
            p.stop()

        assert isinstance(result, PipelineResult)

    @pytest.mark.e2e
    def test_recovery_from_init_failure_camera_changed_event_cleared(
        self, mock_engine: MagicMock, default_config: RuntimeConfig, mocker
    ) -> None:
        mock_camera = mocker.MagicMock()
        mock_camera.read.return_value = Frame(
            data=np.zeros((480, 640, 3), dtype=np.uint8),
            timestamp=1748000400.0,
            source="local:0",
        )

        local_cam_cls = mocker.patch(
            "model_lens.detection_pipeline.LocalCamera",
            side_effect=DeviceNotFoundError("not found"),
        )

        p = DetectionPipeline(engine=mock_engine, initial_config=default_config)

        local_cam_cls.side_effect = None
        local_cam_cls.return_value = mock_camera

        try:
            p.start()
            with patch("cv2.imencode", return_value=(True, _make_mock_buffer())):
                p.update_config(RuntimeConfig())
                p.get_queue().get(timeout=2.0)  # wait for first result
                # Give the loop a moment to clear the event
                time.sleep(0.1)
        finally:
            p.stop()

        assert p._camera_changed_event.is_set() is False
