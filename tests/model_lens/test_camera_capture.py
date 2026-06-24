"""Tests for model_lens.camera_capture module.

Covers CameraCapture abstract base, LocalCamera, RtspCamera, and _retry_read.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, call

import numpy as np
import pytest

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# Production module gate — all tests skip until camera_capture.py exists.
camera_capture = pytest.importorskip(
    "model_lens.camera_capture",
    reason="Production module model_lens.camera_capture not yet implemented",
)

from model_lens.camera_capture import (  # noqa: E402
    CameraCapture,
    LocalCamera,
    RtspCamera,
    _retry_read,
)
from model_lens.entities import Frame, LocalCameraConfig, RtspCameraConfig  # noqa: E402
from model_lens.exceptions import (  # noqa: E402
    DeviceNotFoundError,
    OperationError,
    ValidationError,
)


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def fake_bgr_array() -> np.ndarray:
    """Create a small BGR array simulating a camera frame."""
    return np.zeros((480, 640, 3), dtype=np.uint8)


@pytest.fixture()
def mock_video_capture_opened(mocker: MockerFixture) -> MagicMock:
    """Mock cv2.VideoCapture returning an opened handle."""
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
    mocker.patch("model_lens.camera_capture.cv2.VideoCapture", return_value=mock_cap)
    return mock_cap


@pytest.fixture()
def mock_video_capture_closed(mocker: MockerFixture) -> MagicMock:
    """Mock cv2.VideoCapture returning a handle where isOpened() is False."""
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = False
    mocker.patch("model_lens.camera_capture.cv2.VideoCapture", return_value=mock_cap)
    return mock_cap


def _make_local_camera(mocker: MockerFixture, device_index: int = 0) -> LocalCamera:
    """Construct a LocalCamera with an opened mock VideoCapture."""
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
    mocker.patch("model_lens.camera_capture.cv2.VideoCapture", return_value=mock_cap)
    config = LocalCameraConfig(device_index=device_index)
    return LocalCamera(config)


def _make_rtsp_camera(mocker: MockerFixture, url: str = "rtsp://192.168.1.1/stream") -> RtspCamera:
    """Construct an RtspCamera with an opened mock VideoCapture."""
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
    mocker.patch("model_lens.camera_capture.cv2.VideoCapture", return_value=mock_cap)
    config = RtspCameraConfig(rtsp_url=url)
    return RtspCamera(config)


# ===========================================================================
# CameraCapture — Type Hierarchy
# ===========================================================================


class TestCameraCaptureTypeHierarchy:
    """CameraCapture abstract base class type hierarchy tests."""

    def test_camera_capture_is_abstract(self) -> None:
        """CameraCapture cannot be instantiated directly."""
        with pytest.raises(TypeError):
            CameraCapture()  # type: ignore[abstract]

    def test_local_camera_is_subclass_of_camera_capture(self) -> None:
        """LocalCamera inherits from CameraCapture."""
        assert issubclass(LocalCamera, CameraCapture)

    def test_rtsp_camera_is_subclass_of_camera_capture(self) -> None:
        """RtspCamera inherits from CameraCapture."""
        assert issubclass(RtspCamera, CameraCapture)


# ===========================================================================
# LocalCamera — Happy Path Construction
# ===========================================================================


class TestLocalCameraConstruction:
    """LocalCamera construction tests."""

    def test_local_camera_opens_device(self, mocker: MockerFixture) -> None:
        """Construction opens the cv2.VideoCapture with the given device index."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_vc = mocker.patch("model_lens.camera_capture.cv2.VideoCapture", return_value=mock_cap)
        config = LocalCameraConfig(device_index=0)

        LocalCamera(config)

        mock_vc.assert_called_once_with(0)

    def test_local_camera_sets_source_string(self, mocker: MockerFixture) -> None:
        """Source is set to the format 'local:{device_index}'."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mocker.patch("model_lens.camera_capture.cv2.VideoCapture", return_value=mock_cap)
        config = LocalCameraConfig(device_index=2)

        camera = LocalCamera(config)

        assert camera.source == "local:2"


# ===========================================================================
# LocalCamera — Validation Failures
# ===========================================================================


class TestLocalCameraValidationFailures:
    """LocalCamera validation failure tests."""

    def test_local_camera_device_not_found(self, mock_video_capture_closed: MagicMock) -> None:
        """Raises DeviceNotFoundError when device is unreachable."""
        config = LocalCameraConfig(device_index=99)

        with pytest.raises(DeviceNotFoundError):
            LocalCamera(config)


# ===========================================================================
# LocalCamera — Happy Path read
# ===========================================================================


class TestLocalCameraRead:
    """LocalCamera.read() happy path tests."""

    def test_local_camera_read_returns_frame(self, mocker: MockerFixture) -> None:
        """Successful read returns a Frame with copied data, timestamp, and source."""
        fake_array = np.ones((480, 640, 3), dtype=np.uint8)
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, fake_array)
        mocker.patch("model_lens.camera_capture.cv2.VideoCapture", return_value=mock_cap)
        mocker.patch("model_lens.camera_capture.time.time", return_value=1000.5)
        mocker.patch("model_lens.camera_capture.random.uniform", return_value=0.0)

        config = LocalCameraConfig(device_index=0)
        camera = LocalCamera(config)
        frame = camera.read()

        assert isinstance(frame, Frame)
        assert np.array_equal(frame.data, fake_array)
        assert frame.timestamp == 1000.5
        assert frame.source == "local:0"

    def test_local_camera_read_copies_buffer(self, mocker: MockerFixture) -> None:
        """Frame data is a copy of the raw buffer, not the original reference."""
        original_array = np.ones((480, 640, 3), dtype=np.uint8)
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, original_array)
        mocker.patch("model_lens.camera_capture.cv2.VideoCapture", return_value=mock_cap)
        mocker.patch("model_lens.camera_capture.time.time", return_value=1000.0)
        mocker.patch("model_lens.camera_capture.random.uniform", return_value=0.0)

        config = LocalCameraConfig(device_index=0)
        camera = LocalCamera(config)
        frame = camera.read()

        assert frame.data is not original_array


# ===========================================================================
# LocalCamera — Mock / Dependency Interaction
# ===========================================================================


class TestLocalCameraDependencyInteraction:
    """LocalCamera mock/dependency interaction tests."""

    def test_local_camera_read_acquires_lock(self, mocker: MockerFixture) -> None:
        """read() acquires the per-instance lock during cap.read()."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mocker.patch("model_lens.camera_capture.cv2.VideoCapture", return_value=mock_cap)
        mocker.patch("model_lens.camera_capture.time.time", return_value=1000.0)
        mocker.patch("model_lens.camera_capture.random.uniform", return_value=0.0)

        config = LocalCameraConfig(device_index=0)
        camera = LocalCamera(config)

        # Replace lock with a spy
        spy_lock = MagicMock(spec=threading.Lock)
        spy_lock.acquire.return_value = True
        camera._lock = spy_lock

        camera.read()

        # Lock should have been used (acquire/release or __enter__/__exit__)
        assert spy_lock.acquire.called or spy_lock.__enter__.called

    def test_local_camera_reopen_creates_fresh_handle(self, mocker: MockerFixture) -> None:
        """_reopen() creates a new VideoCapture and stores it."""
        mock_cap_initial = MagicMock()
        mock_cap_initial.isOpened.return_value = True
        mock_vc = mocker.patch("model_lens.camera_capture.cv2.VideoCapture", return_value=mock_cap_initial)

        config = LocalCameraConfig(device_index=0)
        camera = LocalCamera(config)

        # Set up a new mock for the reopen call
        mock_cap_fresh = MagicMock()
        mock_cap_fresh.isOpened.return_value = True
        mock_vc.return_value = mock_cap_fresh

        camera._reopen()

        # Verify new VideoCapture was created with device_index
        assert mock_vc.call_count == 2
        mock_vc.assert_called_with(0)
        assert camera._cap is mock_cap_fresh


