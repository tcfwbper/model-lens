import threading
import time
from unittest.mock import MagicMock, call, patch

import numpy as np
import pytest

from model_lens.camera_capture import CameraCapture, LocalCamera, RtspCamera
from model_lens.entities import Frame, LocalCameraConfig, RtspCameraConfig
from model_lens.exceptions import DeviceNotFoundError, OperationError, ValidationError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RTSP_URL = "rtsp://192.168.1.10/stream"
_RTSP_URL_PORT = "rtsp://192.168.1.10:554/stream"
_RTSP_URL_ROUTE = "rtsp://192.168.1.10:554/live/channel1"
_RTSP_URL_DOMAIN = "rtsp://example.com/stream"
_FIXED_TIMESTAMP = 1748000400.123456


def _make_opened_cap() -> MagicMock:
    cap = MagicMock()
    cap.isOpened.return_value = True
    return cap


def _make_closed_cap() -> MagicMock:
    cap = MagicMock()
    cap.isOpened.return_value = False
    return cap


def _valid_bgr_frame() -> np.ndarray:
    return np.zeros((480, 640, 3), dtype=np.uint8)


# ===========================================================================
# 1. LocalCamera
# ===========================================================================

# ---------------------------------------------------------------------------
# 1.1 Happy Path — Construction
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_local_camera_opens_capture_on_init() -> None:
    """cv2.VideoCapture is called with the device index on construction."""
    cap = _make_opened_cap()
    with patch("model_lens.camera_capture.cv2.VideoCapture", return_value=cap) as mock_vc:
        LocalCamera(LocalCameraConfig(device_index=2))
        mock_vc.assert_called_once_with(2)


@pytest.mark.unit
def test_local_camera_source_string() -> None:
    """`source` is set to `"local:<device_index>"`."""
    cap = _make_opened_cap()
    with patch("model_lens.camera_capture.cv2.VideoCapture", return_value=cap):
        cam = LocalCamera(LocalCameraConfig(device_index=2))
        assert cam.source == "local:2"


@pytest.mark.unit
def test_local_camera_source_string_zero() -> None:
    """`source` is set to `"local:0"` for default device index."""
    cap = _make_opened_cap()
    with patch("model_lens.camera_capture.cv2.VideoCapture", return_value=cap):
        cam = LocalCamera(LocalCameraConfig(device_index=0))
        assert cam.source == "local:0"


# ---------------------------------------------------------------------------
# 1.2 Validation Failures
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_local_camera_device_not_found_on_init() -> None:
    """`DeviceNotFoundError` is raised when `cap.isOpened()` returns `False`."""
    cap = _make_closed_cap()
    with patch("model_lens.camera_capture.cv2.VideoCapture", return_value=cap):
        with pytest.raises(DeviceNotFoundError):
            LocalCamera(LocalCameraConfig(device_index=0))


# ---------------------------------------------------------------------------
# 1.3 Happy Path — read()
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_local_camera_read_returns_frame() -> None:
    """A successful `read()` returns a `Frame` with correct fields."""
    arr = _valid_bgr_frame()
    cap = _make_opened_cap()
    cap.read.return_value = (True, arr)

    with patch("model_lens.camera_capture.cv2.VideoCapture", return_value=cap):
        with patch("model_lens.camera_capture.time.time", return_value=_FIXED_TIMESTAMP):
            cam = LocalCamera(LocalCameraConfig(device_index=0))
            frame = cam.read()

    assert frame.data.shape == (480, 640, 3)
    assert frame.data.dtype == np.uint8
    assert frame.timestamp == _FIXED_TIMESTAMP
    assert frame.source == "local:0"


@pytest.mark.unit
def test_local_camera_read_timestamp_within_bounds() -> None:
    """`frame.timestamp` is between `start_time` and `end_time`."""
    arr = _valid_bgr_frame()
    cap = _make_opened_cap()
    cap.read.return_value = (True, arr)

    with patch("model_lens.camera_capture.cv2.VideoCapture", return_value=cap):
        cam = LocalCamera(LocalCameraConfig(device_index=0))
        start_time = time.time()
        frame = cam.read()
        end_time = time.time()

    assert start_time <= frame.timestamp <= end_time


