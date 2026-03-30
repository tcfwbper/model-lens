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

from model_lens.entities import DetectionResult
from model_lens.exceptions import (
    ConfigurationError,
    OperationError,
    ParseError,
)

logger = logging.getLogger(__name__)

#: Package name used for importlib.resources fallback resolution.
_PACKAGE = "model_lens"


def _resolve_package_resource(filename: str) -> str:
    """Resolve a package-data resource filename to an absolute path string.

    Uses :mod:`importlib.resources` to locate a file bundled inside the
    ``model_lens`` package data directory.

    Args:
        filename: The bare filename (e.g. ``"model.pt"`` or ``"labels.txt"``)
            to look up inside the package data.

    Returns:
        The resolved absolute path string for the resource.

    Raises:
        FileNotFoundError: If the resource cannot be located (e.g. the package
            was not installed correctly or the data file is missing from the
            distribution).
    """
    try:
        ref = importlib.resources.files(_PACKAGE).joinpath(filename)
        resolved = str(ref)
        return resolved
    except Exception as exc:
        raise FileNotFoundError(
            f"Package-data resource {filename!r} could not be resolved: {exc}"
        ) from exc


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
        """Load the label map from ``labels_path``.

        Args:
            labels_path: Absolute path to the label map plain-text file.

        Raises:
            ConfigurationError: If the file does not exist or cannot be read.
            ParseError: If the file is empty or contains only blank/whitespace lines.
        """
        self._label_map: dict[int, str] = self._load_label_map(labels_path)

    @staticmethod
    def _load_label_map(labels_path: str) -> dict[int, str]:
        """Parse a plain-text label map file into an index-to-label dict.

        Every line (including blank and whitespace-only lines) consumes one
        index slot. Non-blank lines have leading/trailing whitespace stripped;
        blank/whitespace-only lines are stored as ``""``.

        Args:
            labels_path: Absolute path to the label map file.

        Returns:
            A dict mapping integer index to label string.

        Raises:
            ConfigurationError: If the file does not exist or cannot be read.
            ParseError: If the file is empty or contains only blank/whitespace lines.
        """
        path = Path(labels_path)
        if not path.exists():
            raise ConfigurationError(f"Label map file not found: {labels_path!r}")

        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ConfigurationError(f"Label map file cannot be read: {labels_path!r}") from exc

        lines = raw.splitlines()

        if not lines:
            raise ParseError(f"Label map file is empty (zero lines): {labels_path!r}")

        label_map: dict[int, str] = {}
        for idx, line in enumerate(lines):
            label_map[idx] = line.strip()  # blank/whitespace-only lines → ""

        if not any(v for v in label_map.values()):
            raise ParseError(f"Label map file contains only blank/whitespace lines: {labels_path!r}")

        logger.info("Loaded label map with %d entries from %r", len(label_map), labels_path)
        return label_map

    @abc.abstractmethod
    def detect(
        self,
        frame: np.ndarray,
        target_labels: list[str],
    ) -> list[DetectionResult]:
        """Run inference on a single BGR frame and return filtered detections.

        Args:
            frame: BGR image array with shape ``(H, W, 3)`` and dtype ``uint8``.
            target_labels: Current target label strings from ``RuntimeConfig``.
                Passed per call so the engine always uses the latest value
                without requiring a state update.

        Returns:
            A list of :class:`~model_lens.entities.DetectionResult` objects,
            filtered to those with ``confidence >= confidence_threshold``,
            ordered by descending confidence.

        Raises:
            ParseError: If a raw model output index has no entry in the label map.
            OperationError: If the inference call fails unexpectedly at runtime.
        """


