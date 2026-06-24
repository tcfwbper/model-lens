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

"""Camera configuration entities — abstract base and concrete subclasses."""

from __future__ import annotations

import abc
from dataclasses import dataclass

from model_lens.exceptions import ValidationError


@dataclass(frozen=True)
class CameraConfig(abc.ABC):
    """Abstract base class identifying the active camera source.

    Cannot be instantiated directly — only concrete subclasses may be constructed.
    """

    @abc.abstractmethod
    def __post_init__(self) -> None:
        """Validate fields after construction. Subclasses must implement."""


@dataclass(frozen=True)
class LocalCameraConfig(CameraConfig):
    """Concrete camera configuration for a locally attached camera device.

    Args:
        device_index: Zero-based index of the local camera device.

    Raises:
        ValidationError: If device_index is negative.
    """

    device_index: int = 0

    def __post_init__(self) -> None:
        """Validate that device_index is non-negative.

        Raises:
            ValidationError: If device_index is negative.
        """
        if self.device_index < 0:
            raise ValidationError(
                f"device_index must be >= 0, got {self.device_index}"
            )


@dataclass(frozen=True)
class RtspCameraConfig(CameraConfig):
    """Concrete camera configuration for an RTSP network camera stream.

    Args:
        rtsp_url: URL of the RTSP stream.

    Raises:
        ValidationError: If rtsp_url is empty.
    """

    rtsp_url: str = ""

    def __post_init__(self) -> None:
        """Validate that rtsp_url is a non-empty string.

        Raises:
            ValidationError: If rtsp_url is empty.
        """
        if self.rtsp_url == "":
            raise ValidationError("rtsp_url must not be empty")
