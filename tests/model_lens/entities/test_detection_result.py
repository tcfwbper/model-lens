"""Tests for model_lens.entities.detection_result — DetectionResult entity.

Target source: src/model_lens/entities/detection_result.py
Once the entities module is refactored into a subpackage, update the import below to:
    from model_lens.entities.detection_result import DetectionResult
"""

from __future__ import annotations

import dataclasses

import pytest

from model_lens.entities import DetectionResult
from model_lens.exceptions import ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_detection_result(
    label: str = "person",
    confidence: float = 0.95,
    bounding_box: tuple[float, float, float, float] = (0.1, 0.2, 0.5, 0.8),
    is_target: bool = True,
) -> DetectionResult:
    """Fixture builder for DetectionResult with sensible defaults."""
    return DetectionResult(
        label=label,
        confidence=confidence,
        bounding_box=bounding_box,
        is_target=is_target,
    )


# ---------------------------------------------------------------------------
# Happy Path — Construction
# ---------------------------------------------------------------------------


class TestDetectionResultHappyPath:
    """Verify valid construction stores all fields."""

    def test_detection_result_valid(self) -> None:
        """Construction with valid fields stores all values."""
        result = DetectionResult(
            label="person",
            confidence=0.95,
            bounding_box=(0.1, 0.2, 0.5, 0.8),
            is_target=True,
        )
        assert result.label == "person"
        assert result.confidence == 0.95
        assert result.bounding_box == (0.1, 0.2, 0.5, 0.8)
        assert result.is_target is True

    def test_detection_result_confidence_one(self) -> None:
        """confidence=1.0 is the inclusive upper bound and valid."""
        result = DetectionResult(
            label="car",
            confidence=1.0,
            bounding_box=(0.0, 0.0, 1.0, 1.0),
            is_target=False,
        )
        assert result.confidence == 1.0

    def test_detection_result_is_target_false(self) -> None:
        """is_target=False is stored correctly."""
        result = DetectionResult(
            label="cat",
            confidence=0.5,
            bounding_box=(0.0, 0.0, 0.5, 0.5),
            is_target=False,
        )
        assert result.is_target is False


# ---------------------------------------------------------------------------
# Boundary Values — confidence
# ---------------------------------------------------------------------------


class TestDetectionResultConfidenceBoundary:
    """Verify confidence boundary conditions."""

    def test_detection_result_confidence_just_above_zero(self) -> None:
        """confidence just above zero is valid."""
        result = DetectionResult(
            label="dog",
            confidence=0.001,
            bounding_box=(0.0, 0.0, 0.5, 0.5),
            is_target=False,
        )
        assert result.confidence == 0.001

    def test_detection_result_confidence_zero(self) -> None:
        """confidence=0.0 is invalid (exclusive lower bound)."""
        with pytest.raises(ValidationError):
            DetectionResult(
                label="dog",
                confidence=0.0,
                bounding_box=(0.0, 0.0, 0.5, 0.5),
                is_target=False,
            )

    def test_detection_result_confidence_above_one(self) -> None:
        """confidence > 1.0 is invalid."""
        with pytest.raises(ValidationError):
            DetectionResult(
                label="dog",
                confidence=1.1,
                bounding_box=(0.0, 0.0, 0.5, 0.5),
                is_target=False,
            )

    def test_detection_result_confidence_negative(self) -> None:
        """Negative confidence is invalid."""
        with pytest.raises(ValidationError):
            DetectionResult(
                label="dog",
                confidence=-0.5,
                bounding_box=(0.0, 0.0, 0.5, 0.5),
                is_target=False,
            )


# ---------------------------------------------------------------------------
# Validation Failures — label
# ---------------------------------------------------------------------------


class TestDetectionResultLabelValidation:
    """Verify empty label rejection."""

    def test_detection_result_empty_label(self) -> None:
        """Empty label string raises ValidationError."""
        with pytest.raises(ValidationError):
            DetectionResult(
                label="",
                confidence=0.9,
                bounding_box=(0.0, 0.0, 0.5, 0.5),
                is_target=False,
            )


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------


class TestDetectionResultImmutability:
    """Verify frozen dataclass behaviour."""

    def test_detection_result_frozen(self) -> None:
        """Assigning to any field on an existing instance raises."""
        result = _make_detection_result()
        with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
            result.label = "new"  # type: ignore[misc]
