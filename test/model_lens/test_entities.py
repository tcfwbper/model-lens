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

"""Tests for src/model_lens/entities.py."""

import dataclasses

import numpy as np
import pytest

from model_lens.entities import (
    CameraConfig,
    DetectionResult,
    Frame,
    LocalCameraConfig,
    RtspCameraConfig,
    RuntimeConfig,
)
from model_lens.exceptions import ValidationError

# ---------------------------------------------------------------------------
# 1. LocalCameraConfig
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_local_camera_config_default_device_index() -> None:
    """Default device_index is 0."""
    instance = LocalCameraConfig()
    assert instance.device_index == 0


@pytest.mark.unit
def test_local_camera_config_explicit_device_index() -> None:
    """Explicit positive device_index is stored correctly."""
    instance = LocalCameraConfig(device_index=2)
    assert instance.device_index == 2


@pytest.mark.unit
def test_local_camera_config_zero_device_index() -> None:
    """device_index=0 is the boundary minimum and is valid."""
    instance = LocalCameraConfig(device_index=0)
    assert instance.device_index == 0


@pytest.mark.unit
def test_local_camera_config_negative_device_index() -> None:
    """Negative device_index raises ValidationError."""
    with pytest.raises(ValidationError):
        LocalCameraConfig(device_index=-1)


@pytest.mark.unit
def test_local_camera_config_is_frozen() -> None:
    """Assigning to any field after construction raises FrozenInstanceError or AttributeError."""
    instance = LocalCameraConfig()
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        instance.device_index = 1  # type: ignore[misc]


@pytest.mark.unit
def test_local_camera_config_is_camera_config() -> None:
    """LocalCameraConfig is a subclass of CameraConfig."""
    assert isinstance(LocalCameraConfig(), CameraConfig)


# ---------------------------------------------------------------------------
# 2. RtspCameraConfig
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_rtsp_camera_config_stores_url() -> None:
    """A valid RTSP URL is stored correctly."""
    instance = RtspCameraConfig(rtsp_url="rtsp://192.168.1.10/stream")
    assert instance.rtsp_url == "rtsp://192.168.1.10/stream"


@pytest.mark.unit
def test_rtsp_camera_config_empty_url() -> None:
    """Empty string rtsp_url raises ValidationError."""
    with pytest.raises(ValidationError):
        RtspCameraConfig(rtsp_url="")


@pytest.mark.unit
def test_rtsp_camera_config_is_frozen() -> None:
    """Assigning to any field after construction raises FrozenInstanceError or AttributeError."""
    instance = RtspCameraConfig(rtsp_url="rtsp://192.168.1.10/stream")
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        instance.rtsp_url = "rtsp://other"  # type: ignore[misc]


@pytest.mark.unit
def test_rtsp_camera_config_is_camera_config() -> None:
    """RtspCameraConfig is a subclass of CameraConfig."""
    assert isinstance(RtspCameraConfig(rtsp_url="rtsp://x"), CameraConfig)


# ---------------------------------------------------------------------------
# 3. CameraConfig
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_camera_config_cannot_be_instantiated() -> None:
    """Directly instantiating CameraConfig raises TypeError."""
    with pytest.raises(TypeError):
        CameraConfig()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# 4. RuntimeConfig
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_runtime_config_default_camera() -> None:
    """Default camera is LocalCameraConfig(device_index=0)."""
    instance = RuntimeConfig()
    assert isinstance(instance.camera, LocalCameraConfig)
    assert instance.camera.device_index == 0


@pytest.mark.unit
def test_runtime_config_default_target_labels() -> None:
    """Default target_labels is an empty list."""
    instance = RuntimeConfig()
    assert instance.target_labels == []


@pytest.mark.unit
def test_runtime_config_default_confidence_threshold() -> None:
    """Default confidence_threshold is 0.5."""
    instance = RuntimeConfig()
    assert instance.confidence_threshold == 0.5


@pytest.mark.unit
def test_runtime_config_explicit_local_camera() -> None:
    """Accepts a LocalCameraConfig with a non-default device_index."""
    instance = RuntimeConfig(camera=LocalCameraConfig(device_index=1))
    assert instance.camera.device_index == 1  # type: ignore[union-attr]


