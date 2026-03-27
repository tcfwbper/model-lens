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
"""Camera capture abstractions for ModelLens.

Defines the :class:`CameraCapture` abstract base class and its two concrete
subclasses :class:`LocalCamera` and :class:`RtspCamera`, which wrap
``cv2.VideoCapture`` and vend :class:`~model_lens.entities.Frame` objects to
the Detection Pipeline.
"""

from __future__ import annotations

import abc
import logging
import random
import threading
import time
from types import TracebackType

import cv2
import numpy as np

from model_lens.entities import Frame, LocalCameraConfig, RtspCameraConfig
from model_lens.exceptions import DeviceNotFoundError, OperationError, ValidationError

logger = logging.getLogger(__name__)

# Retry schedule: base wait in seconds before attempt 2, 3, and give-up.
_RETRY_BASE_WAITS: tuple[float, float, float] = (1.0, 2.0, 4.0)
_MAX_ATTEMPTS: int = 3


class CameraCapture(abc.ABC):
    """Abstract base class for all camera capture backends.

    Defines the public contract for acquiring :class:`~model_lens.entities.Frame`
    objects from a camera source. Concrete subclasses implement :meth:`read` and
    :meth:`close` for their respective source types.

    Supports the context manager protocol; :meth:`__exit__` always calls
    :meth:`close`.
    """

    @abc.abstractmethod
    def read(self) -> Frame:
        """Acquire and return the next frame from the camera source.

        Blocking call. Retries up to :data:`_MAX_ATTEMPTS` times on failure,
        re-opening the underlying capture handle between attempts.

        Returns:
            A :class:`~model_lens.entities.Frame` containing a copy of the
            captured BGR image, a POSIX timestamp, and the source identifier.

        Raises:
            OperationError: If all retry attempts are exhausted without
                obtaining a valid frame.
        """

    @abc.abstractmethod
    def close(self) -> None:
        """Release the underlying capture handle and any held resources.

        Idempotent: calling this method more than once is safe.
        """

    def __enter__(self) -> "CameraCapture":
        """Enter the context manager, returning ``self``.

        Returns:
            This :class:`CameraCapture` instance.
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the context manager, calling :meth:`close`.

        Args:
            exc_type: The exception type, if any.
            exc_val: The exception value, if any.
            exc_tb: The exception traceback, if any.
        """
        self.close()


def _retry_read(
    open_cap: "cv2.VideoCapture",
    reopen_fn: "callable[[], cv2.VideoCapture]",
    source: str,
    lock: threading.Lock,
) -> Frame:
    """Shared retry logic for both :class:`LocalCamera` and :class:`RtspCamera`.

    Attempts to read a frame up to :data:`_MAX_ATTEMPTS` times. On each failure
    the existing handle is released, a new one is opened via ``reopen_fn``, and
    the process waits ``base + jitter`` seconds before the next attempt.

    Args:
        open_cap: The already-opened ``cv2.VideoCapture`` handle to use for the
            first attempt.
        reopen_fn: A zero-argument callable that opens and returns a fresh
            ``cv2.VideoCapture`` handle.
        source: The human-readable source identifier stored on the returned
            :class:`~model_lens.entities.Frame`.
        lock: The per-instance lock, already held by the caller.

    Returns:
        A :class:`~model_lens.entities.Frame` on success.

    Raises:
        OperationError: If all :data:`_MAX_ATTEMPTS` attempts fail.
    """
    cap = open_cap
    for attempt in range(_MAX_ATTEMPTS):
        success, raw = cap.read()
        if success and raw is not None:
            timestamp = time.time()
            data: np.ndarray = raw.copy()
            return Frame(data=data, timestamp=timestamp, source=source)

        # This attempt failed — release the handle.
        cap.release()
        logger.warning("Frame read failed on attempt %d for source %r", attempt + 1, source)

        # Determine the wait duration (base + jitter).
        base_wait = _RETRY_BASE_WAITS[attempt]
        jitter = random.uniform(0.0, 1.0)
        wait = base_wait + jitter
        logger.debug("Waiting %.3f s before retry (base=%.1f, jitter=%.3f)", wait, base_wait, jitter)
        time.sleep(wait)

        if attempt + 1 < _MAX_ATTEMPTS:
            # Open a fresh handle for the next attempt.
            cap = reopen_fn()

    logger.error("All %d read attempts exhausted for source %r", _MAX_ATTEMPTS, source)
    raise OperationError(f"Failed to read a frame from {source!r} after {_MAX_ATTEMPTS} attempts")


