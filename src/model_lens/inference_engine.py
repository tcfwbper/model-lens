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
"""Inference engine abstraction and concrete PyTorch backend for ModelLens.

Defines :class:`InferenceEngine` (abstract base class) and
:class:`TorchInferenceEngine` (MVP PyTorch backend), plus the module-level
:data:`ENGINE_REGISTRY` that maps backend name strings to subclasses.
"""

from __future__ import annotations

import abc
import importlib.resources
import logging
import threading
from pathlib import Path

import numpy as np
import torch
from numpy.typing import NDArray
from torch import nn

from model_lens.entities import DetectionResult
from model_lens.exceptions import ConfigurationError, OperationError, ParseError

logger = logging.getLogger(__name__)

#: Package name used for importlib.resources fallback resolution.
_PACKAGE = "model_lens"


class InferenceEngine(abc.ABC):
    """Abstract base class for all inference engine backends.

    Loads and owns the label map at construction time. Subclasses implement
    :meth:`detect` to run backend-specific inference.

    Args:
        labels_path: Absolute path to the label map file. Must point to an
            existing, readable plain-text file.

    Raises:
        ConfigurationError: If ``labels_path`` does not exist or cannot be read.
        ParseError: If the label map file is empty or contains only blank lines.
    """

    def __init__(self, labels_path: str) -> None:
        """Load the label map from ``labels_path``."""
        self._label_map: dict[int, str] = self._load_label_map(labels_path)

    @classmethod
    def _resolve_package_resource(cls, filename: str) -> str:
        """Resolve a package-data resource filename to an absolute path string.

        Args:
            filename: The bare filename (e.g. ``"model.pt"``) to look up.

        Returns:
            The resolved absolute path string.

        Raises:
            FileNotFoundError: If the resource cannot be located.
        """
        try:
            ref = importlib.resources.files(_PACKAGE).joinpath(filename)
            return str(ref)
        except Exception as exc:
            raise FileNotFoundError(f"Package-data resource {filename!r} could not be resolved: {exc}") from exc

    @staticmethod
    def _load_label_map(labels_path: str) -> dict[int, str]:
        """Parse a plain-text label map file into an index-to-label dict."""
        path = Path(labels_path)

        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ConfigurationError(f"Label map file cannot be read or found: {labels_path!r}") from exc

        lines = raw.splitlines()

        if not lines:
            raise ParseError(f"Label map file is empty (zero lines): {labels_path!r}")

        label_map: dict[int, str] = {idx: line.strip() for idx, line in enumerate(lines)}

        if not any(v for v in label_map.values()):
            raise ParseError(f"Label map file contains only blank/whitespace lines: {labels_path!r}")

        logger.info("Loaded label map with %d entries from %r", len(label_map), labels_path)
        return label_map

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


class TorchInferenceEngine(InferenceEngine):
    """Concrete inference engine backend using PyTorch (``.pt`` model files)."""

    _DEFAULT_MODEL = "model.pt"
    _DEFAULT_LABELS = "labels.txt"

    def __init__(
        self,
        model_path: str,
        confidence_threshold: float,
        labels_path: str,
    ) -> None:
        """Initialize the PyTorch inference engine."""
        if not 0.0 < confidence_threshold <= 1.0:
            raise ConfigurationError(
                f"confidence_threshold must satisfy 0.0 < value <= 1.0, got {confidence_threshold!r}"
            )

        resolved_labels = self._resolve_path(labels_path, self._DEFAULT_LABELS, "labels_path")
        resolved_model = self._resolve_path(model_path, self._DEFAULT_MODEL, "model_path")

        super().__init__(resolved_labels)

        self._confidence_threshold: float = confidence_threshold
        self._lock: threading.Lock = threading.Lock()
        self._torn_down: bool = False
        self._model: nn.Module | None = self._load_model(resolved_model)

    @classmethod
    def _resolve_path(cls, user_path: str, default_filename: str, param_name: str) -> str:
        """Resolve a user-supplied path or fall back to package data."""
        if user_path:
            if not Path(user_path).exists():
                raise ConfigurationError(f"{param_name} file not found: {user_path!r}")
            return user_path

        try:
            return cls._resolve_package_resource(default_filename)
        except FileNotFoundError as exc:
            raise ConfigurationError(
                f"{param_name} is empty and the package-data resource "
                f"{default_filename!r} could not be resolved: {exc}"
            ) from exc

    @staticmethod
    def _load_model(model_path: str) -> nn.Module:
        """Load a PyTorch model from ``model_path``."""
        try:
            model: nn.Module = torch.load(model_path, map_location="cpu")
            logger.info("Model loaded successfully from %r", model_path)
            return model
        except Exception as exc:
            raise OperationError(f"Failed to load model from {model_path!r}: {exc}") from exc

    def detect(
        self,
        frame: NDArray[np.uint8],
        target_labels: list[str],
    ) -> list[DetectionResult]:
        """Run inference on a single BGR frame and return filtered detections."""
        with self._lock:
            if self._torn_down:
                raise OperationError("detect() called on a torn-down InferenceEngine instance")

            rgb_frame = frame[:, :, ::-1].copy()

            try:
                if self._model is None:
                    raise OperationError("Inference model is not loaded")
                raw_results = self._model(rgb_frame)
            except Exception as exc:
                raise OperationError(f"Inference call failed: {exc}") from exc

            results: list[DetectionResult] = []

            for detection in raw_results:
                index = int(detection["index"])
                confidence = float(detection["confidence"])
                box: tuple[float, float, float, float] = (
                    float(detection["box"][0]),
                    float(detection["box"][1]),
                    float(detection["box"][2]),
                    float(detection["box"][3]),
                )

                if confidence < self._confidence_threshold:
                    continue

                if index not in self._label_map:
                    raise ParseError(f"Raw model output index {index!r} has no entry in the label map")

                label = self._label_map[index]
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
        """Release the model and label map held by this engine.

        Idempotent: subsequent calls after the first are silent no-ops.
        Thread-safe: acquires the per-instance lock before clearing state.
        """
        with self._lock:
            if self._torn_down:
                return
            self._torn_down = True
            self._model = None
            self._label_map.clear()
        logger.info("TorchInferenceEngine torn down; model and label map released.")


ENGINE_REGISTRY: dict[str, type[InferenceEngine]] = {
    "torch": TorchInferenceEngine,
}