@pytest.mark.unit
def test_local_camera_read_data_is_copy() -> None:
    """`Frame.data` is independent of the buffer returned by `cap.read()`."""
    arr = np.ones((480, 640, 3), dtype=np.uint8) * 42
    cap = _make_opened_cap()
    cap.read.return_value = (True, arr)

    with patch("model_lens.camera_capture.cv2.VideoCapture", return_value=cap):
        cam = LocalCamera(LocalCameraConfig(device_index=0))
        frame = cam.read()

    original_value = frame.data[0, 0, 0]
    arr[0, 0, 0] = 255
    assert frame.data[0, 0, 0] == original_value


# ---------------------------------------------------------------------------
# 1.4 Error Propagation
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_local_camera_read_retries_on_failure_then_succeeds() -> None:
    """When the first `cap.read()` fails, a new handle is opened and the second attempt succeeds."""
    arr = _valid_bgr_frame()
    cap_fail = _make_opened_cap()
    cap_fail.read.return_value = (False, None)
    cap_ok = _make_opened_cap()
    cap_ok.read.return_value = (True, arr)

    side_effects = [cap_fail, cap_ok]

    with patch("model_lens.camera_capture.cv2.VideoCapture", side_effect=side_effects) as mock_vc:
        with patch("model_lens.camera_capture.time.sleep") as mock_sleep:
            with patch("model_lens.camera_capture.random.uniform", return_value=0.5):
                cam = LocalCamera(LocalCameraConfig(device_index=0))
                frame = cam.read()

    assert isinstance(frame, Frame)
    assert mock_vc.call_count == 2
    mock_sleep.assert_called_once_with(1.5)


@pytest.mark.unit
def test_local_camera_read_retries_sleep_arguments() -> None:
    """Sleep durations follow the base wait schedule with fixed jitter on each retry."""
    arr = _valid_bgr_frame()
    cap_fail1 = _make_opened_cap()
    cap_fail1.read.return_value = (False, None)
    cap_fail2 = _make_opened_cap()
    cap_fail2.read.return_value = (False, None)
    cap_ok = _make_opened_cap()
    cap_ok.read.return_value = (True, arr)

    side_effects = [cap_fail1, cap_fail2, cap_ok]

    with patch("model_lens.camera_capture.cv2.VideoCapture", side_effect=side_effects):
        with patch("model_lens.camera_capture.time.sleep") as mock_sleep:
            with patch("model_lens.camera_capture.random.uniform", return_value=0.5):
                cam = LocalCamera(LocalCameraConfig(device_index=0))
                cam.read()

    assert mock_sleep.call_args_list == [call(1.5), call(2.5)]


@pytest.mark.unit
def test_local_camera_read_raises_after_all_retries_exhausted() -> None:
    """`OperationError` is raised when all 3 attempts fail."""
    cap1 = _make_opened_cap()
    cap1.read.return_value = (False, None)
    cap2 = _make_opened_cap()
    cap2.read.return_value = (False, None)
    cap3 = _make_opened_cap()
    cap3.read.return_value = (False, None)

    side_effects = [cap1, cap2, cap3]

    with patch("model_lens.camera_capture.cv2.VideoCapture", side_effect=side_effects) as mock_vc:
        with patch("model_lens.camera_capture.time.sleep") as mock_sleep:
            with patch("model_lens.camera_capture.random.uniform", return_value=0.5):
                cam = LocalCamera(LocalCameraConfig(device_index=0))
                with pytest.raises(OperationError):
                    cam.read()

    assert mock_vc.call_count == 3
    assert mock_sleep.call_count == 3


@pytest.mark.unit
def test_local_camera_read_all_retries_exhausted_sleep_arguments() -> None:
    """All three sleep durations (1 s, 2 s, 4 s base) are used in order when all attempts are exhausted."""
    cap1 = _make_opened_cap()
    cap1.read.return_value = (False, None)
    cap2 = _make_opened_cap()
    cap2.read.return_value = (False, None)
    cap3 = _make_opened_cap()
    cap3.read.return_value = (False, None)

    side_effects = [cap1, cap2, cap3]

    with patch("model_lens.camera_capture.cv2.VideoCapture", side_effect=side_effects):
        with patch("model_lens.camera_capture.time.sleep") as mock_sleep:
            with patch("model_lens.camera_capture.random.uniform", return_value=0.5):
                cam = LocalCamera(LocalCameraConfig(device_index=0))
                with pytest.raises(OperationError):
                    cam.read()

    assert mock_sleep.call_args_list == [call(1.5), call(2.5), call(4.5)]


