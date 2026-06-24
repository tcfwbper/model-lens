"""Shared test fixtures for model_lens.routers tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from model_lens.entities.camera_config import LocalCameraConfig, RtspCameraConfig
from model_lens.entities.runtime_config import RuntimeConfig


@pytest.fixture()
def mock_pipeline() -> MagicMock:
    """Create a mock DetectionPipeline with sensible defaults."""
    pipeline = MagicMock()
    pipeline.get_config.return_value = RuntimeConfig(
        camera=LocalCameraConfig(device_index=0),
        target_labels=["person"],
        confidence_threshold=0.5,
    )
    return pipeline


@pytest.fixture()
def mock_engine() -> MagicMock:
    """Create a mock InferenceEngine with a default label map."""
    engine = MagicMock()
    engine.get_label_map.return_value = {0: "person", 1: "bicycle", 2: "car"}
    return engine


@pytest.fixture()
def make_runtime_config() -> Any:
    """Factory fixture for building RuntimeConfig instances."""

    def _factory(
        *,
        camera: LocalCameraConfig | RtspCameraConfig | None = None,
        target_labels: list[str] | None = None,
        confidence_threshold: float = 0.5,
    ) -> RuntimeConfig:
        if camera is None:
            camera = LocalCameraConfig(device_index=0)
        if target_labels is None:
            target_labels = []
        return RuntimeConfig(
            camera=camera,
            target_labels=target_labels,
            confidence_threshold=confidence_threshold,
        )

    return _factory
