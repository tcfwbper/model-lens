"""Tests for model_lens.detection_pipeline module.

Covers PipelineResult entity and DetectionPipeline class lifecycle, camera
construction, frame iteration, FPS throttling, queue publish, error propagation,
and concurrent behaviour.
"""

from __future__ import annotations

import queue
import signal
import threading
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import numpy as np
import pytest

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# Production module gate — all tests skip until detection_pipeline.py exists.
detection_pipeline_mod = pytest.importorskip(
    "model_lens.detection_pipeline",
    reason="Production module model_lens.detection_pipeline not yet implemented",
)

from model_lens.detection_pipeline import (  # noqa: E402
    DetectionPipeline,
    PipelineResult,
)
from model_lens.entities import (  # noqa: E402
    DetectionResult,
    Frame,
    LocalCameraConfig,
    RtspCameraConfig,
    RuntimeConfig,
)
from model_lens.exceptions import (  # noqa: E402
    DeviceNotFoundError,
    OperationError,
    ParseError,
)


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_engine() -> MagicMock:
    """Create a mock InferenceEngine with detect() and teardown() methods."""
    engine = MagicMock()
    engine.detect.return_value = []
    return engine


@pytest.fixture()
def local_config() -> RuntimeConfig:
    """Create a RuntimeConfig with a default LocalCameraConfig."""
    return RuntimeConfig(
        camera=LocalCameraConfig(device_index=0),
        target_labels=["person"],
        confidence_threshold=0.5,
    )


@pytest.fixture()
def rtsp_config() -> RuntimeConfig:
    """Create a RuntimeConfig with an RtspCameraConfig."""
    return RuntimeConfig(
        camera=RtspCameraConfig(rtsp_url="rtsp://192.168.1.1:554/stream"),
        target_labels=["car"],
        confidence_threshold=0.5,
    )


@pytest.fixture()
def fake_camera() -> MagicMock:
    """Create a mock camera with read() and close() methods."""
    camera = MagicMock()
    camera.read.return_value = Frame(
        data=np.zeros((480, 640, 3), dtype=np.uint8),
        timestamp=1.0,
        source="local:0",
    )
    return camera


@pytest.fixture()
def fake_bgr_frame() -> np.ndarray:
    """Create a fake BGR array for frame data."""
    return np.zeros((480, 640, 3), dtype=np.uint8)


def _build_pipeline_with_mock_camera(
    mocker: MockerFixture,
    mock_engine: MagicMock,
    config: RuntimeConfig,
    fake_camera: MagicMock | None = None,
) -> tuple[DetectionPipeline, MagicMock]:
    """Construct a DetectionPipeline with a mocked camera constructor.

    Returns:
        Tuple of (pipeline, fake_camera_instance).
    """
    if fake_camera is None:
        fake_camera = MagicMock()
        fake_camera.read.return_value = Frame(
            data=np.zeros((480, 640, 3), dtype=np.uint8),
            timestamp=1.0,
            source="local:0",
        )

    mocker.patch(
        "model_lens.detection_pipeline.LocalCamera",
        return_value=fake_camera,
    )
    mocker.patch(
        "model_lens.detection_pipeline.RtspCamera",
        return_value=fake_camera,
    )
    pipeline = DetectionPipeline(engine=mock_engine, initial_config=config)
    return pipeline, fake_camera


def _build_pipeline_no_camera(
    mocker: MockerFixture,
    mock_engine: MagicMock,
    config: RuntimeConfig,
) -> DetectionPipeline:
    """Construct a DetectionPipeline where camera construction raises DeviceNotFoundError."""
    mocker.patch(
        "model_lens.detection_pipeline.LocalCamera",
        side_effect=DeviceNotFoundError("Device not found"),
    )
    mocker.patch(
        "model_lens.detection_pipeline.RtspCamera",
        side_effect=DeviceNotFoundError("Device not found"),
    )
    pipeline = DetectionPipeline(engine=mock_engine, initial_config=config)
    return pipeline


def _patch_run_to_exit_immediately(mocker: MockerFixture, pipeline: DetectionPipeline) -> None:
    """Patch _run so the background thread exits immediately."""
    mocker.patch.object(pipeline, "_run", return_value=None)


def _patch_run_to_wait_on_stop(mocker: MockerFixture, pipeline: DetectionPipeline) -> None:
    """Patch _run so it waits on _stop_event then returns."""

    def _wait_on_stop() -> None:
        pipeline._stop_event.wait()

    mocker.patch.object(pipeline, "_run", side_effect=_wait_on_stop)


# ===========================================================================
# PipelineResult — Immutability
# ===========================================================================


class TestPipelineResultImmutability:
    """PipelineResult frozen dataclass immutability tests."""

    def test_pipeline_result_is_frozen(self) -> None:
        """Assigning to a field on PipelineResult raises."""
        result = PipelineResult(
            jpeg_bytes=b"\xff\xd8",
            timestamp=1.0,
            source="local:0",
            detections=[],
        )
        with pytest.raises(AttributeError):
            result.jpeg_bytes = b"new"  # type: ignore[misc]


# ===========================================================================
# PipelineResult — Happy Path Construction
# ===========================================================================