@pytest.mark.unit
def test_local_camera_read_retry_reopens_handle() -> None:
    """On each retry, the old handle is released and a new `cv2.VideoCapture` is opened."""
    arr = _valid_bgr_frame()
    cap1 = _make_opened_cap()
    cap1.read.return_value = (False, None)
    cap2 = _make_opened_cap()
    cap2.read.return_value = (False, None)
    cap3 = _make_opened_cap()
    cap3.read.return_value = (True, arr)

    side_effects = [cap1, cap2, cap3]

    with patch("model_lens.camera_capture.cv2.VideoCapture", side_effect=side_effects):
        with patch("model_lens.camera_capture.time.sleep"):
            with patch("model_lens.camera_capture.random.uniform", return_value=0.5):
                cam = LocalCamera(LocalCameraConfig(device_index=0))
                cam.read()

    cap1.release.assert_called_once()
    cap2.release.assert_called_once()


# ---------------------------------------------------------------------------
# 1.5 Resource Cleanup
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_local_camera_close_releases_capture() -> None:
    """`close()` calls `cap.release()` on the underlying handle."""
    cap = _make_opened_cap()
    with patch("model_lens.camera_capture.cv2.VideoCapture", return_value=cap):
        cam = LocalCamera(LocalCameraConfig(device_index=0))
        cam.close()
    cap.release.assert_called_once()


@pytest.mark.unit
def test_local_camera_close_is_idempotent() -> None:
    """Calling `close()` twice does not raise and does not call `cap.release()` a second time."""
    cap = _make_opened_cap()
    with patch("model_lens.camera_capture.cv2.VideoCapture", return_value=cap):
        cam = LocalCamera(LocalCameraConfig(device_index=0))
        cam.close()
        cam.close()
    cap.release.assert_called_once()


@pytest.mark.unit
def test_local_camera_context_manager_enter_returns_self() -> None:
    """`__enter__` returns the `LocalCamera` instance itself."""
    cap = _make_opened_cap()
    with patch("model_lens.camera_capture.cv2.VideoCapture", return_value=cap):
        instance = LocalCamera(LocalCameraConfig(device_index=0))
        result = instance.__enter__()
    assert result is instance


@pytest.mark.unit
def test_local_camera_context_manager_exit_calls_close() -> None:
    """`__exit__` calls `close()`, releasing the capture handle."""
    cap = _make_opened_cap()
    with patch("model_lens.camera_capture.cv2.VideoCapture", return_value=cap):
        with LocalCamera(LocalCameraConfig(device_index=0)):
            pass
    cap.release.assert_called_once()


@pytest.mark.unit
def test_local_camera_context_manager_exit_calls_close_on_exception() -> None:
    """`__exit__` calls `close()` even when the body raises an exception."""
    cap = _make_opened_cap()
    with patch("model_lens.camera_capture.cv2.VideoCapture", return_value=cap):
        with pytest.raises(RuntimeError):
            with LocalCamera(LocalCameraConfig(device_index=0)):
                raise RuntimeError("boom")
    cap.release.assert_called_once()


# ---------------------------------------------------------------------------
# 1.6 Concurrent Behaviour
# ---------------------------------------------------------------------------


@pytest.mark.race
def test_local_camera_concurrent_read_and_close_no_crash() -> None:
    """Calling `read()` and `close()` concurrently does not raise an unhandled exception."""
    arr = _valid_bgr_frame()
    cap = _make_opened_cap()

    def slow_read(mock_cap: MagicMock) -> None:
        time.sleep(0.01)
        mock_cap.read.return_value = (True, arr)

    cap.read.side_effect = lambda: (time.sleep(0.01), (True, arr))[1]

    errors: list[Exception] = []

    with patch("model_lens.camera_capture.cv2.VideoCapture", return_value=cap):
        cam = LocalCamera(LocalCameraConfig(device_index=0))

    def do_read() -> None:
        try:
            cam.read()
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    def do_close() -> None:
        try:
            cam.close()
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    t1 = threading.Thread(target=do_read)
    t2 = threading.Thread(target=do_close)
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

    assert errors == []


