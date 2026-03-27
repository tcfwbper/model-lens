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
"""Domain entities for ModelLens.

Defines the shared data structures passed between components of the Detection Pipeline,
Config API, and Stream API. All entities except :class:`Frame` are immutable after construction.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field

import numpy as np

from model_lens.exceptions import ValidationError


@dataclass(frozen=True)
class CameraConfig(abc.ABC):
    """Abstract base class identifying the active camera source.

    Cannot be instantiated directly. Use :class:`LocalCameraConfig` or
    :class:`RtspCameraConfig` instead.
    """

    @abc.abstractmethod
    def __post_init__(self) -> None:
        """Validate fields after construction.

        Raises:
            ValidationError: If any field value is invalid.
        """


@dataclass(frozen=True)
class LocalCameraConfig(CameraConfig):
    """Camera configuration for a locally attached camera device.

    Args:
        device_index: The zero-based index of the local camera device. Must be >= 0.

    Raises:
        ValidationError: If ``device_index`` is negative.
    """

    device_index: int = 0

    def __post_init__(self) -> None:
        """Validate that ``device_index`` is non-negative.

        Raises:
            ValidationError: If ``device_index`` is negative.
        """
        if self.device_index < 0:
            raise ValidationError(
                f"LocalCameraConfig.device_index must be >= 0, got {self.device_index!r}"
            )


@dataclass(frozen=True)
class RtspCameraConfig(CameraConfig):
    """Camera configuration for an RTSP network camera stream.

    Args:
        rtsp_url: The full RTSP URL of the camera stream. Must be non-empty.

    Raises:
        ValidationError: If ``rtsp_url`` is an empty string.
    """

    rtsp_url: str = ""

    def __post_init__(self) -> None:
        """Validate that ``rtsp_url`` is non-empty.

        Raises:
            ValidationError: If ``rtsp_url`` is an empty string.
        """
        if not self.rtsp_url:
            raise ValidationError("RtspCameraConfig.rtsp_url must be a non-empty string")


@dataclass(frozen=True)
class RuntimeConfig:
    """Full mutable runtime state of the server, replaced atomically on each update.

    Args:
        camera: The active camera configuration. Defaults to ``LocalCameraConfig(device_index=0)``.
        target_labels: The list of label strings considered detection targets. Defaults to ``[]``.
        confidence_threshold: The minimum confidence score for a detection to be reported.
            Defaults to ``0.5``.
    """

    camera: CameraConfig = field(default_factory=lambda: LocalCameraConfig(device_index=0))
    target_labels: list[str] = field(default_factory=list)
    confidence_threshold: float = 0.5


@dataclass(frozen=True)
class DetectionResult:
    """A single detected object produced by one inference pass.

    Args:
        label: The resolved human-readable class name. Must be non-empty.
        confidence: The model confidence score. Must satisfy ``0.0 < value <= 1.0``.
        bounding_box: Normalised ``(x1, y1, x2, y2)`` coordinates in ``[0.0, 1.0]``.
        is_target: ``True`` if ``label`` is in the current ``RuntimeConfig.target_labels``.

    Raises:
        ValidationError: If ``label`` is empty or ``confidence`` is out of range.
    """

    label: str
    confidence: float
    bounding_box: tuple[float, float, float, float]
    is_target: bool

    def __post_init__(self) -> None:
        """Validate ``label`` and ``confidence`` after construction.

        Raises:
            ValidationError: If ``label`` is empty or ``confidence`` is not in ``(0.0, 1.0]``.
        """
        if not self.label:
            raise ValidationError("DetectionResult.label must be a non-empty string")
        if not (0.0 < self.confidence <= 1.0):
            raise ValidationError(
                f"DetectionResult.confidence must satisfy 0.0 < value <= 1.0, got {self.confidence!r}"
            )


@dataclass
class Frame:
    """A single decoded image captured from a camera source.

    ``data`` is stored as-is (no internal copy). :class:`CameraCapture` is responsible
    for calling ``.copy()`` on the camera buffer before constructing a ``Frame``.
    ``data`` must be treated as read-only by all consumers.

    Args:
        data: The BGR image array with shape ``(H, W, 3)`` and dtype ``uint8``.
        timestamp: POSIX timestamp (seconds since 1970-01-01T00:00:00 UTC) at frame capture.
        source: Human-readable camera source identifier (e.g., ``"local:0"`` or an RTSP URL).
    """

    data: np.ndarray
    timestamp: float
    source: str