# ===========================================================================
# LocalCamera — Resource Cleanup
# ===========================================================================


class TestLocalCameraResourceCleanup:
    """LocalCamera resource cleanup tests."""

    def test_local_camera_close_releases_handle(self, mocker: MockerFixture) -> None:
        """close() releases the underlying cv2 handle."""
        camera = _make_local_camera(mocker)
        cap = camera._cap

        camera.close()

        cap.release.assert_called_once()

    def test_local_camera_close_idempotent(self, mocker: MockerFixture) -> None:
        """Calling close() multiple times does not raise or release again."""
        camera = _make_local_camera(mocker)
        cap = camera._cap

        camera.close()
        camera.close()

        cap.release.assert_called_once()

    def test_local_camera_context_manager_calls_close(self, mocker: MockerFixture) -> None:
        """Exiting the context manager calls close()."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mocker.patch("model_lens.camera_capture.cv2.VideoCapture", return_value=mock_cap)

        config = LocalCameraConfig(device_index=0)
        with LocalCamera(config) as _cam:
            pass

        mock_cap.release.assert_called_once()


# ===========================================================================
# RtspCamera — Happy Path Construction
# ===========================================================================


class TestRtspCameraConstruction:
    """RtspCamera construction tests."""

    def test_rtsp_camera_opens_url(self, mocker: MockerFixture) -> None:
        """Construction opens cv2.VideoCapture with the RTSP URL."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_vc = mocker.patch("model_lens.camera_capture.cv2.VideoCapture", return_value=mock_cap)

        config = RtspCameraConfig(rtsp_url="rtsp://192.168.1.1/stream")
        RtspCamera(config)

        mock_vc.assert_called_once_with("rtsp://192.168.1.1/stream")

    def test_rtsp_camera_sets_source_to_url(self, mocker: MockerFixture) -> None:
        """Source is set to the full RTSP URL string."""
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mocker.patch("model_lens.camera_capture.cv2.VideoCapture", return_value=mock_cap)

        config = RtspCameraConfig(rtsp_url="rtsp://host/path")
        camera = RtspCamera(config)

        assert camera.source == "rtsp://host/path"


