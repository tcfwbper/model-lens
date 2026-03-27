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

"""Shared pytest fixtures for entity tests."""

import numpy as np
import pytest

from model_lens.entities import (
    DetectionResult,
    Frame,
    LocalCameraConfig,
    RuntimeConfig,
)


@pytest.fixture()
def valid_frame_array() -> np.ndarray:
    """Return a valid HxWxC uint8 NumPy array suitable for Frame construction.

    Returns:
        A (480, 640, 3) uint8 zeros array.
    """
    return np.zeros((480, 640, 3), dtype=np.uint8)


@pytest.fixture()
def valid_frame(valid_frame_array: np.ndarray) -> Frame:
    """Return a fully constructed Frame using a copy of the shared array.

    Returns:
        A Frame with shape (480, 640, 3), a fixed timestamp, and source "local:0".
    """
    return Frame(
        data=valid_frame_array.copy(),
        timestamp=1748000400.123456,
        source="local:0",
    )


@pytest.fixture()
def valid_detection_result() -> DetectionResult:
    """Return a fully constructed DetectionResult with valid field values.

    Returns:
        A DetectionResult for label "cat" with confidence 0.9.
    """
    return DetectionResult(
        label="cat",
        confidence=0.9,
        bounding_box=(0.1, 0.2, 0.4, 0.6),
        is_target=True,
    )


@pytest.fixture()
def default_runtime_config() -> RuntimeConfig:
    """Return a RuntimeConfig constructed with all defaults.

    Returns:
        A RuntimeConfig with default camera, target_labels, and confidence_threshold.
    """
    return RuntimeConfig()


@pytest.fixture()
def local_camera_config() -> LocalCameraConfig:
    """Return a LocalCameraConfig with the default device index.

    Returns:
        A LocalCameraConfig with device_index=0.
    """
    return LocalCameraConfig()