@pytest.mark.race
def test_local_camera_close_blocks_until_read_completes() -> None:
    """`close()` blocks while `read()` holds the lock; completes only after `read()` returns."""
    arr = _valid_bgr_frame()
    cap = _make_opened_cap()

    read_acquired = threading.Event()
    read_may_finish = threading.Event()

    original_read = cap.read

    def blocking_read() -> tuple[bool, np.ndarray]:
        read_acquired.set()
        read_may_finish.wait(timeout=5)
        return (True, arr)

    cap.read.side_effect = blocking_read

    with patch("model_lens.camera_capture.cv2.VideoCapture", return_value=cap):
        cam = LocalCamera(LocalCameraConfig(device_index=0))

    close_completed = threading.Event()

    def do_read() -> None:
        cam.read()

    def do_close() -> None:
        close_completed.clear()
        cam.close()
        close_completed.set()

    t_read = threading.Thread(target=do_read)
    t_close = threading.Thread(target=do_close)

    t_read.start()
    read_acquired.wait(timeout=5)

    t_close.start()
    # Give close a moment to attempt acquiring the lock
    time.sleep(0.05)
    assert not close_completed.is_set(), "close() should not have completed while read() holds the lock"

    read_may_finish.set()
    t_read.join(timeout=5)
    t_close.join(timeout=5)

    assert close_completed.is_set(), "close() should have completed after read() released the lock"


# ===========================================================================
# 2. RtspCamera
# ===========================================================================

# ---------------------------------------------------------------------------
# 2.1 Happy Path — Construction
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_rtsp_camera_opens_capture_on_init_domain() -> None:
    """`cv2.VideoCapture` is called with a domain-name RTSP URL."""
    cap = _make_opened_cap()
    with patch("model_lens.camera_capture.cv2.VideoCapture", return_value=cap) as mock_vc:
        RtspCamera(RtspCameraConfig(rtsp_url=_RTSP_URL_DOMAIN))
        mock_vc.assert_called_once_with(_RTSP_URL_DOMAIN)


@pytest.mark.unit
def test_rtsp_camera_opens_capture_on_init_ip_port() -> None:
    """`cv2.VideoCapture` is called with an IP+port RTSP URL."""
    cap = _make_opened_cap()
    with patch("model_lens.camera_capture.cv2.VideoCapture", return_value=cap) as mock_vc:
        RtspCamera(RtspCameraConfig(rtsp_url=_RTSP_URL_PORT))
        mock_vc.assert_called_once_with(_RTSP_URL_PORT)


@pytest.mark.unit
def test_rtsp_camera_opens_capture_on_init_ip_port_route() -> None:
    """`cv2.VideoCapture` is called with an IP+port+route RTSP URL."""
    cap = _make_opened_cap()
    with patch("model_lens.camera_capture.cv2.VideoCapture", return_value=cap) as mock_vc:
        RtspCamera(RtspCameraConfig(rtsp_url=_RTSP_URL_ROUTE))
        mock_vc.assert_called_once_with(_RTSP_URL_ROUTE)


@pytest.mark.unit
def test_rtsp_camera_source_string() -> None:
    """`source` is set to the full RTSP URL."""
    cap = _make_opened_cap()
    with patch("model_lens.camera_capture.cv2.VideoCapture", return_value=cap):
        cam = RtspCamera(RtspCameraConfig(rtsp_url=_RTSP_URL))
        assert cam.source == _RTSP_URL


# ---------------------------------------------------------------------------
# 2.2 Validation Failures
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_rtsp_camera_invalid_url_no_scheme() -> None:
    """URL without `rtsp://` scheme raises `ValidationError`."""
    with pytest.raises(ValidationError):
        RtspCamera(RtspCameraConfig(rtsp_url="http://192.168.1.10/stream"))