# ===========================================================================
# RtspCamera — Validation Failures
# ===========================================================================


class TestRtspCameraValidationFailures:
    """RtspCamera validation failure tests."""

    def test_rtsp_camera_invalid_url_prefix(self) -> None:
        """Raises ValidationError when URL does not start with 'rtsp://'."""
        config = RtspCameraConfig(rtsp_url="http://example.com/stream")

        with pytest.raises(ValidationError):
            RtspCamera(config)

    def test_rtsp_camera_rtsps_url_rejected(self) -> None:
        """Raises ValidationError when URL uses rtsps:// scheme."""
        config = RtspCameraConfig(rtsp_url="rtsps://secure.host/stream")

        with pytest.raises(ValidationError):
            RtspCamera(config)

    def test_rtsp_camera_device_not_found(self, mock_video_capture_closed: MagicMock) -> None:
        """Raises DeviceNotFoundError when URL is unreachable."""
        config = RtspCameraConfig(rtsp_url="rtsp://unreachable/stream")

        with pytest.raises(DeviceNotFoundError):
            RtspCamera(config)


# ===========================================================================
# RtspCamera — Happy Path read
# ===========================================================================


class TestRtspCameraRead:
    """RtspCamera.read() happy path tests."""

    def test_rtsp_camera_read_returns_frame(self, mocker: MockerFixture) -> None:
        """Successful read returns a Frame with correct fields."""
        fake_array = np.ones((480, 640, 3), dtype=np.uint8)
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, fake_array)
        mocker.patch("model_lens.camera_capture.cv2.VideoCapture", return_value=mock_cap)
        mocker.patch("model_lens.camera_capture.time.time", return_value=2000.0)
        mocker.patch("model_lens.camera_capture.random.uniform", return_value=0.0)

        url = "rtsp://192.168.1.1/stream"
        config = RtspCameraConfig(rtsp_url=url)
        camera = RtspCamera(config)
        frame = camera.read()

        assert isinstance(frame, Frame)
        assert np.array_equal(frame.data, fake_array)
        assert frame.timestamp == 2000.0
        assert frame.source == url


