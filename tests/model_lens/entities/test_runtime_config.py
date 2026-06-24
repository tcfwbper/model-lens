"""Tests for model_lens.entities.runtime_config — RuntimeConfig entity.

Target source: src/model_lens/entities/runtime_config.py
Once the entities module is refactored into a subpackage, update the imports below to:
    from model_lens.entities.camera_config import LocalCameraConfig, RtspCameraConfig
    from model_lens.entities.runtime_config import RuntimeConfig
"""

from __future__ import annotations

import dataclasses

import pytest

from model_lens.entities import LocalCameraConfig, RtspCameraConfig, RuntimeConfig


# ---------------------------------------------------------------------------
# Happy Path — Default Construction
# ---------------------------------------------------------------------------


class TestRuntimeConfigDefaults:
    """Verify default construction produces expected defaults."""

    def test_runtime_config_defaults(self) -> None:
        """Default construction produces expected defaults."""
        config = RuntimeConfig()
        assert config.camera == LocalCameraConfig(device_index=0)
        assert config.target_labels == []
        assert config.confidence_threshold == 0.5


# ---------------------------------------------------------------------------
# Happy Path — Explicit Construction
# ---------------------------------------------------------------------------


class TestRuntimeConfigExplicit:
    """Verify explicit construction stores all provided values."""

    def test_runtime_config_explicit_fields(self) -> None:
        """Explicit construction stores all provided values."""
        camera = RtspCameraConfig(rtsp_url="rtsp://x")
        config = RuntimeConfig(
            camera=camera,
            target_labels=["person", "car"],
            confidence_threshold=0.8,
        )
        assert config.camera == camera
        assert config.target_labels == ["person", "car"]
        assert config.confidence_threshold == 0.8


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------


class TestRuntimeConfigImmutability:
    """Verify frozen dataclass behaviour."""

    def test_runtime_config_frozen(self) -> None:
        """Assigning to any field on an existing instance raises."""
        config = RuntimeConfig()
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            config.confidence_threshold = 0.9  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Atomic Replacement
# ---------------------------------------------------------------------------


class TestRuntimeConfigAtomicReplacement:
    """Verify that creating new instances does not mutate existing ones."""

    def test_runtime_config_new_instance_does_not_mutate_original(self) -> None:
        """Creating a new RuntimeConfig does not alter an existing instance."""
        original = RuntimeConfig()
        _new = RuntimeConfig(target_labels=["dog"])
        assert original.target_labels == []


# ---------------------------------------------------------------------------
# Null / Empty Input
# ---------------------------------------------------------------------------


class TestRuntimeConfigEmptyInput:
    """Verify empty target_labels is valid."""

    def test_runtime_config_empty_target_labels(self) -> None:
        """Empty target_labels list is valid."""
        config = RuntimeConfig(target_labels=[])
        assert config.target_labels == []
