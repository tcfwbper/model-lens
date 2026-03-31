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
"""Detection pipeline for ModelLens.

Owns the background frame loop: reads frames from :class:`~model_lens.camera_capture.CameraCapture`,
runs inference via :class:`~model_lens.inference_engine.InferenceEngine`, converts BGR frames to
JPEG bytes, and publishes :class:`PipelineResult` objects to a bounded in-memory queue consumed
by the Stream API.
"""

from __future__ import annotations

import logging
import queue
import sys
import threading
import time
from dataclasses import dataclass

import cv2

from model_lens.camera_capture import LocalCamera, RtspCamera
from model_lens.entities import DetectionResult, LocalCameraConfig, RtspCameraConfig, RuntimeConfig
from model_lens.exceptions import DeviceNotFoundError, OperationError, ParseError
from model_lens.inference_engine import InferenceEngine

logger = logging.getLogger(__name__)

_MIN_INTER_FRAME_INTERVAL: float = 1.0 / 30


@dataclass(frozen=True)
class PipelineResult:
    """A single published output produced by one successful frame iteration.

    Args:
        jpeg_bytes: JPEG-encoded RGB image, converted from the original BGR frame before inference.
        timestamp: POSIX timestamp copied from :attr:`~model_lens.entities.Frame.timestamp`.
        source: Camera source identifier copied from :attr:`~model_lens.entities.Frame.source`.
        detections: Filtered, label-resolved detections from
            :meth:`~model_lens.inference_engine.InferenceEngine.detect`, ordered by descending
            confidence.
    """

    jpeg_bytes: bytes
    timestamp: float
    source: str
    detections: list[DetectionResult]


