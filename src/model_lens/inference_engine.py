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

"""Inference engine abstraction — model loading, inference, and result filtering.

Provides the ``InferenceEngine`` abstract base class, ``YOLOInferenceEngine``
concrete subclass, and the module-level ``ENGINE_REGISTRY``.
"""

from __future__ import annotations

import abc
import logging
import threading

import numpy as np
from numpy.typing import NDArray
from ultralytics import YOLO  # type: ignore[attr-defined]

from model_lens.entities import DetectionResult
from model_lens.exceptions import ConfigurationError, OperationError

logger = logging.getLogger(__name__)


class InferenceEngine(abc.ABC):
    """Abstract base class for inference engine backends.

    Subclasses must implement ``_get_label_map()``, ``get_label_map()``,
    ``detect()``, and ``teardown()``.
    """

    def __init__(self) -> None:
        """Initialize the inference engine and populate the label map."""
        self._label_map: dict[int, str] = self._get_label_map()

    @abc.abstractmethod
    def _get_label_map(self) -> dict[int, str]:
        """Return the backend-specific label map.

        Returns:
            A dictionary mapping class indices to label strings.
        """

    @abc.abstractmethod
    def get_label_map(self) -> dict[int, str]:
        """Return a copy of the label map.

        Returns:
            A dictionary mapping class indices to label strings.

        Raises:
            OperationError: If called after teardown.
        """

    @abc.abstractmethod
    def detect(self, frame: NDArray[np.uint8], target_labels: list[str]) -> list[DetectionResult]:
        """Run inference on a frame and return filtered detection results.

        Args:
            frame: BGR image array with shape (H, W, 3) and dtype uint8.
            target_labels: List of label strings to flag as targets.

        Returns:
            A list of DetectionResult objects sorted by descending confidence.

        Raises:
            OperationError: If inference fails or engine is torn down.
        """

    @abc.abstractmethod
    def teardown(self) -> None:
        """Release all model resources.

        Must be idempotent — multiple calls are safe.
        """


class YOLOInferenceEngine(InferenceEngine):
    """Concrete inference engine using Ultralytics YOLO.

    Loads a YOLO model at construction, runs inference per frame, filters
    detections by confidence threshold, and normalises bounding boxes.

    Args:
        model: Model name or path passed to YOLO() (e.g. "yolov8n.pt").
        confidence_threshold: Minimum confidence for inclusion, in (0.0, 1.0].

    Raises:
        ConfigurationError: If confidence_threshold is out of range.
        OperationError: If model loading fails.
    """

    def __init__(self, model: str, confidence_threshold: float) -> None:
        """Initialize YOLOInferenceEngine.

        Args:
            model: Model name or path passed to YOLO().
            confidence_threshold: Minimum confidence for inclusion, in (0.0, 1.0].

        Raises:
            ConfigurationError: If confidence_threshold is out of range.
            OperationError: If model loading fails.
        """
        # Validate confidence_threshold
        if not (0.0 < confidence_threshold <= 1.0):
            raise ConfigurationError(
                f"confidence_threshold must be in (0.0, 1.0], got {confidence_threshold}"
            )

        self._confidence_threshold = confidence_threshold
        self._lock = threading.Lock()
        self._torn_down = False

        # Load model
        self._model: YOLO | None = self._load_model(model)

        # Call super().__init__() which invokes _get_label_map()
        super().__init__()

        logger.info("YOLOInferenceEngine loaded model '%s'", model)

    @staticmethod
    def _load_model(model: str) -> YOLO:
        """Load a YOLO model.

        Args:
            model: Model name or path.

        Returns:
            The loaded YOLO model instance.

        Raises:
            OperationError: If model loading fails.
        """
        try:
            return YOLO(model)
        except Exception as exc:
            raise OperationError(f"Failed to load YOLO model '{model}'") from exc

    def _get_label_map(self) -> dict[int, str]:
        """Return the label map from the loaded YOLO model.

        Returns:
            A dictionary mapping class indices to label strings.

        Raises:
            OperationError: If model is None.
        """
        if self._model is None:
            raise OperationError("Model is not loaded")
        return self._model.names

    def get_label_map(self) -> dict[int, str]:
        """Return a copy of the label map.

        Returns:
            A dictionary mapping class indices to label strings.

        Raises:
            OperationError: If called after teardown.
        """
        with self._lock:
            if self._torn_down:
                raise OperationError("Engine has been torn down")
            return self._label_map.copy()

    def detect(self, frame: NDArray[np.uint8], target_labels: list[str]) -> list[DetectionResult]:
        """Run inference on a frame and return filtered detection results.

        Args:
            frame: BGR image array with shape (H, W, 3) and dtype uint8.
            target_labels: List of label strings to flag as targets.

        Returns:
            A list of DetectionResult objects sorted by descending confidence.

        Raises:
            OperationError: If inference fails, model is None, or engine is torn down.
        """
        with self._lock:
            if self._torn_down:
                raise OperationError("Engine has been torn down")
            if self._model is None:
                raise OperationError("Model is not loaded")

            try:
                raw_results = self._model(frame)
            except Exception as exc:
                raise OperationError("Inference failed") from exc

            results: list[DetectionResult] = []

            boxes = raw_results[0].boxes
            if not boxes:
                return results

            h, w = frame.shape[:2]

            for i in range(len(boxes.cls)):
                cls_id = int(boxes.cls[i].item())
                confidence = float(boxes.conf[i].item())

                if confidence < self._confidence_threshold:
                    continue

                label = self._label_map[cls_id]
                bbox_raw = boxes.xyxy[i].tolist()
                x1, y1, x2, y2 = bbox_raw[0], bbox_raw[1], bbox_raw[2], bbox_raw[3]

                # Normalise bounding box by frame dimensions
                bounding_box = (x1 / w, y1 / h, x2 / w, y2 / h)

                is_target = label in target_labels

                results.append(
                    DetectionResult(
                        label=label,
                        confidence=confidence,
                        bounding_box=bounding_box,
                        is_target=is_target,
                    )
                )

            # Sort by descending confidence
            results.sort(key=lambda r: r.confidence, reverse=True)

            return results

    def teardown(self) -> None:
        """Release the model reference.

        Idempotent — multiple calls are safe.
        """
        with self._lock:
            if self._torn_down:
                return
            self._torn_down = True
            self._model = None

        logger.info("YOLOInferenceEngine torn down")


ENGINE_REGISTRY: dict[str, type[InferenceEngine]] = {
    "yolo": YOLOInferenceEngine,
}