class TestPipelineResultConstruction:
    """PipelineResult construction tests."""

    def test_pipeline_result_stores_all_fields(self) -> None:
        """All fields are stored correctly on construction."""
        result = PipelineResult(
            jpeg_bytes=b"\xff\xd8",
            timestamp=1.0,
            source="local:0",
            detections=[],
        )
        assert result.jpeg_bytes == b"\xff\xd8"
        assert result.timestamp == 1.0
        assert result.source == "local:0"
        assert result.detections == []

    def test_pipeline_result_stores_detections_list(self) -> None:
        """Detections list with items is preserved."""
        mock_detection = MagicMock(spec=DetectionResult)
        result = PipelineResult(
            jpeg_bytes=b"img",
            timestamp=2.0,
            source="rtsp:x",
            detections=[mock_detection],
        )
        assert result.detections == [mock_detection]


# ===========================================================================
# DetectionPipeline — Happy Path Construction
# ===========================================================================


class TestDetectionPipelineConstruction:
    """DetectionPipeline construction tests."""

    def test_construction_stores_engine_reference(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """Engine reference is stored."""
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config)
        assert pipeline._engine is mock_engine

    def test_construction_stores_initial_config(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """Initial config is stored as current config."""
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config)
        assert pipeline.get_config() is local_config

    def test_construction_creates_queue_with_maxsize_5(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """Result queue is created with maxsize=5."""
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config)
        assert pipeline.get_queue().maxsize == 5

    def test_construction_thread_is_daemon(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """Background thread is created as daemon."""
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config)
        assert pipeline._thread.daemon is True

    def test_construction_thread_not_started(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """Thread is not started during construction."""
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config)
        assert pipeline._thread.is_alive() is False

    def test_construction_builds_local_camera(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """LocalCamera is constructed when config has LocalCameraConfig."""
        fake_cam = MagicMock()
        mock_local_cls = mocker.patch(
            "model_lens.detection_pipeline.LocalCamera",
            return_value=fake_cam,
        )
        mocker.patch("model_lens.detection_pipeline.RtspCamera", return_value=MagicMock())

        pipeline = DetectionPipeline(engine=mock_engine, initial_config=local_config)

        mock_local_cls.assert_called_once_with(local_config.camera)
        assert pipeline._camera is fake_cam

    def test_construction_builds_rtsp_camera(
        self, mocker: MockerFixture, mock_engine: MagicMock, rtsp_config: RuntimeConfig
    ) -> None:
        """RtspCamera is constructed when config has RtspCameraConfig."""
        fake_cam = MagicMock()
        mocker.patch("model_lens.detection_pipeline.LocalCamera", return_value=MagicMock())
        mock_rtsp_cls = mocker.patch(
            "model_lens.detection_pipeline.RtspCamera",
            return_value=fake_cam,
        )

        pipeline = DetectionPipeline(engine=mock_engine, initial_config=rtsp_config)

        mock_rtsp_cls.assert_called_once_with(rtsp_config.camera)
        assert pipeline._camera is fake_cam

    def test_construction_camera_unavailable_sets_none(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """DeviceNotFoundError during camera build leaves _camera as None."""
        pipeline = _build_pipeline_no_camera(mocker, mock_engine, local_config)
        assert pipeline._camera is None

    def test_construction_unrecognised_camera_type_sets_none(
        self, mocker: MockerFixture, mock_engine: MagicMock
    ) -> None:
        """Unrecognised camera config type leaves _camera as None."""
        # Use a plain object as an unsupported camera config type
        unsupported_config = RuntimeConfig(camera=MagicMock())  # type: ignore[arg-type]
        mocker.patch("model_lens.detection_pipeline.LocalCamera", return_value=MagicMock())
        mocker.patch("model_lens.detection_pipeline.RtspCamera", return_value=MagicMock())

        pipeline = DetectionPipeline(engine=mock_engine, initial_config=unsupported_config)

        assert pipeline._camera is None


# ===========================================================================
# DetectionPipeline — Happy Path start
# ===========================================================================


class TestDetectionPipelineStart:
    """DetectionPipeline.start() tests."""

    def test_start_spawns_thread(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """start() begins the background thread."""
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config)
        # Patch _run to set _stop_event immediately so thread exits quickly
        mocker.patch.object(pipeline, "_run", side_effect=lambda: pipeline._stop_event.set())

        pipeline.start()

        # Give the thread a moment to start and finish
        pipeline._thread.join(timeout=2.0)
        # Thread was alive or completed — no exception raised
        assert not pipeline._thread.is_alive()


# ===========================================================================
# DetectionPipeline — Validation Failures
# ===========================================================================


class TestDetectionPipelineValidationFailures:
    """DetectionPipeline validation failure tests."""

    def test_start_called_twice_raises_runtime_error(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """Double start raises RuntimeError."""
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config)
        _patch_run_to_exit_immediately(mocker, pipeline)

        pipeline.start()

        with pytest.raises(RuntimeError, match="already running"):
            pipeline.start()


# ===========================================================================
# DetectionPipeline — Happy Path stop
# ===========================================================================


class TestDetectionPipelineStop:
    """DetectionPipeline.stop() tests."""

    def test_stop_sets_stop_event(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """stop() sets the stop event."""
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config)
        _patch_run_to_wait_on_stop(mocker, pipeline)
        pipeline.start()

        pipeline.stop()

        assert pipeline._stop_event.is_set() is True

    def test_stop_joins_thread(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """stop() joins the background thread."""
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config)
        _patch_run_to_wait_on_stop(mocker, pipeline)
        pipeline.start()

        pipeline.stop()

        assert pipeline._thread.is_alive() is False

    def test_stop_closes_camera(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """stop() closes the camera after thread exits."""
        pipeline, fake_cam = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config)
        _patch_run_to_wait_on_stop(mocker, pipeline)
        pipeline.start()

        pipeline.stop()

        fake_cam.close.assert_called_once()

    def test_stop_does_not_call_engine_teardown(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """stop() never calls engine.teardown()."""
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config)
        _patch_run_to_wait_on_stop(mocker, pipeline)
        pipeline.start()

        pipeline.stop()

        mock_engine.teardown.assert_not_called()


# ===========================================================================
# DetectionPipeline — Idempotency
# ===========================================================================


class TestDetectionPipelineIdempotency:
    """DetectionPipeline idempotency tests."""

    def test_stop_idempotent(self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig) -> None:
        """Calling stop() multiple times does not raise."""
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config)
        _patch_run_to_wait_on_stop(mocker, pipeline)
        pipeline.start()
        pipeline.stop()

        # Second call should not raise
        pipeline.stop()

    def test_stop_with_no_camera_does_not_raise(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """stop() with _camera=None does not raise."""
        pipeline = _build_pipeline_no_camera(mocker, mock_engine, local_config)
        _patch_run_to_wait_on_stop(mocker, pipeline)
        pipeline.start()

        # Should not raise
        pipeline.stop()


# ===========================================================================
# DetectionPipeline — Happy Path update_config
# ===========================================================================


class TestDetectionPipelineUpdateConfig:
    """DetectionPipeline.update_config() tests."""

    def test_update_config_replaces_config(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """update_config stores new config."""
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config)
        config_b = RuntimeConfig(
            camera=LocalCameraConfig(device_index=1),
            target_labels=["car"],
            confidence_threshold=0.7,
        )

        pipeline.update_config(config_b)

        assert pipeline.get_config() is config_b

    def test_update_config_sets_camera_changed_event(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """update_config signals camera change."""
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config)
        new_config = RuntimeConfig(
            camera=LocalCameraConfig(device_index=1),
            target_labels=[],
            confidence_threshold=0.5,
        )

        pipeline.update_config(new_config)

        assert pipeline._camera_changed_event.is_set() is True

    def test_update_config_returns_immediately(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """update_config does not block on camera recreation."""
        pipeline, original_cam = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config)
        # Do not start the thread
        new_config = RuntimeConfig(
            camera=LocalCameraConfig(device_index=2),
            target_labels=[],
            confidence_threshold=0.5,
        )

        pipeline.update_config(new_config)

        # Camera should be unchanged until loop runs
        assert pipeline._camera is original_cam


# ===========================================================================
# DetectionPipeline — Happy Path get_config
# ===========================================================================


class TestDetectionPipelineGetConfig:
    """DetectionPipeline.get_config() tests."""

    def test_get_config_returns_current_config(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """get_config returns stored config."""
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config)

        assert pipeline.get_config() is local_config


# ===========================================================================
# DetectionPipeline — Happy Path get_queue
# ===========================================================================


class TestDetectionPipelineGetQueue:
    """DetectionPipeline.get_queue() tests."""

    def test_get_queue_returns_queue_instance(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """get_queue returns the internal queue."""
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config)

        q = pipeline.get_queue()

        assert isinstance(q, queue.Queue)
        assert q.maxsize == 5


# ===========================================================================
# DetectionPipeline — Happy Path _build_camera
# ===========================================================================


class TestDetectionPipelineBuildCamera:
    """DetectionPipeline._build_camera() tests."""

    def test_build_camera_local_config(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """Builds LocalCamera for LocalCameraConfig."""
        fake_cam = MagicMock()
        mock_local_cls = mocker.patch(
            "model_lens.detection_pipeline.LocalCamera",
            return_value=fake_cam,
        )
        mocker.patch("model_lens.detection_pipeline.RtspCamera", return_value=MagicMock())

        # Construct pipeline first (which also calls _build_camera internally)
        pipeline = DetectionPipeline(engine=mock_engine, initial_config=local_config)
        mock_local_cls.reset_mock()

        # Call _build_camera directly
        result = pipeline._build_camera(local_config)

        mock_local_cls.assert_called_once_with(local_config.camera)
        assert result is fake_cam

    def test_build_camera_rtsp_config(
        self, mocker: MockerFixture, mock_engine: MagicMock, rtsp_config: RuntimeConfig
    ) -> None:
        """Builds RtspCamera for RtspCameraConfig."""
        fake_cam = MagicMock()
        mocker.patch("model_lens.detection_pipeline.LocalCamera", return_value=MagicMock())
        mock_rtsp_cls = mocker.patch(
            "model_lens.detection_pipeline.RtspCamera",
            return_value=fake_cam,
        )

        pipeline = DetectionPipeline(engine=mock_engine, initial_config=rtsp_config)
        mock_rtsp_cls.reset_mock()

        result = pipeline._build_camera(rtsp_config)

        mock_rtsp_cls.assert_called_once_with(rtsp_config.camera)
        assert result is fake_cam

    def test_build_camera_unrecognised_type_returns_none(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """Returns None for unrecognised camera config."""
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config)
        unsupported_config = RuntimeConfig(camera=MagicMock())  # type: ignore[arg-type]

        result = pipeline._build_camera(unsupported_config)

        assert result is None

    def test_build_camera_device_not_found_returns_none(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """Returns None when DeviceNotFoundError raised."""
        mocker.patch(
            "model_lens.detection_pipeline.LocalCamera",
            side_effect=DeviceNotFoundError("Device not found"),
        )
        mocker.patch("model_lens.detection_pipeline.RtspCamera", return_value=MagicMock())

        # Construction will also fail gracefully
        pipeline = DetectionPipeline(engine=mock_engine, initial_config=local_config)

        # Confirm _build_camera returns None
        result = pipeline._build_camera(local_config)

        assert result is None


# ===========================================================================
# DetectionPipeline — Happy Path _run_one_iteration
# ===========================================================================


class TestDetectionPipelineIteration:
    """DetectionPipeline._run_one_iteration() happy path tests."""

    def test_iteration_reads_frame_and_publishes_result(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """Full happy-path iteration produces a PipelineResult on the queue."""
        fake_bgr = np.zeros((480, 640, 3), dtype=np.uint8)
        fake_cam = MagicMock()
        fake_cam.read.return_value = Frame(data=fake_bgr, timestamp=1.0, source="local:0")

        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config, fake_camera=fake_cam)

        # Mock cv2.imencode
        numpy_buffer = MagicMock()
        numpy_buffer.tobytes.return_value = b"\xff\xd8"
        mocker.patch(
            "model_lens.detection_pipeline.cv2.imencode",
            return_value=(True, numpy_buffer),
        )

        # Mock engine.detect
        mock_detection = MagicMock(spec=DetectionResult)
        mock_engine.detect.return_value = [mock_detection]

        # Patch time.monotonic
        mocker.patch("model_lens.detection_pipeline.time.monotonic", return_value=50.0)

        pipeline._run_one_iteration()

        q = pipeline.get_queue()
        assert not q.empty()
        result = q.get_nowait()
        assert isinstance(result, PipelineResult)
        assert result.jpeg_bytes == b"\xff\xd8"
        assert result.timestamp == 1.0
        assert result.source == "local:0"
        assert result.detections == [mock_detection]

    def test_iteration_calls_detect_with_frame_data_and_target_labels(
        self, mocker: MockerFixture, mock_engine: MagicMock
    ) -> None:
        """Inference is called with frame.data and target_labels from config."""
        config = RuntimeConfig(
            camera=LocalCameraConfig(device_index=0),
            target_labels=["person", "car"],
            confidence_threshold=0.5,
        )
        fake_bgr = np.zeros((480, 640, 3), dtype=np.uint8)
        fake_cam = MagicMock()
        fake_cam.read.return_value = Frame(data=fake_bgr, timestamp=1.0, source="local:0")

        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, config, fake_camera=fake_cam)

        numpy_buffer = MagicMock()
        numpy_buffer.tobytes.return_value = b"\xff\xd8"
        mocker.patch(
            "model_lens.detection_pipeline.cv2.imencode",
            return_value=(True, numpy_buffer),
        )
        mocker.patch("model_lens.detection_pipeline.time.monotonic", return_value=50.0)

        pipeline._run_one_iteration()

        mock_engine.detect.assert_called_once()
        call_args = mock_engine.detect.call_args
        assert np.array_equal(call_args[0][0], fake_bgr)
        assert call_args[0][1] == ["person", "car"]


# ===========================================================================
# DetectionPipeline — State Transitions
# ===========================================================================


class TestDetectionPipelineStateTransitions:
    """DetectionPipeline state transition tests."""

    def test_camera_changed_event_triggers_rebuild(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """When camera_changed_event is set, existing camera is closed and new one built."""
        camera_a = MagicMock()
        camera_a.read.return_value = Frame(
            data=np.zeros((480, 640, 3), dtype=np.uint8), timestamp=1.0, source="local:0"
        )
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config, fake_camera=camera_a)

        # Prepare a new config and camera_b
        new_config = RuntimeConfig(
            camera=LocalCameraConfig(device_index=1),
            target_labels=[],
            confidence_threshold=0.5,
        )
        camera_b = MagicMock()
        camera_b.read.return_value = Frame(
            data=np.zeros((480, 640, 3), dtype=np.uint8), timestamp=2.0, source="local:1"
        )

        # Set up the event and new config
        pipeline._camera_changed_event.set()
        pipeline.update_config(new_config)

        # Mock _build_camera to return camera_b
        mocker.patch.object(pipeline, "_build_camera", return_value=camera_b)

        # Mock cv2/engine so iteration completes
        numpy_buffer = MagicMock()
        numpy_buffer.tobytes.return_value = b"\xff\xd8"
        mocker.patch(
            "model_lens.detection_pipeline.cv2.imencode",
            return_value=(True, numpy_buffer),
        )
        mocker.patch("model_lens.detection_pipeline.time.monotonic", return_value=50.0)

        pipeline._run_one_iteration()

        camera_a.close.assert_called_once()
        assert pipeline._camera is camera_b

    def test_no_camera_waits_for_event(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """When _camera is None, iteration waits on _camera_changed_event."""
        pipeline = _build_pipeline_no_camera(mocker, mock_engine, local_config)

        # Spy on the wait method
        mock_wait = mocker.patch.object(pipeline._camera_changed_event, "wait", return_value=False)

        pipeline._run_one_iteration()

        mock_wait.assert_called_once_with(timeout=1.0)


# ===========================================================================
# DetectionPipeline — Error Propagation
# ===========================================================================


class TestDetectionPipelineErrorPropagation:
    """DetectionPipeline error propagation tests."""

    def test_camera_read_operation_error_closes_camera(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """OperationError from camera.read() closes and discards camera."""
        fake_cam = MagicMock()
        fake_cam.read.side_effect = OperationError("read failed")

        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config, fake_camera=fake_cam)
        mocker.patch("model_lens.detection_pipeline.time.monotonic", return_value=50.0)

        pipeline._run_one_iteration()

        fake_cam.close.assert_called_once()
        assert pipeline._camera is None
        assert pipeline.get_queue().empty()

    def test_imencode_failure_skips_frame(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """cv2.imencode returning False skips the frame."""
        fake_cam = MagicMock()
        fake_cam.read.return_value = Frame(
            data=np.zeros((480, 640, 3), dtype=np.uint8), timestamp=1.0, source="local:0"
        )
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config, fake_camera=fake_cam)

        mocker.patch(
            "model_lens.detection_pipeline.cv2.imencode",
            return_value=(False, None),
        )
        mocker.patch("model_lens.detection_pipeline.time.monotonic", return_value=50.0)

        pipeline._run_one_iteration()

        assert pipeline.get_queue().empty()
        mock_engine.detect.assert_not_called()

    def test_detect_operation_error_skips_frame(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """OperationError from engine.detect() skips the frame."""
        fake_cam = MagicMock()
        fake_cam.read.return_value = Frame(
            data=np.zeros((480, 640, 3), dtype=np.uint8), timestamp=1.0, source="local:0"
        )
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config, fake_camera=fake_cam)

        numpy_buffer = MagicMock()
        numpy_buffer.tobytes.return_value = b"\xff\xd8"
        mocker.patch(
            "model_lens.detection_pipeline.cv2.imencode",
            return_value=(True, numpy_buffer),
        )
        mocker.patch("model_lens.detection_pipeline.time.monotonic", return_value=50.0)
        mock_engine.detect.side_effect = OperationError("detect failed")

        pipeline._run_one_iteration()

        assert pipeline.get_queue().empty()
        # Camera NOT closed
        fake_cam.close.assert_not_called()

    def test_detect_parse_error_triggers_shutdown(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """ParseError from engine.detect() sets stop event and sends SIGINT."""
        fake_cam = MagicMock()
        fake_cam.read.return_value = Frame(
            data=np.zeros((480, 640, 3), dtype=np.uint8), timestamp=1.0, source="local:0"
        )
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config, fake_camera=fake_cam)

        numpy_buffer = MagicMock()
        numpy_buffer.tobytes.return_value = b"\xff\xd8"
        mocker.patch(
            "model_lens.detection_pipeline.cv2.imencode",
            return_value=(True, numpy_buffer),
        )
        mocker.patch("model_lens.detection_pipeline.time.monotonic", return_value=50.0)
        mock_engine.detect.side_effect = ParseError("parse failed")

        known_pid = 12345
        mocker.patch("model_lens.detection_pipeline.os.getpid", return_value=known_pid)
        mock_kill = mocker.patch("model_lens.detection_pipeline.os.kill")

        pipeline._run_one_iteration()

        assert pipeline._stop_event.is_set() is True
        mock_kill.assert_called_once_with(known_pid, signal.SIGINT)

    def test_detect_parse_error_does_not_call_engine_teardown(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """ParseError handling does not call engine.teardown()."""
        fake_cam = MagicMock()
        fake_cam.read.return_value = Frame(
            data=np.zeros((480, 640, 3), dtype=np.uint8), timestamp=1.0, source="local:0"
        )
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config, fake_camera=fake_cam)

        numpy_buffer = MagicMock()
        numpy_buffer.tobytes.return_value = b"\xff\xd8"
        mocker.patch(
            "model_lens.detection_pipeline.cv2.imencode",
            return_value=(True, numpy_buffer),
        )
        mocker.patch("model_lens.detection_pipeline.time.monotonic", return_value=50.0)
        mock_engine.detect.side_effect = ParseError("parse failed")
        mocker.patch("model_lens.detection_pipeline.os.getpid", return_value=1)
        mocker.patch("model_lens.detection_pipeline.os.kill")

        pipeline._run_one_iteration()

        mock_engine.teardown.assert_not_called()


# ===========================================================================
# DetectionPipeline — Queue Publish
# ===========================================================================


class TestDetectionPipelineQueuePublish:
    """DetectionPipeline queue publish tests."""

    def test_publish_drops_oldest_when_queue_full(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """When queue is full, oldest item is dropped before new publish."""
        fake_cam = MagicMock()
        fake_cam.read.return_value = Frame(
            data=np.zeros((480, 640, 3), dtype=np.uint8), timestamp=99.0, source="local:0"
        )
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config, fake_camera=fake_cam)

        # Fill queue to capacity (5 items)
        q = pipeline.get_queue()
        oldest = PipelineResult(jpeg_bytes=b"oldest", timestamp=0.0, source="old", detections=[])
        for i in range(5):
            if i == 0:
                q.put_nowait(oldest)
            else:
                q.put_nowait(
                    PipelineResult(jpeg_bytes=f"item{i}".encode(), timestamp=float(i), source="x", detections=[])
                )

        numpy_buffer = MagicMock()
        numpy_buffer.tobytes.return_value = b"new_frame"
        mocker.patch(
            "model_lens.detection_pipeline.cv2.imencode",
            return_value=(True, numpy_buffer),
        )
        mocker.patch("model_lens.detection_pipeline.time.monotonic", return_value=50.0)

        pipeline._run_one_iteration()

        # Queue still has 5 items
        assert q.qsize() == 5
        # Collect all items
        items = []
        while not q.empty():
            items.append(q.get_nowait())
        # The oldest item should no longer be present
        assert oldest not in items
        # The newest item should be the last one
        assert items[-1].jpeg_bytes == b"new_frame"

    def test_publish_updates_last_frame_time(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """_last_frame_time is updated after successful publish."""
        fake_cam = MagicMock()
        fake_cam.read.return_value = Frame(
            data=np.zeros((480, 640, 3), dtype=np.uint8), timestamp=1.0, source="local:0"
        )
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config, fake_camera=fake_cam)

        numpy_buffer = MagicMock()
        numpy_buffer.tobytes.return_value = b"\xff\xd8"
        mocker.patch(
            "model_lens.detection_pipeline.cv2.imencode",
            return_value=(True, numpy_buffer),
        )
        mocker.patch("model_lens.detection_pipeline.time.monotonic", return_value=99.5)

        pipeline._run_one_iteration()

        assert pipeline._last_frame_time == 99.5

    def test_skipped_frame_does_not_update_last_frame_time(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """_last_frame_time is NOT updated when frame is skipped."""
        fake_cam = MagicMock()
        fake_cam.read.return_value = Frame(
            data=np.zeros((480, 640, 3), dtype=np.uint8), timestamp=1.0, source="local:0"
        )
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config, fake_camera=fake_cam)
        pipeline._last_frame_time = 10.0

        mocker.patch(
            "model_lens.detection_pipeline.cv2.imencode",
            return_value=(False, None),
        )
        mocker.patch("model_lens.detection_pipeline.time.monotonic", return_value=50.0)

        pipeline._run_one_iteration()

        assert pipeline._last_frame_time == 10.0


# ===========================================================================
# DetectionPipeline — FPS Throttle
# ===========================================================================


class TestDetectionPipelineFPSThrottle:
    """DetectionPipeline FPS throttle tests."""

    def test_first_frame_not_throttled(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """First frame is never throttled (_last_frame_time == 0.0)."""
        fake_cam = MagicMock()
        fake_cam.read.return_value = Frame(
            data=np.zeros((480, 640, 3), dtype=np.uint8), timestamp=1.0, source="local:0"
        )
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config, fake_camera=fake_cam)
        pipeline._last_frame_time = 0.0

        numpy_buffer = MagicMock()
        numpy_buffer.tobytes.return_value = b"\xff\xd8"
        mocker.patch(
            "model_lens.detection_pipeline.cv2.imencode",
            return_value=(True, numpy_buffer),
        )
        mocker.patch("model_lens.detection_pipeline.time.monotonic", return_value=100.0)

        # Spy on _stop_event.wait to check throttle
        spy_wait = mocker.spy(pipeline._stop_event, "wait")

        pipeline._run_one_iteration()

        # _stop_event.wait should NOT have been called for throttle
        spy_wait.assert_not_called()
        # Result published
        assert not pipeline.get_queue().empty()

    def test_throttle_waits_when_frames_too_fast(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """Throttle applies interruptible wait when elapsed < 1/30."""
        fake_cam = MagicMock()
        fake_cam.read.return_value = Frame(
            data=np.zeros((480, 640, 3), dtype=np.uint8), timestamp=1.0, source="local:0"
        )
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config, fake_camera=fake_cam)
        pipeline._last_frame_time = 100.0

        numpy_buffer = MagicMock()
        numpy_buffer.tobytes.return_value = b"\xff\xd8"
        mocker.patch(
            "model_lens.detection_pipeline.cv2.imencode",
            return_value=(True, numpy_buffer),
        )
        # Only 10ms elapsed (less than ~33.3ms for 30 FPS)
        mocker.patch("model_lens.detection_pipeline.time.monotonic", return_value=100.01)

        # Spy on _stop_event.wait
        spy_wait = mocker.spy(pipeline._stop_event, "wait")

        pipeline._run_one_iteration()

        # _stop_event.wait should have been called with timeout approximately 1/30 - 0.01
        spy_wait.assert_called_once()
        call_kwargs = spy_wait.call_args
        timeout_val = call_kwargs[1].get("timeout") if call_kwargs[1] else call_kwargs[0][0]
        expected = (1.0 / 30) - 0.01
        assert timeout_val == pytest.approx(expected, abs=0.001)

    def test_throttle_skipped_when_frames_slow(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """No throttle when elapsed >= 1/30."""
        fake_cam = MagicMock()
        fake_cam.read.return_value = Frame(
            data=np.zeros((480, 640, 3), dtype=np.uint8), timestamp=1.0, source="local:0"
        )
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config, fake_camera=fake_cam)
        pipeline._last_frame_time = 100.0

        numpy_buffer = MagicMock()
        numpy_buffer.tobytes.return_value = b"\xff\xd8"
        mocker.patch(
            "model_lens.detection_pipeline.cv2.imencode",
            return_value=(True, numpy_buffer),
        )
        # 50ms elapsed (more than ~33.3ms)
        mocker.patch("model_lens.detection_pipeline.time.monotonic", return_value=100.05)

        spy_wait = mocker.spy(pipeline._stop_event, "wait")

        pipeline._run_one_iteration()

        # _stop_event.wait should NOT be called for throttle
        spy_wait.assert_not_called()
        assert not pipeline.get_queue().empty()

    def test_throttle_interrupted_by_stop_event(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """If stop_event set during throttle wait, iteration returns without reading."""
        fake_cam = MagicMock()
        fake_cam.read.return_value = Frame(
            data=np.zeros((480, 640, 3), dtype=np.uint8), timestamp=1.0, source="local:0"
        )
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config, fake_camera=fake_cam)
        pipeline._last_frame_time = 100.0

        mocker.patch("model_lens.detection_pipeline.time.monotonic", return_value=100.01)

        # Configure _stop_event.wait to set _stop_event (simulating stop during wait)
        def wait_and_set_stop(timeout: float | None = None) -> bool:
            pipeline._stop_event.set()
            return True

        mocker.patch.object(pipeline._stop_event, "wait", side_effect=wait_and_set_stop)

        pipeline._run_one_iteration()

        # camera.read() should not have been called
        fake_cam.read.assert_not_called()
        assert pipeline.get_queue().empty()


# ===========================================================================
# DetectionPipeline — Concurrent Behaviour
# ===========================================================================


class TestDetectionPipelineConcurrency:
    """DetectionPipeline concurrent behaviour tests."""

    def test_update_config_thread_safe(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """Concurrent update_config and get_config do not corrupt state."""
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config)

        num_threads = 10
        barrier = threading.Barrier(num_threads)
        errors: list[Exception] = []
        configs = [
            RuntimeConfig(
                camera=LocalCameraConfig(device_index=i),
                target_labels=[f"label_{i}"],
                confidence_threshold=0.5,
            )
            for i in range(num_threads // 2)
        ]

        def writer(idx: int) -> None:
            try:
                barrier.wait(timeout=5.0)
                pipeline.update_config(configs[idx % len(configs)])
            except Exception as e:
                errors.append(e)

        def reader() -> None:
            try:
                barrier.wait(timeout=5.0)
                result = pipeline.get_config()
                assert isinstance(result, RuntimeConfig)
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(num_threads):
            if i % 2 == 0:
                t = threading.Thread(target=writer, args=(i,))
            else:
                t = threading.Thread(target=reader)
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        assert errors == []

    def test_update_config_unblocks_camera_wait(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """update_config unblocks _camera_changed_event.wait in the loop."""
        pipeline = _build_pipeline_no_camera(mocker, mock_engine, local_config)

        # Prepare new config with a camera that will succeed
        new_config = RuntimeConfig(
            camera=LocalCameraConfig(device_index=0),
            target_labels=[],
            confidence_threshold=0.5,
        )
        new_cam = MagicMock()
        new_cam.read.return_value = Frame(data=np.zeros((480, 640, 3), dtype=np.uint8), timestamp=1.0, source="local:0")

        iteration_done = threading.Event()

        # Patch _build_camera to return new_cam (after the initial None from construction)
        def patched_build(cfg: RuntimeConfig) -> MagicMock | None:
            if cfg is new_config:
                return new_cam
            return None

        mocker.patch.object(pipeline, "_build_camera", side_effect=patched_build)

        numpy_buffer = MagicMock()
        numpy_buffer.tobytes.return_value = b"\xff\xd8"
        mocker.patch(
            "model_lens.detection_pipeline.cv2.imencode",
            return_value=(True, numpy_buffer),
        )
        mocker.patch("model_lens.detection_pipeline.time.monotonic", return_value=50.0)

        # Start a thread that runs two iterations: first waits, second processes
        def run_iterations() -> None:
            pipeline._run_one_iteration()  # This should wait on event
            pipeline._run_one_iteration()  # This should process after config update
            iteration_done.set()

        runner = threading.Thread(target=run_iterations)
        runner.start()

        # Give the first iteration time to start waiting
        import time

        time.sleep(0.1)

        # Update config from another thread — should unblock the wait
        pipeline.update_config(new_config)

        runner.join(timeout=5.0)
        assert iteration_done.is_set()


# ===========================================================================
# DetectionPipeline — Mock / Dependency Interaction
# ===========================================================================


class TestDetectionPipelineDependencyInteraction:
    """DetectionPipeline mock/dependency interaction tests."""

    def test_camera_close_called_on_config_change(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """Old camera is closed when camera_changed_event fires."""
        camera_a = MagicMock()
        camera_a.read.return_value = Frame(
            data=np.zeros((480, 640, 3), dtype=np.uint8), timestamp=1.0, source="local:0"
        )
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config, fake_camera=camera_a)

        new_config = RuntimeConfig(
            camera=LocalCameraConfig(device_index=1),
            target_labels=[],
            confidence_threshold=0.5,
        )
        pipeline._camera_changed_event.set()
        pipeline.update_config(new_config)

        new_cam = MagicMock()
        new_cam.read.return_value = Frame(data=np.zeros((480, 640, 3), dtype=np.uint8), timestamp=2.0, source="local:1")
        mocker.patch.object(pipeline, "_build_camera", return_value=new_cam)

        numpy_buffer = MagicMock()
        numpy_buffer.tobytes.return_value = b"\xff\xd8"
        mocker.patch(
            "model_lens.detection_pipeline.cv2.imencode",
            return_value=(True, numpy_buffer),
        )
        mocker.patch("model_lens.detection_pipeline.time.monotonic", return_value=50.0)

        pipeline._run_one_iteration()

        camera_a.close.assert_called_once()

    def test_imencode_called_with_jpg_and_frame_data(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """cv2.imencode is called with '.jpg' and the frame data."""
        fake_bgr = np.ones((480, 640, 3), dtype=np.uint8) * 42
        fake_cam = MagicMock()
        fake_cam.read.return_value = Frame(data=fake_bgr, timestamp=1.0, source="local:0")
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config, fake_camera=fake_cam)

        numpy_buffer = MagicMock()
        numpy_buffer.tobytes.return_value = b"\xff\xd8"
        mock_imencode = mocker.patch(
            "model_lens.detection_pipeline.cv2.imencode",
            return_value=(True, numpy_buffer),
        )
        mocker.patch("model_lens.detection_pipeline.time.monotonic", return_value=50.0)

        pipeline._run_one_iteration()

        mock_imencode.assert_called_once()
        call_args = mock_imencode.call_args[0]
        assert call_args[0] == ".jpg"
        assert np.array_equal(call_args[1], fake_bgr)

    def test_engine_detect_not_called_when_imencode_fails(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """Engine.detect is not called if imencode fails."""
        fake_cam = MagicMock()
        fake_cam.read.return_value = Frame(
            data=np.zeros((480, 640, 3), dtype=np.uint8), timestamp=1.0, source="local:0"
        )
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config, fake_camera=fake_cam)

        mocker.patch(
            "model_lens.detection_pipeline.cv2.imencode",
            return_value=(False, None),
        )
        mocker.patch("model_lens.detection_pipeline.time.monotonic", return_value=50.0)

        pipeline._run_one_iteration()

        mock_engine.detect.assert_not_called()

    def test_stop_event_set_before_sigint_on_parse_error(
        self, mocker: MockerFixture, mock_engine: MagicMock, local_config: RuntimeConfig
    ) -> None:
        """_stop_event is set before os.kill is called on ParseError."""
        fake_cam = MagicMock()
        fake_cam.read.return_value = Frame(
            data=np.zeros((480, 640, 3), dtype=np.uint8), timestamp=1.0, source="local:0"
        )
        pipeline, _ = _build_pipeline_with_mock_camera(mocker, mock_engine, local_config, fake_camera=fake_cam)

        numpy_buffer = MagicMock()
        numpy_buffer.tobytes.return_value = b"\xff\xd8"
        mocker.patch(
            "model_lens.detection_pipeline.cv2.imencode",
            return_value=(True, numpy_buffer),
        )
        mocker.patch("model_lens.detection_pipeline.time.monotonic", return_value=50.0)
        mock_engine.detect.side_effect = ParseError("parse failed")
        mocker.patch("model_lens.detection_pipeline.os.getpid", return_value=999)

        # Track whether _stop_event was set at the time os.kill is called
        stop_was_set_at_kill_time: list[bool] = []

        def track_kill(pid: int, sig: int) -> None:
            stop_was_set_at_kill_time.append(pipeline._stop_event.is_set())

        mocker.patch("model_lens.detection_pipeline.os.kill", side_effect=track_kill)

        pipeline._run_one_iteration()

        assert stop_was_set_at_kill_time == [True]
