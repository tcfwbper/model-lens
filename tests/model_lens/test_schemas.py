"""Tests for model_lens.schemas — Pydantic request model validation."""

from __future__ import annotations

import pytest

# Skip entire module if production schemas module is not yet implemented.
pytest.importorskip(
    "model_lens.schemas",
    reason="Production module model_lens.schemas not yet implemented",
)

from model_lens.schemas import (  # noqa: E402
    LocalCameraRequest,
    RtspCameraRequest,
    UpdateCameraRequest,
    UpdateLabelsRequest,
)
from pydantic import ValidationError  # noqa: E402


# ---------------------------------------------------------------------------
# LocalCameraRequest
# ---------------------------------------------------------------------------


class TestLocalCameraRequestConstruction:
    """Happy Path — Construction."""

    def test_local_camera_request_defaults(self) -> None:
        """Constructs with default device_index of 0."""
        obj = LocalCameraRequest.model_validate({"source_type": "local"})
        assert obj.source_type == "local"
        assert obj.device_index == 0

    def test_local_camera_request_explicit_device_index(self) -> None:
        """Constructs with an explicit device index."""
        obj = LocalCameraRequest.model_validate({"source_type": "local", "device_index": 2})
        assert obj.device_index == 2


class TestLocalCameraRequestBoundary:
    """Boundary Values — device_index."""

    def test_local_camera_request_device_index_zero(self) -> None:
        """Accepts the minimum valid device index."""
        obj = LocalCameraRequest.model_validate({"source_type": "local", "device_index": 0})
        assert obj.device_index == 0


class TestLocalCameraRequestValidationFailures:
    """Validation Failures — device_index."""

    def test_local_camera_request_negative_device_index(self) -> None:
        """Rejects a negative device index."""
        with pytest.raises(ValidationError):
            LocalCameraRequest.model_validate({"source_type": "local", "device_index": -1})


# ---------------------------------------------------------------------------
# RtspCameraRequest
# ---------------------------------------------------------------------------


class TestRtspCameraRequestConstruction:
    """Happy Path — Construction."""

    def test_rtsp_camera_request_valid_url(self) -> None:
        """Constructs with a valid RTSP URL."""
        obj = RtspCameraRequest.model_validate({"source_type": "rtsp", "rtsp_url": "rtsp://192.168.1.1/stream"})
        assert obj.source_type == "rtsp"
        assert obj.rtsp_url == "rtsp://192.168.1.1/stream"


class TestRtspCameraRequestValidationFailures:
    """Validation Failures — rtsp_url."""

    def test_rtsp_camera_request_invalid_url_scheme(self) -> None:
        """Rejects a URL that does not start with rtsp://."""
        with pytest.raises(ValidationError):
            RtspCameraRequest.model_validate({"source_type": "rtsp", "rtsp_url": "http://example.com/stream"})

    def test_rtsp_camera_request_empty_url(self) -> None:
        """Rejects an empty string URL."""
        with pytest.raises(ValidationError):
            RtspCameraRequest.model_validate({"source_type": "rtsp", "rtsp_url": ""})


# ---------------------------------------------------------------------------
# UpdateCameraRequest
# ---------------------------------------------------------------------------


class TestUpdateCameraRequestConstruction:
    """Happy Path — Construction."""

    def test_update_camera_request_local(self) -> None:
        """Discriminates to LocalCameraRequest when source_type is 'local'."""
        body = UpdateCameraRequest.model_validate({"camera": {"source_type": "local", "device_index": 1}})
        assert isinstance(body.camera, LocalCameraRequest)
        assert body.camera.device_index == 1

    def test_update_camera_request_rtsp(self) -> None:
        """Discriminates to RtspCameraRequest when source_type is 'rtsp'."""
        body = UpdateCameraRequest.model_validate({"camera": {"source_type": "rtsp", "rtsp_url": "rtsp://host/path"}})
        assert isinstance(body.camera, RtspCameraRequest)
        assert body.camera.rtsp_url == "rtsp://host/path"


class TestUpdateCameraRequestValidationFailures:
    """Validation Failures."""

    def test_update_camera_request_invalid_source_type(self) -> None:
        """Rejects an unknown discriminator value."""
        with pytest.raises(ValidationError):
            UpdateCameraRequest.model_validate({"camera": {"source_type": "usb", "device_index": 0}})

    def test_update_camera_request_missing_camera(self) -> None:
        """Rejects a body with no camera field."""
        with pytest.raises(ValidationError):
            UpdateCameraRequest.model_validate({})


# ---------------------------------------------------------------------------
# UpdateLabelsRequest
# ---------------------------------------------------------------------------


class TestUpdateLabelsRequestConstruction:
    """Happy Path — Construction."""

    def test_update_labels_request_with_labels(self) -> None:
        """Constructs with a non-empty label list."""
        obj = UpdateLabelsRequest.model_validate({"target_labels": ["cat", "dog"]})
        assert obj.target_labels == ["cat", "dog"]

    def test_update_labels_request_empty_list(self) -> None:
        """Accepts an empty list as valid input."""
        obj = UpdateLabelsRequest.model_validate({"target_labels": []})
        assert obj.target_labels == []


class TestUpdateLabelsRequestValidationFailures:
    """Validation Failures."""

    def test_update_labels_request_missing_field(self) -> None:
        """Rejects a body with no target_labels field."""
        with pytest.raises(ValidationError):
            UpdateLabelsRequest.model_validate({})