@pytest.mark.unit
def test_rtsp_camera_invalid_url_rtsps_scheme() -> None:
    """`rtsps://` (TLS) URL raises `ValidationError`."""
    with pytest.raises(ValidationError):
        RtspCamera(RtspCameraConfig(rtsp_url="rtsps://192.168.1.10/stream"))


@pytest.mark.unit
def test_rtsp_camera_device_not_found_on_init() -> None:
    """`DeviceNotFoundError` is raised when `cap.isOpened()` returns `False`."""
    cap = _make_closed_cap()
    with patch("model_lens.camera_capture.cv2.VideoCapture", return_value=cap):
        with pytest.raises(DeviceNotFoundError):
            RtspCamera(RtspCameraConfig(rtsp_url=_RTSP_URL))


# ---------------------------------------------------------------------------
# 2.3 Happy Path — read()
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_rtsp_camera_read_returns_frame() -> None:
    """A successful `read()` returns a `Frame` with correct fields."""
    arr = _valid_bgr_frame()
    cap = _make_opened_cap()
    cap.read.return_value = (True, arr)

    with patch("model_lens.camera_capture.cv2.VideoCapture", return_value=cap):
        with patch("model_lens.camera_capture.time.time", return_value=_FIXED_TIMESTAMP):
            cam = RtspCamera(RtspCameraConfig(rtsp_url=_RTSP_URL))
            frame = cam.read()

    assert frame.data.shape == (480, 640, 3)
    assert frame.data.dtype == np.uint8
    assert frame.timestamp == _FIXED_TIMESTAMP
    assert frame.source == _RTSP_URL


@pytest.mark.unit
def test_rtsp_camera_read_timestamp_within_bounds() -> None:
    """`frame.timestamp` is between `start_time` and `end_time`."""
    arr = _valid_bgr_frame()
    cap = _make_opened_cap()
    cap.read.return_value = (True, arr)

    with patch("model_lens.camera_capture.cv2.VideoCapture", return_value=cap):
        cam = RtspCamera(RtspCameraConfig(rtsp_url=_RTSP_URL))
        start_time = time.time()
        frame = cam.read()
        end_time = time.time()

    assert start_time <= frame.timestamp <= end_time


@pytest.mark.unit
def test_rtsp_camera_read_data_is_copy() -> None:
    """`Frame.data` is independent of the buffer returned by `cap.read()`."""
    arr = np.ones((480, 640, 3), dtype=np.uint8) * 42
    cap = _make_opened_cap()
    cap.read.return_value = (True, arr)

    with patch("model_lens.camera_capture.cv2.VideoCapture", return_value=cap):
        cam = RtspCamera(RtspCameraConfig(rtsp_url=_RTSP_URL))
        frame = cam.read()

    original_value = frame.data[0, 0, 0]
    arr[0, 0, 0] = 255
    assert frame.data[0, 0, 0] == original_value


# ---------------------------------------------------------------------------
# 2.4 Error Propagation
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_rtsp_camera_read_retries_on_failure_then_succeeds() -> None:
    """When the first `cap.read()` fails, a new handle is opened and the second attempt succeeds."""
    arr = _valid_bgr_frame()
    cap_fail = _make_opened_cap()
    cap_fail.read.return_value = (False, None)
    cap_ok = _make_opened_cap()
    cap_ok.read.return_value = (True, arr)

    side_effects = [cap_fail, cap_ok]

    with patch("model_lens.camera_capture.cv2.VideoCapture", side_effect=side_effects) as mock_vc:
        with patch("model_lens.camera_capture.time.sleep") as mock_sleep:
            with patch("model_lens.camera_capture.random.uniform", return_value=0.5):
                cam = RtspCamera(RtspCameraConfig(rtsp_url=_RTSP_URL))
                frame = cam.read()

    assert isinstance(frame, Frame)
    assert mock_vc.call_count == 2
    mock_sleep.assert_called_once_with(1.5)


