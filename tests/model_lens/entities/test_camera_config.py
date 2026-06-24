"""Tests for model_lens.entities.camera_config — CameraConfig hierarchy.

Target source: src/model_lens/entities/camera_config.py
Once the entities module is refactored into a subpackage, update the import below to:
    from model_lens.entities.camera_config import CameraConfig, LocalCameraConfig, RtspCameraConfig
"""

from __future__ import annotations

import abc
import dataclasses

import pytest

from model_lens.entities import (
    CameraConfig,
    LocalCameraConfig,
    RtspCameraConfig,
)
from model_lens.exceptions import ValidationError


# ---------------------------------------------------------------------------
# CameraConfig — Type Hierarchy
# ---------------------------------------------------------------------------


class TestCameraConfigTypeHierarchy:
    """Verify abstract base and subclass relationships."""

    def test_camera_config_is_abstract(self) -> None:
        """Direct instantiation of CameraConfig raises TypeError."""
        with pytest.raises(TypeError):
            CameraConfig()  # type: ignore[abstract]

    def test_camera_config_inherits_abc(self) -> None:
        """CameraConfig is a subclass of abc.ABC."""
        assert issubclass(CameraConfig, abc.ABC)

    def test_local_camera_config_is_subclass(self) -> None:
        """LocalCameraConfig is a subclass of CameraConfig."""
        assert issubclass(LocalCameraConfig, CameraConfig)

    def test_rtsp_camera_config_is_subclass(self) -> None:
        """RtspCameraConfig is a subclass of CameraConfig."""
        assert issubclass(RtspCameraConfig, CameraConfig)


# ---------------------------------------------------------------------------
# LocalCameraConfig — Happy Path
# ---------------------------------------------------------------------------


class TestLocalCameraConfigHappyPath:
    """Verify default and explicit construction."""

    def test_local_camera_config_default(self) -> None:
        """Default construction uses device_index=0."""
        config = LocalCameraConfig()
        assert config.device_index == 0

    def test_local_camera_config_explicit_index(self) -> None:
        """Construction with explicit device_index stores the value."""
        config = LocalCameraConfig(device_index=2)
        assert config.device_index == 2


# ---------------------------------------------------------------------------
# LocalCameraConfig — Boundary Values
# ---------------------------------------------------------------------------


class TestLocalCameraConfigBoundaryValues:
    """Verify device_index boundary conditions."""

    def test_local_camera_config_zero_index(self) -> None:
        """device_index=0 is the minimum valid value."""
        config = LocalCameraConfig(device_index=0)
        assert config.device_index == 0

    def test_local_camera_config_negative_index(self) -> None:
        """device_index=-1 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            LocalCameraConfig(device_index=-1)
        assert "-1" in str(exc_info.value)


# ---------------------------------------------------------------------------
# LocalCameraConfig — Validation Failures
# ---------------------------------------------------------------------------


class TestLocalCameraConfigValidationFailures:
    """Verify validation rejects invalid device_index values."""

    def test_local_camera_config_negative_large(self) -> None:
        """A large negative device_index raises ValidationError."""
        with pytest.raises(ValidationError):
            LocalCameraConfig(device_index=-100)


# ---------------------------------------------------------------------------
# LocalCameraConfig — Immutability
# ---------------------------------------------------------------------------


class TestLocalCameraConfigImmutability:
    """Verify frozen dataclass behaviour."""

    def test_local_camera_config_frozen(self) -> None:
        """Assigning to device_index on an existing instance raises."""
        config = LocalCameraConfig(device_index=0)
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            config.device_index = 5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# RtspCameraConfig — Happy Path
# ---------------------------------------------------------------------------


class TestRtspCameraConfigHappyPath:
    """Verify valid URL construction."""

    def test_rtsp_camera_config_valid_url(self) -> None:
        """Construction with a non-empty URL succeeds."""
        config = RtspCameraConfig(rtsp_url="rtsp://192.168.1.1:554/stream")
        assert config.rtsp_url == "rtsp://192.168.1.1:554/stream"

    def test_rtsp_camera_config_whitespace_only_url(self) -> None:
        """A whitespace-only URL is accepted (only empty-string check is performed)."""
        config = RtspCameraConfig(rtsp_url="   ")
        assert config.rtsp_url == "   "


# ---------------------------------------------------------------------------
# RtspCameraConfig — Validation Failures
# ---------------------------------------------------------------------------


class TestRtspCameraConfigValidationFailures:
    """Verify empty URL rejection."""

    def test_rtsp_camera_config_empty_url(self) -> None:
        """Empty string raises ValidationError."""
        with pytest.raises(ValidationError):
            RtspCameraConfig(rtsp_url="")

    def test_rtsp_camera_config_default_url(self) -> None:
        """Default construction (empty string default) raises ValidationError."""
        with pytest.raises(ValidationError):
            RtspCameraConfig()


# ---------------------------------------------------------------------------
# RtspCameraConfig — Immutability
# ---------------------------------------------------------------------------


class TestRtspCameraConfigImmutability:
    """Verify frozen dataclass behaviour."""

    def test_rtsp_camera_config_frozen(self) -> None:
        """Assigning to rtsp_url on an existing instance raises."""
        config = RtspCameraConfig(rtsp_url="rtsp://192.168.1.1:554/stream")
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            config.rtsp_url = "new"  # type: ignore[misc]