@pytest.mark.unit
def test_runtime_config_explicit_rtsp_camera() -> None:
    """Accepts an RtspCameraConfig."""
    instance = RuntimeConfig(camera=RtspCameraConfig(rtsp_url="rtsp://x"))
    assert instance.camera.rtsp_url == "rtsp://x"  # type: ignore[union-attr]


@pytest.mark.unit
def test_runtime_config_explicit_target_labels() -> None:
    """Stores a non-empty target labels list."""
    instance = RuntimeConfig(target_labels=["cat", "dog"])
    assert instance.target_labels == ["cat", "dog"]


@pytest.mark.unit
def test_runtime_config_explicit_confidence_threshold() -> None:
    """Stores a custom confidence threshold."""
    instance = RuntimeConfig(confidence_threshold=0.75)
    assert instance.confidence_threshold == 0.75


@pytest.mark.unit
def test_runtime_config_is_frozen() -> None:
    """Assigning to any field after construction raises FrozenInstanceError or AttributeError."""
    instance = RuntimeConfig()
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        instance.target_labels = ["x"]  # type: ignore[misc]


@pytest.mark.unit
def test_runtime_config_replacement_produces_new_instance() -> None:
    """Replacing a RuntimeConfig by constructing a new one does not mutate the original."""
    config_a = RuntimeConfig(target_labels=["cat"])
    config_b = RuntimeConfig(target_labels=["dog"])  # noqa: F841
    assert config_a.target_labels == ["cat"]


# ---------------------------------------------------------------------------
# 5. DetectionResult
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_detection_result_stores_label() -> None:
    """Label string is stored correctly."""
    instance = DetectionResult(label="cat", confidence=0.9, bounding_box=(0.1, 0.2, 0.4, 0.6), is_target=True)
    assert instance.label == "cat"


@pytest.mark.unit
def test_detection_result_stores_confidence() -> None:
    """Confidence float is stored correctly."""
    instance = DetectionResult(label="cat", confidence=0.9, bounding_box=(0.1, 0.2, 0.4, 0.6), is_target=True)
    assert instance.confidence == 0.9


@pytest.mark.unit
def test_detection_result_stores_bounding_box() -> None:
    """Bounding box tuple is stored correctly."""
    instance = DetectionResult(label="cat", confidence=0.9, bounding_box=(0.1, 0.2, 0.4, 0.6), is_target=True)
    assert instance.bounding_box == (0.1, 0.2, 0.4, 0.6)


@pytest.mark.unit
def test_detection_result_stores_is_target_true() -> None:
    """is_target=True is stored correctly."""
    instance = DetectionResult(label="cat", confidence=0.9, bounding_box=(0.1, 0.2, 0.4, 0.6), is_target=True)
    assert instance.is_target is True


@pytest.mark.unit
def test_detection_result_stores_is_target_false() -> None:
    """is_target=False is stored correctly."""
    instance = DetectionResult(label="cat", confidence=0.9, bounding_box=(0.1, 0.2, 0.4, 0.6), is_target=False)
    assert instance.is_target is False


@pytest.mark.unit
def test_detection_result_confidence_at_upper_boundary() -> None:
    """confidence=1.0 is valid and stored correctly."""
    instance = DetectionResult(label="cat", confidence=1.0, bounding_box=(0.1, 0.2, 0.4, 0.6), is_target=True)
    assert instance.confidence == 1.0


@pytest.mark.unit
def test_detection_result_confidence_just_above_zero() -> None:
    """confidence just above 0.0 is valid."""
    instance = DetectionResult(label="cat", confidence=1e-9, bounding_box=(0.1, 0.2, 0.4, 0.6), is_target=True)
    assert instance.confidence == pytest.approx(1e-9)


@pytest.mark.unit
def test_detection_result_confidence_zero() -> None:
    """confidence=0.0 violates the 0.0 < value constraint and raises ValidationError."""
    with pytest.raises(ValidationError):
        DetectionResult(label="cat", confidence=0.0, bounding_box=(0.1, 0.2, 0.4, 0.6), is_target=True)


@pytest.mark.unit
def test_detection_result_confidence_above_one() -> None:
    """confidence > 1.0 violates the value <= 1.0 constraint and raises ValidationError."""
    with pytest.raises(ValidationError):
        DetectionResult(label="cat", confidence=1.001, bounding_box=(0.1, 0.2, 0.4, 0.6), is_target=True)