class LocalCamera(CameraCapture):
    """Camera capture backend for a locally attached camera device.

    Opens ``cv2.VideoCapture(device_index)`` immediately on construction.

    Args:
        config: A :class:`~model_lens.entities.LocalCameraConfig` specifying the
            device index.

    Raises:
        DeviceNotFoundError: If the device cannot be opened on the first attempt.
    """

    def __init__(self, config: LocalCameraConfig) -> None:
        """Initialise the local camera capture.

        Args:
            config: The local camera configuration.

        Raises:
            DeviceNotFoundError: If ``cv2.VideoCapture`` cannot open the device.
        """
        self._device_index: int = config.device_index
        self.source: str = f"local:{config.device_index}"
        self._lock: threading.Lock = threading.Lock()
        self._cap: cv2.VideoCapture = cv2.VideoCapture(config.device_index)
        if not self._cap.isOpened():
            raise DeviceNotFoundError(
                f"LocalCamera: cannot open device index {config.device_index!r}"
            )
        logger.info("LocalCamera opened device index %d", config.device_index)

    def _reopen(self) -> "cv2.VideoCapture":
        """Open a fresh ``cv2.VideoCapture`` handle for the configured device index.

        Returns:
            A new ``cv2.VideoCapture`` instance.
        """
        return cv2.VideoCapture(self._device_index)

    def read(self) -> Frame:
        """Acquire and return the next frame from the local camera.

        Returns:
            A :class:`~model_lens.entities.Frame` with BGR image data, timestamp,
            and source identifier.

        Raises:
            OperationError: If all retry attempts are exhausted.
        """
        with self._lock:
            return _retry_read(
                open_cap=self._cap,
                reopen_fn=self._reopen,
                source=self.source,
                lock=self._lock,
            )

    def close(self) -> None:
        """Release the ``cv2.VideoCapture`` handle.

        Idempotent: safe to call multiple times.
        """
        with self._lock:
            if self._cap.isOpened():
                self._cap.release()
                logger.info("LocalCamera released device index %d", self._device_index)


class RtspCamera(CameraCapture):
    """Camera capture backend for an RTSP network camera stream.

    Opens ``cv2.VideoCapture(rtsp_url)`` immediately on construction.

    Args:
        config: A :class:`~model_lens.entities.RtspCameraConfig` specifying the
            RTSP URL.

    Raises:
        ValidationError: If ``rtsp_url`` does not start with ``rtsp://``.
        DeviceNotFoundError: If the RTSP stream cannot be opened on the first attempt.
    """

    def __init__(self, config: RtspCameraConfig) -> None:
        """Initialise the RTSP camera capture.

        Args:
            config: The RTSP camera configuration.

        Raises:
            ValidationError: If ``rtsp_url`` does not start with ``rtsp://``.
            DeviceNotFoundError: If ``cv2.VideoCapture`` cannot open the RTSP URL.
        """
        if not config.rtsp_url.startswith("rtsp://"):
            raise ValidationError(
                f"RtspCamera: rtsp_url must start with 'rtsp://', got {config.rtsp_url!r}"
            )
        self._rtsp_url: str = config.rtsp_url
        self.source: str = config.rtsp_url
        self._lock: threading.Lock = threading.Lock()
        self._cap: cv2.VideoCapture = cv2.VideoCapture(config.rtsp_url)
        if not self._cap.isOpened():
            raise DeviceNotFoundError(
                f"RtspCamera: cannot open RTSP URL {config.rtsp_url!r}"
            )
        logger.info("RtspCamera opened URL %r", config.rtsp_url)

    def _reopen(self) -> "cv2.VideoCapture":
        """Open a fresh ``cv2.VideoCapture`` handle for the configured RTSP URL.

        Returns:
            A new ``cv2.VideoCapture`` instance.
        """
        return cv2.VideoCapture(self._rtsp_url)

    def read(self) -> Frame:
        """Acquire and return the next frame from the RTSP stream.

        Returns:
            A :class:`~model_lens.entities.Frame` with BGR image data, timestamp,
            and source identifier.

        Raises:
            OperationError: If all retry attempts are exhausted.
        """
        with self._lock:
            return _retry_read(
                open_cap=self._cap,
                reopen_fn=self._reopen,
                source=self.source,
                lock=self._lock,
            )

    def close(self) -> None:
        """Release the ``cv2.VideoCapture`` handle.

        Idempotent: safe to call multiple times.
        """
        with self._lock:
            if self._cap.isOpened():
                self._cap.release()
                logger.info("RtspCamera released URL %r", self._rtsp_url)
