"""Shared test fixtures for model_lens tests."""

from __future__ import annotations

import pytest


@pytest.fixture()
def valid_rtsp_url() -> str:
    """Provide a standard valid RTSP URL for tests."""
    return "rtsp://192.168.1.1:554/stream"
