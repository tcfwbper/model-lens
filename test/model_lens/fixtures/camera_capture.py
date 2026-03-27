import numpy as np
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture()
def mock_cap_opened() -> MagicMock:
    """Return a mock cv2.VideoCapture that reports as opened."""
    cap = MagicMock()
    cap.isOpened.return_value = True
    return cap


@pytest.fixture()
def mock_cap_closed() -> MagicMock:
    """Return a mock cv2.VideoCapture that reports as NOT opened."""
    cap = MagicMock()
    cap.isOpened.return_value = False
    return cap


@pytest.fixture()
def valid_bgr_frame() -> np.ndarray:
    """Return a valid 480x640 BGR NumPy array."""
    return np.zeros((480, 640, 3), dtype=np.uint8)