@pytest.mark.unit
def test_detection_result_confidence_negative() -> None:
    """Negative confidence raises ValidationError."""
    with pytest.raises(ValidationError):
        DetectionResult(label="cat", confidence=-0.1, bounding_box=(0.1, 0.2, 0.4, 0.6), is_target=True)


@pytest.mark.unit
def test_detection_result_empty_label() -> None:
    """Empty label raises ValidationError."""
    with pytest.raises(ValidationError):
        DetectionResult(label="", confidence=0.9, bounding_box=(0.1, 0.2, 0.4, 0.6), is_target=True)


@pytest.mark.unit
def test_detection_result_is_frozen() -> None:
    """Assigning to any field after construction raises FrozenInstanceError or AttributeError."""
    instance = DetectionResult(label="cat", confidence=0.9, bounding_box=(0.1, 0.2, 0.4, 0.6), is_target=True)
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        instance.label = "dog"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 6. Frame
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_frame_stores_data() -> None:
    """data ndarray is stored with the correct shape and dtype."""
    arr = np.zeros((480, 640, 3), dtype=np.uint8)
    instance = Frame(data=arr.copy(), timestamp=1748000400.123456, source="local:0")
    assert instance.data.shape == (480, 640, 3)
    assert instance.data.dtype == np.uint8


@pytest.mark.unit
def test_frame_stores_timestamp() -> None:
    """timestamp float is stored correctly."""
    arr = np.zeros((480, 640, 3), dtype=np.uint8)
    instance = Frame(data=arr, timestamp=1748000400.123456, source="local:0")
    assert instance.timestamp == 1748000400.123456


@pytest.mark.unit
def test_frame_stores_source_local() -> None:
    """source string for a local camera is stored correctly."""
    arr = np.zeros((480, 640, 3), dtype=np.uint8)
    instance = Frame(data=arr, timestamp=1748000400.0, source="local:0")
    assert instance.source == "local:0"


@pytest.mark.unit
def test_frame_stores_source_rtsp() -> None:
    """source string for an RTSP camera is stored correctly."""
    arr = np.zeros((480, 640, 3), dtype=np.uint8)
    instance = Frame(data=arr, timestamp=1748000400.0, source="rtsp://192.168.1.10/stream")
    assert instance.source == "rtsp://192.168.1.10/stream"


@pytest.mark.unit
def test_frame_data_is_independent_of_original_array() -> None:
    """Mutating the original array after Frame construction does not affect Frame.data.

    CameraCapture is responsible for calling .copy() before constructing Frame.
    This test passes a pre-copied array to confirm that once a copy has been made
    the data is independent.
    """
    arr = np.zeros((480, 640, 3), dtype=np.uint8)
    instance = Frame(data=arr.copy(), timestamp=1748000400.0, source="local:0")
    arr[0, 0, 0] = 255
    assert instance.data[0, 0, 0] == 0


@pytest.mark.unit
def test_frame_init_stores_array_without_copying() -> None:
    """Frame.__init__ stores the passed-in array reference directly without calling .copy().

    This guards the architectural contract that copy responsibility belongs exclusively
    to CameraCapture, not to Frame.__init__.
    """
    arr = np.zeros((480, 640, 3), dtype=np.uint8)
    instance = Frame(data=arr, timestamp=1748000400.0, source="local:0")
    assert instance.data is arr


@pytest.mark.unit
def test_frame_data_mutation_does_not_raise() -> None:
    """Mutating Frame.data in place does not raise (mutation prevention is a convention only)."""
    arr = np.zeros((480, 640, 3), dtype=np.uint8)
    instance = Frame(data=arr, timestamp=1748000400.0, source="local:0")
    instance.data[0, 0, 0] = 255  # must not raise


@pytest.mark.unit
def test_frame_is_not_frozen() -> None:
    """Frame is a regular (non-frozen) dataclass; field reassignment does not raise."""
    arr = np.zeros((480, 640, 3), dtype=np.uint8)
    instance = Frame(data=arr, timestamp=1748000400.0, source="local:0")
    instance.source = "local:1"  # must not raise FrozenInstanceError
    assert instance.source == "local:1"