class TorchInferenceEngine(InferenceEngine):
    """Concrete inference engine backend using PyTorch (``.pt`` model files).

    Loads a ``.pt`` model file at construction time and runs inference via
    PyTorch. Thread-safe: concurrent calls to :meth:`detect` are serialised
    by a per-instance :class:`threading.Lock`.

    Args:
        model_path: Absolute path to the ``.pt`` model file, or ``""`` to use
            the package-data default.
        confidence_threshold: Minimum confidence score (inclusive) for a
            detection to be included in results. Must satisfy
            ``0.0 < value <= 1.0``.
        labels_path: Absolute path to the label map file, or ``""`` to use
            the package-data default.

    Raises:
        ConfigurationError: If ``model_path`` is non-empty but the file does
            not exist, or if the package-data fallback cannot be resolved.
        ConfigurationError: If ``labels_path`` is non-empty but the file does
            not exist, or if the package-data fallback cannot be resolved.
        ConfigurationError: If ``confidence_threshold`` does not satisfy
            ``0.0 < value <= 1.0``.
        OperationError: If the model file exists but PyTorch fails to load it.
        ParseError: If the label map file is empty or contains only blank lines.
    """

    #: Default model asset filename inside the package data.
    _DEFAULT_MODEL = "model.pt"
    #: Default label map filename inside the package data.
    _DEFAULT_LABELS = "labels.txt"

    def __init__(
        self,
        model_path: str,
        confidence_threshold: float,
        labels_path: str,
    ) -> None:
        """Initialise the engine: resolve paths, validate threshold, load label map and model.

        Args:
            model_path: Absolute path to the ``.pt`` model file, or ``""`` for
                the package-data default.
            confidence_threshold: Minimum confidence (inclusive) for a detection
                to be returned. Must satisfy ``0.0 < value <= 1.0``.
            labels_path: Absolute path to the label map file, or ``""`` for
                the package-data default.

        Raises:
            ConfigurationError: If any path cannot be resolved or the threshold
                is out of range.
            OperationError: If PyTorch fails to load the model file.
            ParseError: If the label map is empty or all-blank.
        """
        if not 0.0 < confidence_threshold <= 1.0:
            raise ConfigurationError(
                f"confidence_threshold must satisfy 0.0 < value <= 1.0, got {confidence_threshold!r}"
            )

        resolved_labels = self._resolve_path(labels_path, self._DEFAULT_LABELS, "labels_path")
        resolved_model = self._resolve_path(model_path, self._DEFAULT_MODEL, "model_path")

        # Initialise base class (loads and validates the label map).
        super().__init__(resolved_labels)

        self._confidence_threshold: float = confidence_threshold
        self._lock: threading.Lock = threading.Lock()
        self._model = self._load_model(resolved_model)

    @staticmethod
    def _resolve_path(user_path: str, default_filename: str, param_name: str) -> str:
        """Resolve a user-supplied path or fall back to package data.

        Args:
            user_path: The path supplied by the caller. If non-empty, it is
                validated to exist. If empty, the package-data fallback is used
                via :func:`_resolve_package_resource`.
            default_filename: The filename to look up inside the package data
                when ``user_path`` is empty.
            param_name: The parameter name used in error messages.

        Returns:
            The resolved absolute path string.

        Raises:
            ConfigurationError: If ``user_path`` is non-empty but does not
                exist, or if the package-data resource cannot be resolved.
        """
        if user_path:
            if not Path(user_path).exists():
                raise ConfigurationError(f"{param_name} file not found: {user_path!r}")
            return user_path

        # Empty path — use package-data fallback.
        try:
            return _resolve_package_resource(default_filename)
        except FileNotFoundError as exc:
            raise ConfigurationError(
                f"{param_name} is empty and the package-data resource "
                f"{default_filename!r} could not be resolved: {exc}"
            ) from exc

    @staticmethod
    def _load_model(model_path: str) -> object:
        """Load a PyTorch model from ``model_path``.

        Args:
            model_path: Absolute path to the ``.pt`` model file.

        Returns:
            The loaded PyTorch model object.

        Raises:
            OperationError: If PyTorch raises any exception while loading.
        """
        try:
            model = torch.load(model_path, map_location="cpu")  # type: ignore[attr-defined]
            logger.info("Model loaded successfully from %r", model_path)
            return model
        except Exception as exc:
            raise OperationError(f"Failed to load model from {model_path!r}: {exc}") from exc

    def detect(
        self,
        frame: np.ndarray,
        target_labels: list[str],
    ) -> list[DetectionResult]:
        """Run inference on a single BGR frame and return filtered detections.

        Acquires the per-instance lock for the duration of the call, including
        on exception paths. Does not mutate ``frame`` or ``target_labels``.

        Args:
            frame: BGR image array with shape ``(H, W, 3)`` and dtype ``uint8``.
            target_labels: Current target label strings from ``RuntimeConfig``.

        Returns:
            A list of :class:`~model_lens.entities.DetectionResult` objects,
            filtered to those with ``confidence >= confidence_threshold``,
            ordered by descending confidence.

        Raises:
            ParseError: If a raw model output index has no entry in the label map.
            OperationError: If the inference call fails unexpectedly at runtime.
        """
        with self._lock:
            # Convert BGR → RGB without mutating the input array.
            rgb_frame = frame[:, :, ::-1].copy()

            try:
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
                    raise ParseError(
                        f"Raw model output index {index!r} has no entry in the label map"
                    )

                label = self._label_map[index]
                is_target = label in target_labels

                results.append(
                    DetectionResult(
                        label=label,
                        confidence=confidence,
                        bounding_box=box,
                        is_target=is_target,
                    )
                )

            results.sort(key=lambda r: r.confidence, reverse=True)
            return results


ENGINE_REGISTRY: dict[str, type[InferenceEngine]] = {
    "torch": TorchInferenceEngine,
}