@pytest.mark.unit
def test_rtsp_camera_read_retries_sleep_arguments() -> None:
    """Sleep durations follow the base wait schedule with fixed jitter on each retry."""
    arr = _valid_bgr_frame()
    cap_fail1 = _make_opened_cap()
    cap_fail1.read.return_value = (False, None)
    cap_fail2 = _make_opened_cap()
    cap_fail2.read.return_value = (False, None)
    cap_ok = _make_opened_cap()
    cap_ok.read.return_value = (True, arr)

    side_effects = [cap_fail1, cap_fail2, cap_ok]

    with patch("model_lens.camera_capture.cv2.VideoCapture", side_effect=side_effects):
        with patch("model_lens.camera_capture.time.sleep") as mock_sleep:
            with patch("model_lens.camera_capture.random.uniform", return_value=0.5):
                cam = RtspCamera(RtspCameraConfig(rtsp_url=_RTSP_URL))
                cam.read()

    assert mock_sleep.call_args_list == [call(1.5), call(2.5)]


@pytest.mark.unit
def test_rtsp_camera_read_raises_after_all_retries_exhausted() -> None:
    """`OperationError` is raised when all 3 attempts fail."""
    cap1 = _make_opened_cap()
    cap1.read.return_value = (False, None)
    cap2 = _make_opened_cap()
    cap2.read.return_value = (False, None)
    cap3 = _make_opened_cap()
    cap3.read.return_value = (False, None)

    side_effects = [cap1, cap2, cap3]

    with patch("model_lens.camera_capture.cv2.VideoCapture", side_effect=side_effects) as mock_vc:
        with patch("model_lens.camera_capture.time.sleep") as mock_sleep:
            with patch("model_lens.camera_capture.random.uniform", return_value=0.5):
                cam = RtspCamera(RtspCameraConfig(rtsp_url=_RTSP_URL))
                with pytest.raises(OperationError):
                    cam.read()

    assert mock_vc.call_count == 3
    assert mock_sleep.call_count == 3


@pytest.mark.unit
def test_rtsp_camera_read_all_retries_exhausted_sleep_arguments() -> None:
    """All three sleep durations (1 s, 2 s, 4 s base) are used in order when all attempts are exhausted."""
    cap1 = _make_opened_cap()
    cap1.read.return_value = (False, None)
    cap2 = _make_opened_cap()
    cap2.read.return_value = (False, None)
    cap3 = _make_opened_cap()
    cap3.read.return_value = (False, None)

    side_effects = [cap1, cap2, cap3]

    with patch("model_lens.camera_capture.cv2.VideoCapture", side_effect=side_effects):
        with patch("model_lens.camera_capture.time.sleep") as mock_sleep:
            with patch("model_lens.camera_capture.random.uniform", return_value=0.5):
                cam = RtspCamera(RtspCameraConfig(rtsp_url=_RTSP_URL))
                with pytest.raises(OperationError):
                    cam.read()

    assert mock_sleep.call_args_list == [call(1.5), call(2.5), call(4.5)]


@pytest.mark.unit
def test_rtsp_camera_read_retry_reopens_handle() -> None:
    """On each retry, the old handle is released and a new `cv2.VideoCapture` is opened."""
    arr = _valid_bgr_frame()
    cap1 = _make_opened_cap()
    cap1.read.return_value = (False, None)
    cap2 = _make_opened_cap()
    cap2.read.return_value = (False, None)
    cap3 = _make_opened_cap()
    cap3.read.return_value = (True, arr)

    side_effects = [cap1, cap2, cap3]

    with patch("model_lens.camera_capture.cv2.VideoCapture", side_effect=side_effects):
        with patch("model_lens.camera_capture.time.sleep"):
            with patch("model_lens.camera_capture.random.uniform", return_value=0.5):
                cam = RtspCamera(RtspCameraConfig(rtsp_url=_RTSP_URL))
                cam.read()

    cap1.release.assert_called_once()
    cap2.release.assert_called_once()


# ---------------------------------------------------------------------------
# 2.5 Resource Cleanup
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_rtsp_camera_close_releases_capture() -> None:
    """`close()` calls `cap.release()` on the underlying handle."""
    cap = _make_opened_cap()
    with patch("model_lens.camera_capture.cv2.VideoCapture", return_value=cap):
        cam = RtspCamera(RtspCameraConfig(rtsp_url=_RTSP_URL))
        cam.close()
    cap.release.assert_called_once()


