"""Tests for model_lens.entities.frame — Frame entity.

Target source: src/model_lens/entities/frame.py
Once the entities module is refactored into a subpackage, update the import below to:
    from model_lens.entities.frame import Frame
"""

from __future__ import annotations

import numpy as np

from model_lens.entities import Frame


# ---------------------------------------------------------------------------
# Happy Path — Construction
# ---------------------------------------------------------------------------


class TestFrameConstruction:
    """Verify construction stores fields as provided."""

    def test_frame_stores_fields(self) -> None:
        """Construction stores data, timestamp, and source as provided."""
        array = np.zeros((480, 640, 3), dtype=np.uint8)
        frame = Frame(data=array, timestamp=1700000000.123, source="local:0")

        assert frame.timestamp == 1700000000.123
        assert frame.source == "local:0"
        assert frame.data.shape == (480, 640, 3)
        assert frame.data.dtype == np.uint8


# ---------------------------------------------------------------------------
# Not Immutable
# ---------------------------------------------------------------------------


class TestFrameMutability:
    """Verify Frame is not frozen — field reassignment is allowed."""

    def test_frame_allows_field_reassignment(self) -> None:
        """Frame is not frozen; field reassignment does not raise."""
        array = np.zeros((480, 640, 3), dtype=np.uint8)
        frame = Frame(data=array, timestamp=1700000000.0, source="local:0")

        frame.source = "rtsp://new"
        assert frame.source == "rtsp://new"


# ---------------------------------------------------------------------------
# Read-Only Convention
# ---------------------------------------------------------------------------


class TestFrameDataReference:
    """Verify Frame holds a reference to the data array, not a copy."""

    def test_frame_data_not_copied(self) -> None:
        """Frame does not internally copy the data array; it holds a reference."""
        original_array = np.zeros((480, 640, 3), dtype=np.uint8)
        frame = Frame(data=original_array, timestamp=1700000000.0, source="local:0")

        assert frame.data is original_array
