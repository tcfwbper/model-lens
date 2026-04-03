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
"""Inference engine abstraction and concrete YOLO backend for ModelLens.

Defines :class:`InferenceEngine` (abstract base class) and
:class:`YOLOInferenceEngine` (MVP YOLO backend), plus the module-level
:data:`ENGINE_REGISTRY` that maps backend name strings to subclasses.
"""

from __future__ import annotations

import abc
import logging
import threading

import numpy as np
from numpy.typing import NDArray
from ultralytics import YOLO  # type: ignore[attr-defined]
from ultralytics.engine.results import Results

from model_lens.entities import DetectionResult
from model_lens.exceptions import ConfigurationError, OperationError

logger = logging.getLogger(__name__)


class InferenceEngine(abc.ABC):
    """Abstract base class for all inference engine backends.

    Loads and owns the label map at construction time. Subclasses implement
    :meth:`detect` to run backend-specific inference.
    """

    @abc.abstractmethod
    def __init__(self) -> None:
        """Initialize the inference engine."""
        self._label_map: dict[int, str] = self._get_label_map()

    @abc.abstractmethod
    def _get_label_map(self) -> dict[int, str]:
        """Get the label map."""

    @abc.abstractmethod
    def get_label_map(self) -> dict[int, str]:
        """Public accessor for the label map."""

    @abc.abstractmethod
    def detect(
        self,
        frame: NDArray[np.uint8],
        target_labels: list[str],
    ) -> list[DetectionResult]:
        """Run inference on a single BGR frame and return filtered detections."""

    @abc.abstractmethod
    def teardown(self) -> None:
        """Release all resources held by the engine.

        After this method returns the engine is inert; any call to
        :meth:`detect` will raise :exc:`OperationError`.  Calling
        ``teardown()`` more than once is safe (subsequent calls are no-ops).
        """


class YOLOInferenceEngine(InferenceEngine):
    """Concrete inference engine backend using Ultralytics YOLO."""

    def __init__(
        self,
        model: str,
        confidence_threshold: float,
    ) -> None:
        """Initialize the YOLO inference engine."""
        if not 0.0 < confidence_threshold <= 1.0:
            raise ConfigurationError(
                f"confidence_threshold must satisfy 0.0 < value <= 1.0, got {confidence_threshold!r}"
            )

        self._confidence_threshold: float = confidence_threshold
        self._lock: threading.Lock = threading.Lock()
        self._torn_down: bool = False
        self._model: YOLO | None = self._load_model(model)
        super().__init__()

    @staticmethod
    def _load_model(model: str) -> YOLO:
        """Load a YOLO model from ``model``."""
        try:
            yolo_model = YOLO(model)
            logger.info("Model loaded successfully from %r", model)
            return yolo_model
        except Exception as exc:
            raise OperationError(f"Failed to load model {model!r}: {exc}") from exc

    def _get_label_map(self) -> dict[int, str]:
        """Get the label map from the loaded YOLO model."""
        if self._model is None:
            raise OperationError("Inference model is not loaded")
        return self._model.names

    def get_label_map(self) -> dict[int, str]:
        """Public accessor for the label map."""
        with self._lock:
            if self._torn_down:
                raise OperationError("get_label_map() called on a torn-down InferenceEngine instance")
            return self._label_map.copy()

    def detect(
        self,
        frame: NDArray[np.uint8],
        target_labels: list[str],
    ) -> list[DetectionResult]:
        """Run inference on a single BGR frame and return filtered detections."""
        with self._lock:
            if self._torn_down:
                raise OperationError("detect() called on a torn-down InferenceEngine instance")

            try:
                if self._model is None:
                    raise OperationError("Inference model is not loaded")
                raw_results: list[Results] = self._model(frame)
            except Exception as exc:
                raise OperationError(f"Inference call failed: {exc}") from exc

            results: list[DetectionResult] = []

            boxes = raw_results[0].boxes

            if boxes:
                for i in range(len(boxes)):
                    label: str = self._label_map[int(boxes.cls[i].item())]
                    confidence = float(boxes.conf[i].item())
                    h, w = frame.shape[:2]
                    x1, y1, x2, y2 = boxes.xyxy[i].tolist()
                    x1, y1, x2, y2 = float(x1), float(y1), float(x2), float(y2)
                    box = (x1 / w, y1 / h, x2 / w, y2 / h)  # normalised [0.0, 1.0]

                    if confidence < self._confidence_threshold:
                        continue

                    results.append(
                        DetectionResult(
                            label=label,
                            confidence=confidence,
                            bounding_box=box,
                            is_target=(label in target_labels),
                        )
                    )

            results.sort(key=lambda r: r.confidence, reverse=True)
            return results

    def teardown(self) -> None:
        """Release the model held by this engine.

        Idempotent: subsequent calls after the first are silent no-ops.
        Thread-safe: acquires the per-instance lock before clearing state.
        """
        with self._lock:
            if self._torn_down:
                return
            self._torn_down = True
            self._model = None
        logger.info("YOLOInferenceEngine torn down; model released.")


ENGINE_REGISTRY: dict[str, type[InferenceEngine]] = {
    "yolo": YOLOInferenceEngine,
}
