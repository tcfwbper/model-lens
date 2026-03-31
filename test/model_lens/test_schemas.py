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

"""Tests for model_lens.schemas request models."""

import pydantic
import pytest

from model_lens.schemas import (
    LocalCameraRequest,
    RtspCameraRequest,
    UpdateCameraRequest,
    UpdateLabelsRequest,
)


# ---- 1. LocalCameraRequest ----


class TestLocalCameraRequest:
    """Tests for LocalCameraRequest."""

    def test_local_camera_request_default_device_index(self):
        instance = LocalCameraRequest(source_type="local")
        assert instance.device_index == 0

    def test_local_camera_request_explicit_device_index(self):
        instance = LocalCameraRequest(source_type="local", device_index=3)
        assert instance.device_index == 3

    def test_local_camera_request_negative_device_index_raises(self):
        with pytest.raises(pydantic.ValidationError):
            LocalCameraRequest(source_type="local", device_index=-1)


# ---- 2. RtspCameraRequest ----


class TestRtspCameraRequest:
    """Tests for RtspCameraRequest."""

    def test_rtsp_camera_request_stores_url(self):
        instance = RtspCameraRequest(source_type="rtsp", rtsp_url="rtsp://x")
        assert instance.rtsp_url == "rtsp://x"

    def test_rtsp_camera_request_wrong_scheme_raises(self):
        with pytest.raises(pydantic.ValidationError):
            RtspCameraRequest(source_type="rtsp", rtsp_url="http://x")

    def test_rtsp_camera_request_empty_url_raises(self):
        with pytest.raises(pydantic.ValidationError):
            RtspCameraRequest(source_type="rtsp", rtsp_url="")


# ---- 3. UpdateCameraRequest ----


class TestUpdateCameraRequest:
    """Tests for UpdateCameraRequest discriminated union."""

    def test_update_camera_request_local_discriminated(self):
        instance = UpdateCameraRequest(
            camera={"source_type": "local", "device_index": 0}
        )
        assert isinstance(instance.camera, LocalCameraRequest)

    def test_update_camera_request_rtsp_discriminated(self):
        instance = UpdateCameraRequest(
            camera={"source_type": "rtsp", "rtsp_url": "rtsp://x"}
        )
        assert isinstance(instance.camera, RtspCameraRequest)

    def test_update_camera_request_unknown_source_type_raises(self):
        with pytest.raises(pydantic.ValidationError):
            UpdateCameraRequest(camera={"source_type": "usb"})


# ---- 4. UpdateLabelsRequest ----


class TestUpdateLabelsRequest:
    """Tests for UpdateLabelsRequest."""

    def test_update_labels_request_stores_labels(self):
        instance = UpdateLabelsRequest(target_labels=["cat", "dog"])
        assert instance.target_labels == ["cat", "dog"]

    def test_update_labels_request_empty_list_valid(self):
        instance = UpdateLabelsRequest(target_labels=[])
        assert instance.target_labels == []

    def test_update_labels_request_missing_field_raises(self):
        with pytest.raises(pydantic.ValidationError):
            UpdateLabelsRequest()

    def test_update_labels_request_non_array_raises(self):
        with pytest.raises(pydantic.ValidationError):
            UpdateLabelsRequest(target_labels="cat")

    def test_update_labels_request_non_string_elements_raises(self):
        with pytest.raises(pydantic.ValidationError):
            UpdateLabelsRequest(target_labels=[1, 2])