# ===========================================================================
# RtspCamera — Resource Cleanup
# ===========================================================================


class TestRtspCameraResourceCleanup:
    """RtspCamera resource cleanup tests."""

    def test_rtsp_camera_close_releases_handle(self, mocker: MockerFixture) -> None:
        """close() releases the underlying cv2 handle."""
        camera = _make_rtsp_camera(mocker)
        cap = camera._cap

        camera.close()

        cap.release.assert_called_once()

    def test_rtsp_camera_close_idempotent(self, mocker: MockerFixture) -> None:
        """Calling close() multiple times does not raise or release again."""
        camera = _make_rtsp_camera(mocker)
        cap = camera._cap

        camera.close()
        camera.close()

        cap.release.assert_called_once()


# ===========================================================================
# _retry_read — Happy Path
# ===========================================================================


class TestRetryReadHappyPath:
    """_retry_read happy path tests."""

    def test_retry_read_succeeds_first_attempt(self, mocker: MockerFixture) -> None:
        """Returns Frame on first successful read without retrying."""
        fake_array = np.ones((480, 640, 3), dtype=np.uint8)
        mock_cap = MagicMock()
        mock_cap.read.return_value = (True, fake_array)
        mocker.patch("model_lens.camera_capture.time.time", return_value=5000.0)
        mock_sleep = mocker.patch("model_lens.camera_capture.time.sleep")

        mock_lock = MagicMock(spec=threading.Lock)
        mock_lock.acquire.return_value = True
        reopen_fn = MagicMock()

        frame = _retry_read(mock_cap, reopen_fn, "local:0", mock_lock)

        assert isinstance(frame, Frame)
        assert np.array_equal(frame.data, fake_array)
        assert frame.timestamp == 5000.0
        assert frame.source == "local:0"
        reopen_fn.assert_not_called()
        mock_sleep.assert_not_called()

    def test_retry_read_succeeds_second_attempt(self, mocker: MockerFixture) -> None:
        """Returns Frame after one failure and one retry."""
        fake_array = np.ones((480, 640, 3), dtype=np.uint8)
        mock_cap = MagicMock()
        mock_cap.read.side_effect = [(False, None), (True, fake_array)]
        mocker.patch("model_lens.camera_capture.time.time", return_value=5000.0)
        mock_sleep = mocker.patch("model_lens.camera_capture.time.sleep")
        mocker.patch("model_lens.camera_capture.random.uniform", return_value=0.5)

        mock_lock = MagicMock(spec=threading.Lock)
        mock_lock.acquire.return_value = True
        fresh_cap = MagicMock()
        fresh_cap.read.return_value = (True, fake_array)
        reopen_fn = MagicMock(return_value=fresh_cap)

        frame = _retry_read(mock_cap, reopen_fn, "local:0", mock_lock)

        assert isinstance(frame, Frame)
        mock_sleep.assert_called_once_with(1.5)  # 1.0 base + 0.5 jitter
        reopen_fn.assert_called_once()

    def test_retry_read_succeeds_third_attempt(self, mocker: MockerFixture) -> None:
        """Returns Frame after two failures."""
        fake_array = np.ones((480, 640, 3), dtype=np.uint8)
        mock_cap = MagicMock()
        mock_cap.read.side_effect = [(False, None), (False, None)]
        mocker.patch("model_lens.camera_capture.time.time", return_value=5000.0)
        mock_sleep = mocker.patch("model_lens.camera_capture.time.sleep")
        mocker.patch("model_lens.camera_capture.random.uniform", return_value=0.0)

        mock_lock = MagicMock(spec=threading.Lock)
        mock_lock.acquire.return_value = True

        # After each reopen, the cap returned by reopen_fn is used for next read
        fresh_cap_1 = MagicMock()
        fresh_cap_1.read.return_value = (False, None)
        fresh_cap_2 = MagicMock()
        fresh_cap_2.read.return_value = (True, fake_array)
        reopen_fn = MagicMock(side_effect=[fresh_cap_1, fresh_cap_2])

        frame = _retry_read(mock_cap, reopen_fn, "local:0", mock_lock)

        assert isinstance(frame, Frame)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1.0)  # 1.0 + 0.0 jitter
        mock_sleep.assert_any_call(2.0)  # 2.0 + 0.0 jitter
        assert reopen_fn.call_count == 2


