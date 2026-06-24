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

"""Detection pipeline — background frame loop with inference and queue publish.

Provides the ``PipelineResult`` frozen dataclass and ``DetectionPipeline`` class
that orchestrates frame acquisition, JPEG encoding, inference, and result
publication to a bounded in-memory queue.
"""

from __future__ import annotations

import logging
import os
import queue
import signal
import threading
import time
from dataclasses import dataclass

import cv2

from model_lens.camera_capture import LocalCamera, RtspCamera
from model_lens.entities import (
    DetectionResult,
    Frame,
    LocalCameraConfig,
    RtspCameraConfig,
    RuntimeConfig,
)
from model_lens.exceptions import DeviceNotFoundError, OperationError, ParseError
from model_lens.inference_engine import InferenceEngine

logger = logging.getLogger(__name__)

_FPS_CAP: float = 1.0 / 30
_QUEUE_MAXSIZE: int = 5


@dataclass(frozen=True)
class PipelineResult:
    """A single processed frame result ready for queue consumption.

    Args:
        jpeg_bytes: Complete JPEG buffer produced by cv2.imencode.
        timestamp: Timestamp copied from the source Frame.
        source: Source identifier copied from the source Frame.
        detections: List of DetectionResult objects from inference.
    """

    jpeg_bytes: bytes
    timestamp: float
    source: str
    detections: list[DetectionResult]


class DetectionPipeline:
    """Background frame loop: reads, encodes, infers, and publishes results.

    Owns the background thread lifecycle, camera construction/destruction in
    response to config changes, JPEG encoding, and queue publication with
    drop-oldest overflow policy.

    Args:
        engine: A fully initialised InferenceEngine instance (injected).
        initial_config: The initial RuntimeConfig for the pipeline.
    """

    def __init__(self, engine: InferenceEngine, initial_config: RuntimeConfig) -> None:
        """Initialize DetectionPipeline.

        Args:
            engine: A fully initialised InferenceEngine instance.
            initial_config: The initial RuntimeConfig.
        """
        self._engine: InferenceEngine = engine
        self._config: RuntimeConfig = initial_config
        self._config_lock: threading.Lock = threading.Lock()
        self._queue: queue.Queue[PipelineResult] = queue.Queue(maxsize=_QUEUE_MAXSIZE)
        self._stop_event: threading.Event = threading.Event()
        self._camera_changed_event: threading.Event = threading.Event()
        self._started: bool = False
        self._last_frame_time: float = 0.0
        self._camera: LocalCamera | RtspCamera | None = None
        self._thread: threading.Thread = threading.Thread(target=lambda: self._run(), daemon=True)

        # Attempt to build the initial camera
        self._camera = self._build_camera(initial_config)

    def start(self) -> None:
        """Start the background frame loop thread.

        Raises:
            RuntimeError: If the pipeline is already running.
        """
        if self._started:
            raise RuntimeError("Pipeline is already running")
        self._started = True
        self._thread.start()

    def stop(self) -> None:
        """Stop the background frame loop and close the camera.

        Idempotent — safe to call multiple times.
        Does NOT call engine.teardown().
        """
        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join()
        if self._camera is not None:
            self._camera.close()
            self._camera = None

    def update_config(self, new_config: RuntimeConfig) -> None:
        """Replace the current RuntimeConfig and signal camera change.

        Args:
            new_config: The new RuntimeConfig to apply.
        """
        with self._config_lock:
            self._config = new_config
        self._camera_changed_event.set()

    def get_config(self) -> RuntimeConfig:
        """Return the current RuntimeConfig.

        Returns:
            The current RuntimeConfig snapshot.
        """
        with self._config_lock:
            return self._config

    def get_queue(self) -> queue.Queue[PipelineResult]:
        """Return the bounded result queue.

        Returns:
            The internal queue that receives PipelineResult objects.
        """
        return self._queue

    def _build_camera(self, config: RuntimeConfig) -> LocalCamera | RtspCamera | None:
        """Construct a camera instance based on the config's camera field.

        Args:
            config: The RuntimeConfig whose camera field determines the type.

        Returns:
            A LocalCamera or RtspCamera instance, or None on failure.
        """
        try:
            if isinstance(config.camera, LocalCameraConfig):
                return LocalCamera(config.camera)
            if isinstance(config.camera, RtspCameraConfig):
                return RtspCamera(config.camera)
            # Unrecognised camera config type
            return None
        except DeviceNotFoundError:
            logger.error("Camera device not found during construction")
            return None

    def _run(self) -> None:
        """Main frame loop — runs until _stop_event is set."""
        while not self._stop_event.is_set():
            self._run_one_iteration()

    def _run_one_iteration(self) -> None:
        """Execute one cycle of the frame loop."""
        # Step 1 — Camera changed event
        if self._camera_changed_event.is_set():
            self._camera_changed_event.clear()
            if self._camera is not None:
                self._camera.close()
                self._camera = None
            with self._config_lock:
                current_config = self._config
            self._camera = self._build_camera(current_config)

        # Step 2 — No active camera
        if self._camera is None:
            self._camera_changed_event.wait(timeout=1.0)
            return

        # Step 3 — FPS throttle
        if self._last_frame_time != 0.0:
            now = time.monotonic()
            elapsed = now - self._last_frame_time
            remaining = _FPS_CAP - elapsed
            if remaining > 0:
                self._stop_event.wait(timeout=remaining)
                if self._stop_event.is_set():
                    return

        # Step 4 — Frame read
        try:
            frame: Frame = self._camera.read()
        except OperationError:
            logger.error("Camera read failed")
            self._camera.close()
            self._camera = None
            return

        # Step 5 — JPEG encoding
        success, buf = cv2.imencode(".jpg", frame.data)
        if not success:
            logger.warning("cv2.imencode failed, skipping frame")
            return
        jpeg_bytes: bytes = buf.tobytes()

        # Step 6 — Inference
        with self._config_lock:
            target_labels = self._config.target_labels

        try:
            detections: list[DetectionResult] = self._engine.detect(frame.data, target_labels)
        except OperationError:
            logger.error("Inference failed")
            return
        except ParseError:
            logger.critical("Unrecoverable ParseError from engine.detect()")
            self._stop_event.set()
            os.kill(os.getpid(), signal.SIGINT)
            return

        # Step 7 — Construct PipelineResult
        pipeline_result = PipelineResult(
            jpeg_bytes=jpeg_bytes,
            timestamp=frame.timestamp,
            source=frame.source,
            detections=detections,
        )

        # Step 8 — Publish to queue
        if self._queue.full():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
            logger.debug("Queue full, dropped oldest item")
        self._queue.put_nowait(pipeline_result)
        self._last_frame_time = time.monotonic()
