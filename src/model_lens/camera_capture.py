# Copyright 2026 ModelLens Contributors
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

"""Camera capture abstraction — local and RTSP camera sources.

Provides the ``CameraCapture`` abstract base class, ``LocalCamera`` and
``RtspCamera`` concrete subclasses, and the ``_retry_read`` helper function.
"""

from __future__ import annotations

import abc
import logging
import random
import threading
import time
from collections.abc import Callable
from typing import cast

import cv2
import numpy as np
from numpy.typing import NDArray

from model_lens.entities import Frame, LocalCameraConfig, RtspCameraConfig
from model_lens.exceptions import DeviceNotFoundError, OperationError, ValidationError

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS: int = 3
_RETRY_BASE_WAITS: tuple[float, ...] = (1.0, 2.0, 4.0)


def _retry_read(
    open_cap: cv2.VideoCapture,
    reopen_fn: Callable[[], cv2.VideoCapture],
    source: str,
    lock: threading.Lock,
) -> Frame:
    """Attempt to read a frame with exponential backoff and jitter.

    Tries up to ``_MAX_ATTEMPTS`` times. On each failure, releases the current
    handle, sleeps with exponential backoff plus jitter, then reopens.

    Args:
        open_cap: An already-opened cv2.VideoCapture handle.
        reopen_fn: Callable returning a fresh opened VideoCapture handle.
        source: Human-readable source identifier for the Frame.
        lock: Per-instance threading lock for thread safety.

    Returns:
        A Frame containing the captured image data, timestamp, and source.

    Raises:
        OperationError: If all retry attempts are exhausted.
    """
    cap = open_cap

    for attempt in range(_MAX_ATTEMPTS):
        # Read under lock
        lock.acquire()
        try:
            success, raw = cap.read()
        finally:
            lock.release()

        if success and raw is not None:
            # Capture timestamp after successful read
            timestamp = time.time()
            data = cast(NDArray[np.uint8], raw.copy())
            return Frame(data=data, timestamp=timestamp, source=source)

        # Failed read: release cap under lock
        lock.acquire()
        try:
            cap.release()
        finally:
            lock.release()

        # Sleep outside lock (exponential backoff + jitter)
        jitter = random.uniform(0.0, 1.0)
        wait = _RETRY_BASE_WAITS[attempt] + jitter
        time.sleep(wait)

        # Reopen (except after the final attempt)
        if attempt < _MAX_ATTEMPTS - 1:
            lock.acquire()
            try:
                cap = reopen_fn()
            finally:
                lock.release()

    raise OperationError(f"All {_MAX_ATTEMPTS} read attempts exhausted for source '{source}'")


class CameraCapture(abc.ABC):
    """Abstract base class for camera sources.

    Subclasses must implement ``read()`` and ``close()``. Context manager
    support (``__enter__``/``__exit__``) is provided by this base class.
    """

    @abc.abstractmethod
    def read(self) -> Frame:
        """Read a single frame from the camera source.

        Returns:
            A Frame containing the captured image data.

        Raises:
            OperationError: If reading fails after retries.
        """

    @abc.abstractmethod
    def close(self) -> None:
        """Release the underlying camera handle.

        Must be idempotent — multiple calls are safe.
        """

    def __enter__(self) -> CameraCapture:
        """Enter the context manager.

        Returns:
            Self.
        """
        return self

    def __exit__(self, *args: object) -> None:
        """Exit the context manager, calling close()."""
        self.close()