# ===========================================================================
# _retry_read — Error Propagation
# ===========================================================================


class TestRetryReadErrorPropagation:
    """_retry_read error propagation tests."""

    def test_retry_read_all_attempts_fail_raises_operation_error(self, mocker: MockerFixture) -> None:
        """Raises OperationError after all 3 attempts are exhausted."""
        mock_cap = MagicMock()
        mock_cap.read.return_value = (False, None)
        mocker.patch("model_lens.camera_capture.time.sleep")
        mocker.patch("model_lens.camera_capture.random.uniform", return_value=0.0)

        mock_lock = MagicMock(spec=threading.Lock)
        mock_lock.acquire.return_value = True

        fresh_cap = MagicMock()
        fresh_cap.read.return_value = (False, None)
        reopen_fn = MagicMock(return_value=fresh_cap)

        with pytest.raises(OperationError):
            _retry_read(mock_cap, reopen_fn, "source", mock_lock)


# ===========================================================================
# _retry_read — Mock / Dependency Interaction
# ===========================================================================


class TestRetryReadDependencyInteraction:
    """_retry_read mock/dependency interaction tests."""

    def test_retry_read_releases_cap_on_failure(self, mocker: MockerFixture) -> None:
        """Each failed attempt releases the cap under the lock."""
        fake_array = np.ones((480, 640, 3), dtype=np.uint8)
        mock_cap = MagicMock()
        mock_cap.read.return_value = (False, None)
        mocker.patch("model_lens.camera_capture.time.sleep")
        mocker.patch("model_lens.camera_capture.time.time", return_value=1000.0)
        mocker.patch("model_lens.camera_capture.random.uniform", return_value=0.0)

        mock_lock = MagicMock(spec=threading.Lock)
        mock_lock.acquire.return_value = True

        fresh_cap = MagicMock()
        fresh_cap.read.return_value = (True, fake_array)
        reopen_fn = MagicMock(return_value=fresh_cap)

        _retry_read(mock_cap, reopen_fn, "source", mock_lock)

        # Original cap should have been released once (on the first failed attempt)
        mock_cap.release.assert_called_once()

    def test_retry_read_calls_reopen_between_retries(self, mocker: MockerFixture) -> None:
        """reopen_fn is called between failed attempts to get a fresh handle."""
        mock_cap = MagicMock()
        mock_cap.read.return_value = (False, None)
        mocker.patch("model_lens.camera_capture.time.sleep")
        mocker.patch("model_lens.camera_capture.random.uniform", return_value=0.0)

        mock_lock = MagicMock(spec=threading.Lock)
        mock_lock.acquire.return_value = True

        fresh_cap = MagicMock()
        fresh_cap.read.return_value = (False, None)
        reopen_fn = MagicMock(return_value=fresh_cap)

        with pytest.raises(OperationError):
            _retry_read(mock_cap, reopen_fn, "source", mock_lock)

        # reopen_fn called after attempt 1 and attempt 2, not after final attempt
        assert reopen_fn.call_count == 2

    def test_retry_read_sleep_outside_lock(self, mocker: MockerFixture) -> None:
        """Sleep occurs after releasing the lock, not while holding it."""
        fake_array = np.ones((480, 640, 3), dtype=np.uint8)
        mock_cap = MagicMock()
        mock_cap.read.return_value = (False, None)
        mocker.patch("model_lens.camera_capture.time.time", return_value=1000.0)
        mocker.patch("model_lens.camera_capture.random.uniform", return_value=0.0)

        call_log: list[str] = []
        real_lock = threading.Lock()

        class SpyLock:
            """Lock wrapper that logs acquire/release calls."""

            def acquire(self, *args, **kwargs):  # noqa: D102
                call_log.append("lock_acquire")
                return real_lock.acquire(*args, **kwargs)

            def release(self):  # noqa: D102
                call_log.append("lock_release")
                return real_lock.release()

            def __enter__(self):  # noqa: D105
                self.acquire()
                return self

            def __exit__(self, *args):  # noqa: D105
                self.release()

        spy_lock = SpyLock()

        def fake_sleep(seconds: float) -> None:
            call_log.append("sleep")

        mocker.patch("model_lens.camera_capture.time.sleep", side_effect=fake_sleep)

        fresh_cap = MagicMock()
        fresh_cap.read.return_value = (True, fake_array)
        reopen_fn = MagicMock(return_value=fresh_cap)

        _retry_read(mock_cap, reopen_fn, "source", spy_lock)  # type: ignore[arg-type]

        # Verify sleep happens outside lock (between release and next acquire)
        for i, entry in enumerate(call_log):
            if entry == "sleep":
                # Find surrounding lock operations
                assert i > 0
                # Sleep should occur after a lock_release and before the next lock_acquire
                preceding = call_log[:i]
                assert "lock_release" in preceding

    def test_retry_read_wait_schedule(self, mocker: MockerFixture) -> None:
        """Wait durations follow the exponential backoff schedule plus jitter."""
        mock_cap = MagicMock()
        mock_cap.read.return_value = (False, None)
        mock_sleep = mocker.patch("model_lens.camera_capture.time.sleep")
        mocker.patch("model_lens.camera_capture.random.uniform", return_value=0.25)

        mock_lock = MagicMock(spec=threading.Lock)
        mock_lock.acquire.return_value = True

        fresh_cap = MagicMock()
        fresh_cap.read.return_value = (False, None)
        reopen_fn = MagicMock(return_value=fresh_cap)

        with pytest.raises(OperationError):
            _retry_read(mock_cap, reopen_fn, "source", mock_lock)

        # Backoff schedule: base waits (1, 2, 4) + jitter 0.25
        expected_calls = [call(1.25), call(2.25), call(4.25)]
        assert mock_sleep.call_args_list == expected_calls

    def test_retry_read_timestamp_captured_after_read(self, mocker: MockerFixture) -> None:
        """time.time() is called after cap.read() succeeds, not before."""
        fake_array = np.ones((480, 640, 3), dtype=np.uint8)
        mock_cap = MagicMock()

        call_order: list[str] = []

        def tracked_read():
            call_order.append("cap.read")
            return (True, fake_array)

        def tracked_time():
            call_order.append("time.time")
            return 9999.0

        mock_cap.read.side_effect = tracked_read
        mocker.patch("model_lens.camera_capture.time.time", side_effect=tracked_time)
        mocker.patch("model_lens.camera_capture.random.uniform", return_value=0.0)

        mock_lock = MagicMock(spec=threading.Lock)
        mock_lock.acquire.return_value = True
        reopen_fn = MagicMock()

        _retry_read(mock_cap, reopen_fn, "source", mock_lock)

        read_idx = call_order.index("cap.read")
        time_idx = call_order.index("time.time")
        assert time_idx > read_idx