class DetectionPipeline:
    """Background component that owns the frame loop.

    Reads frames from :class:`~model_lens.camera_capture.CameraCapture`, runs inference via
    :class:`~model_lens.inference_engine.InferenceEngine`, converts the raw BGR frame to JPEG
    bytes, and publishes :class:`PipelineResult` objects to a bounded in-memory queue consumed
    by the Stream API.

    Args:
        engine: The shared inference engine instance, created once at server startup and never
            replaced.
        initial_config: The initial runtime configuration seeded from ``AppConfig`` at startup.
    """

    def __init__(
        self,
        engine: InferenceEngine,
        initial_config: RuntimeConfig,
    ) -> None:
        """Initialise the pipeline without starting the background thread.

        Args:
            engine: The shared inference engine instance.
            initial_config: The initial runtime configuration.
        """
        self._engine: InferenceEngine = engine
        self._config: RuntimeConfig = initial_config
        self._config_lock: threading.Lock = threading.Lock()

        self._queue: queue.Queue[PipelineResult] = queue.Queue(maxsize=5)
        self._stop_event: threading.Event = threading.Event()
        self._camera_changed_event: threading.Event = threading.Event()
        self._started: bool = False
        self._last_frame_time: float = 0.0

        self._camera: LocalCamera | RtspCamera | None = None
        self._thread: threading.Thread = threading.Thread(target=self._run, daemon=True)

        self._camera = self._build_camera(initial_config)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background frame loop thread.

        Raises:
            RuntimeError: If ``start()`` has already been called.
        """
        if self._started:
            raise RuntimeError("Pipeline is already running")
        self._started = True
        self._thread.start()

    def stop(self) -> None:
        """Signal the background thread to exit and block until it terminates.

        Closes the active :class:`~model_lens.camera_capture.CameraCapture` instance (if any)
        after the thread has exited. Safe to call more than once.
        """
        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join()
        if self._camera is not None:
            self._camera.close()

    def update_config(self, new_config: RuntimeConfig) -> None:
        """Replace the current :class:`~model_lens.entities.RuntimeConfig` atomically.

        Thread-safe. Returns immediately; camera recreation happens asynchronously inside the
        frame loop on the next iteration.

        Args:
            new_config: The new runtime configuration to apply.
        """
        with self._config_lock:
            self._config = new_config
        self._camera_changed_event.set()

    def get_config(self) -> RuntimeConfig:
        """Return the current :class:`~model_lens.entities.RuntimeConfig`.

        Thread-safe.

        Returns:
            The current runtime configuration.
        """
        with self._config_lock:
            return self._config

    def get_queue(self) -> queue.Queue[PipelineResult]:
        """Return the result queue.

        Returns:
            The bounded :class:`queue.Queue` that receives :class:`PipelineResult` objects.
        """
        return self._queue

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_camera(self, config: RuntimeConfig) -> LocalCamera | RtspCamera | None:
        """Construct a :class:`~model_lens.camera_capture.CameraCapture` from *config*.

        Args:
            config: The runtime configuration whose ``camera`` field determines the backend.

        Returns:
            A new camera capture instance, or ``None`` if construction fails.
        """
        try:
            if isinstance(config.camera, LocalCameraConfig):
                return LocalCamera(config.camera)
            if isinstance(config.camera, RtspCameraConfig):
                return RtspCamera(config.camera)
        except DeviceNotFoundError as exc:
            logger.error("Camera device not found during construction: %s", exc)
        return None

    # ------------------------------------------------------------------
    # Background thread entry point
    # ------------------------------------------------------------------

    def _run(self) -> None:
        """Entry point for the background frame loop thread.

        Runs until :attr:`_stop_event` is set.
        """
        while not self._stop_event.is_set():
            self._run_one_iteration()

    def _run_one_iteration(self) -> None:
        """Execute one iteration of the frame loop.

        Implements the 9-step pipeline:

        1. Check ``_camera_changed_event`` — recreate :class:`~model_lens.camera_capture.CameraCapture` if set.
        2. If no active camera — wait for ``_camera_changed_event``, then return.
        3. FPS throttle check — interruptible wait if within minimum inter-frame interval.
        4. Read a :class:`~model_lens.entities.Frame` from the camera.
        5. Convert BGR → RGB (copy; do not modify ``Frame.data``).
        6. JPEG-encode the RGB frame.
        7. Run inference via :meth:`~model_lens.inference_engine.InferenceEngine.detect`.
        8. Construct a :class:`PipelineResult`.
        9. Publish to the queue (drop oldest if full).
        """
        # ① Camera changed event
        if self._camera_changed_event.is_set():
            self._camera_changed_event.clear()
            if self._camera is not None:
                self._camera.close()
                self._camera = None
            with self._config_lock:
                current_config = self._config
            new_camera = self._build_camera(current_config)
            self._camera = new_camera

        # ② No active camera — wait for a new config
        if self._camera is None:
            self._camera_changed_event.wait(timeout=1.0)
            return

        # ③ FPS throttle
        if self._last_frame_time != 0.0:
            elapsed = time.monotonic() - self._last_frame_time
            remaining = _MIN_INTER_FRAME_INTERVAL - elapsed
            if remaining > 0:
                self._stop_event.wait(timeout=remaining)
                if self._stop_event.is_set():
                    return

        # ④ Frame read
        try:
            frame = self._camera.read()
        except OperationError as exc:
            logger.error("Camera read failed: %s", exc)
            self._camera.close()
            self._camera = None
            return

        # ⑤ BGR → RGB conversion
        rgb_frame = frame.data[:, :, ::-1].copy()

        # ⑥ JPEG encoding
        success, buffer = cv2.imencode(".jpg", rgb_frame)
        if not success:
            logger.warning("cv2.imencode failed; skipping frame from source %r", frame.source)
            return
        jpeg_bytes = buffer.tobytes()

        # ⑦ Inference — read target_labels under lock, then release before detect()
        with self._config_lock:
            target_labels = self._config.target_labels

        try:
            results = self._engine.detect(frame.data, target_labels)
        except OperationError as exc:
            logger.error("Inference engine detect() failed: %s", exc)
            return
        except ParseError as exc:
            logger.critical("Label map mismatch — model and label map are permanently mismatched: %s", exc)
            sys.exit(1)

        # ⑧ Construct PipelineResult
        pipeline_result = PipelineResult(
            jpeg_bytes=jpeg_bytes,
            timestamp=frame.timestamp,
            source=frame.source,
            detections=results,
        )

        # ⑨ Publish to queue (drop oldest if full)
        if self._queue.full():
            try:
                self._queue.get_nowait()
                logger.debug("Queue full; dropped oldest frame to make room for new result.")
            except queue.Empty:
                pass
        self._queue.put_nowait(pipeline_result)
        self._last_frame_time = time.monotonic()