class LocalCamera(CameraCapture):
    """Concrete camera capture for a locally attached camera device.

    Opens a cv2.VideoCapture at construction with the given device index.
    Thread-safe read access is provided via a per-instance lock.

    Args:
        config: A LocalCameraConfig specifying the device index.

    Raises:
        DeviceNotFoundError: If the device cannot be opened.
    """

    def __init__(self, config: LocalCameraConfig) -> None:
        """Initialize LocalCamera with the given configuration.

        Args:
            config: A LocalCameraConfig specifying the device index.

        Raises:
            DeviceNotFoundError: If the device cannot be opened.
        """
        self._device_index = config.device_index
        self._source = f"local:{config.device_index}"
        self._lock = threading.Lock()
        self._is_closed = False

        self._cap = cv2.VideoCapture(config.device_index)
        if not self._cap.isOpened():
            raise DeviceNotFoundError(f"Local camera device {config.device_index} not found")

        logger.info("LocalCamera opened device %d", config.device_index)

    @property
    def source(self) -> str:
        """Human-readable source identifier.

        Returns:
            Source string in the format 'local:{device_index}'.
        """
        return self._source

    def read(self) -> Frame:
        """Read a single frame from the local camera.

        Returns:
            A Frame with copied data, POSIX timestamp, and source string.

        Raises:
            OperationError: If all retry attempts are exhausted.
        """
        return _retry_read(self._cap, self._reopen, self._source, self._lock)

    def _reopen(self) -> cv2.VideoCapture:
        """Create a fresh VideoCapture handle for the device.

        Returns:
            A new cv2.VideoCapture opened with the device index.
        """
        self._cap = cv2.VideoCapture(self._device_index)
        return self._cap

    def close(self) -> None:
        """Release the underlying cv2 handle.

        Idempotent — multiple calls are safe.
        """
        self._lock.acquire()
        try:
            if not self._is_closed:
                self._cap.release()
                self._is_closed = True
                logger.info("LocalCamera closed device %d", self._device_index)
        finally:
            self._lock.release()


class RtspCamera(CameraCapture):
    """Concrete camera capture for an RTSP network camera stream.

    Opens a cv2.VideoCapture at construction with the given RTSP URL.
    Thread-safe read access is provided via a per-instance lock.

    Args:
        config: An RtspCameraConfig specifying the RTSP URL.

    Raises:
        ValidationError: If the URL does not start with 'rtsp://'.
        DeviceNotFoundError: If the stream cannot be opened.
    """

    def __init__(self, config: RtspCameraConfig) -> None:
        """Initialize RtspCamera with the given configuration.

        Args:
            config: An RtspCameraConfig specifying the RTSP URL.

        Raises:
            ValidationError: If the URL does not start with 'rtsp://'.
            DeviceNotFoundError: If the stream cannot be opened.
        """
        if not config.rtsp_url.startswith("rtsp://"):
            raise ValidationError(f"rtsp_url must start with 'rtsp://', got '{config.rtsp_url}'")

        self._rtsp_url = config.rtsp_url
        self._source = config.rtsp_url
        self._lock = threading.Lock()
        self._is_closed = False

        self._cap = cv2.VideoCapture(config.rtsp_url)
        if not self._cap.isOpened():
            raise DeviceNotFoundError(f"RTSP stream unreachable: {config.rtsp_url}")

        logger.info("RtspCamera opened stream %s", config.rtsp_url)

    @property
    def source(self) -> str:
        """Human-readable source identifier.

        Returns:
            The full RTSP URL string.
        """
        return self._source

    def read(self) -> Frame:
        """Read a single frame from the RTSP stream.

        Returns:
            A Frame with copied data, POSIX timestamp, and source string.

        Raises:
            OperationError: If all retry attempts are exhausted.
        """
        return _retry_read(self._cap, self._reopen, self._source, self._lock)

    def _reopen(self) -> cv2.VideoCapture:
        """Create a fresh VideoCapture handle for the RTSP stream.

        Returns:
            A new cv2.VideoCapture opened with the RTSP URL.
        """
        self._cap = cv2.VideoCapture(self._rtsp_url)
        return self._cap

    def close(self) -> None:
        """Release the underlying cv2 handle.

        Idempotent — multiple calls are safe.
        """
        self._lock.acquire()
        try:
            if not self._is_closed:
                self._cap.release()
                self._is_closed = True
                logger.info("RtspCamera closed stream %s", self._rtsp_url)
        finally:
            self._lock.release()