@pytest.mark.unit
def test_rtsp_camera_close_is_idempotent() -> None:
    """Calling `close()` twice does not raise and does not call `cap.release()` a second time."""
    cap = _make_opened_cap()
    with patch("model_lens.camera_capture.cv2.VideoCapture", return_value=cap):
        cam = RtspCamera(RtspCameraConfig(rtsp_url=_RTSP_URL))
        cam.close()
        cam.close()
    cap.release.assert_called_once()


@pytest.mark.unit
def test_rtsp_camera_context_manager_enter_returns_self() -> None:
    """`__enter__` returns the `RtspCamera` instance itself."""
    cap = _make_opened_cap()
    with patch("model_lens.camera_capture.cv2.VideoCapture", return_value=cap):
        instance = RtspCamera(RtspCameraConfig(rtsp_url=_RTSP_URL))
        result = instance.__enter__()
    assert result is instance


@pytest.mark.unit
def test_rtsp_camera_context_manager_exit_calls_close() -> None:
    """`__exit__` calls `close()`, releasing the capture handle."""
    cap = _make_opened_cap()
    with patch("model_lens.camera_capture.cv2.VideoCapture", return_value=cap):
        with RtspCamera(RtspCameraConfig(rtsp_url=_RTSP_URL)):
            pass
    cap.release.assert_called_once()


@pytest.mark.unit
def test_rtsp_camera_context_manager_exit_calls_close_on_exception() -> None:
    """`__exit__` calls `close()` even when the body raises an exception."""
    cap = _make_opened_cap()
    with patch("model_lens.camera_capture.cv2.VideoCapture", return_value=cap):
        with pytest.raises(RuntimeError):
            with RtspCamera(RtspCameraConfig(rtsp_url=_RTSP_URL)):
                raise RuntimeError("boom")
    cap.release.assert_called_once()


# ---------------------------------------------------------------------------
# 2.6 Concurrent Behaviour
# ---------------------------------------------------------------------------


@pytest.mark.race
def test_rtsp_camera_concurrent_read_and_close_no_crash() -> None:
    """Calling `read()` and `close()` concurrently does not raise an unhandled exception."""
    arr = _valid_bgr_frame()
    cap = _make_opened_cap()
    cap.read.side_effect = lambda: (time.sleep(0.01), (True, arr))[1]

    errors: list[Exception] = []

    with patch("model_lens.camera_capture.cv2.VideoCapture", return_value=cap):
        cam = RtspCamera(RtspCameraConfig(rtsp_url=_RTSP_URL))

    def do_read() -> None:
        try:
            cam.read()
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    def do_close() -> None:
        try:
            cam.close()
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    t1 = threading.Thread(target=do_read)
    t2 = threading.Thread(target=do_close)
    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

    assert errors == []


@pytest.mark.race
def test_rtsp_camera_close_blocks_until_read_completes() -> None:
    """`close()` blocks while `read()` holds the lock; completes only after `read()` returns."""
    arr = _valid_bgr_frame()
    cap = _make_opened_cap()

    read_acquired = threading.Event()
    read_may_finish = threading.Event()

    def blocking_read() -> tuple[bool, np.ndarray]:
        read_acquired.set()
        read_may_finish.wait(timeout=5)
        return (True, arr)

    cap.read.side_effect = blocking_read

    with patch("model_lens.camera_capture.cv2.VideoCapture", return_value=cap):
        cam = RtspCamera(RtspCameraConfig(rtsp_url=_RTSP_URL))

    close_completed = threading.Event()

    def do_read() -> None:
        cam.read()

    def do_close() -> None:
        close_completed.clear()
        cam.close()
        close_completed.set()

    t_read = threading.Thread(target=do_read)
    t_close = threading.Thread(target=do_close)

    t_read.start()
    read_acquired.wait(timeout=5)

    t_close.start()
    time.sleep(0.05)
    assert not close_completed.is_set(), "close() should not have completed while read() holds the lock"

    read_may_finish.set()
    t_read.join(timeout=5)
    t_close.join(timeout=5)

    assert close_completed.is_set(), "close() should have completed after read() released the lock"
