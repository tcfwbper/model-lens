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
"""Tests for src/model_lens/inference_engine.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from model_lens.exceptions import ConfigurationError, OperationError
from model_lens.inference_engine import YOLOInferenceEngine
from fixtures.inference_engine import _det, _yolo_results


# ---------------------------------------------------------------------------
# Helper: construct engine with YOLO patched
# ---------------------------------------------------------------------------


def _make_engine(confidence_threshold: float = 0.5) -> YOLOInferenceEngine:
    """Construct a YOLOInferenceEngine with YOLO patched to a minimal mock."""
    mock_yolo = MagicMock()
    mock_yolo.names = {0: "person", 1: "bicycle", 2: "car"}
    with patch("model_lens.inference_engine.YOLO", return_value=mock_yolo):
        return YOLOInferenceEngine(model="yolov8n.pt", confidence_threshold=confidence_threshold)


# ===========================================================================
# Section 1 — Constructor: confidence_threshold Validation
# ===========================================================================


class TestConfidenceThresholdValidation:
    """1.1 Validation Failures — confidence_threshold."""

    @pytest.mark.unit
    def test_confidence_threshold_zero_raises(self) -> None:
        """confidence_threshold=0.0 violates 0.0 < value constraint."""
        mock_yolo = MagicMock()
        mock_yolo.names = {0: "person"}
        with patch("model_lens.inference_engine.YOLO", return_value=mock_yolo):
            with pytest.raises(ConfigurationError):
                YOLOInferenceEngine(model="yolov8n.pt", confidence_threshold=0.0)

    @pytest.mark.unit
    def test_confidence_threshold_negative_raises(self) -> None:
        """Negative confidence_threshold raises ConfigurationError."""
        mock_yolo = MagicMock()
        mock_yolo.names = {0: "person"}
        with patch("model_lens.inference_engine.YOLO", return_value=mock_yolo):
            with pytest.raises(ConfigurationError):
                YOLOInferenceEngine(model="yolov8n.pt", confidence_threshold=-0.1)

    @pytest.mark.unit
    def test_confidence_threshold_above_one_raises(self) -> None:
        """confidence_threshold > 1.0 raises ConfigurationError."""
        mock_yolo = MagicMock()
        mock_yolo.names = {0: "person"}
        with patch("model_lens.inference_engine.YOLO", return_value=mock_yolo):
            with pytest.raises(ConfigurationError):
                YOLOInferenceEngine(model="yolov8n.pt", confidence_threshold=1.001)

    @pytest.mark.unit
    def test_confidence_threshold_at_upper_boundary(self) -> None:
        """confidence_threshold=1.0 is valid."""
        engine = _make_engine(confidence_threshold=1.0)
        assert engine is not None

    @pytest.mark.unit
    def test_confidence_threshold_just_above_zero(self) -> None:
        """confidence_threshold just above 0.0 is valid."""
        engine = _make_engine(confidence_threshold=1e-9)
        assert engine is not None


# ===========================================================================
# Section 2 — Constructor: Model Loading
# ===========================================================================


class TestModelLoading:
    """2.1 & 2.2 — model loading happy path and failure."""

    @pytest.mark.unit
    def test_model_loads_successfully(self) -> None:
        """A valid model string constructs without error."""
        engine = _make_engine()
        assert engine is not None

    @pytest.mark.unit
    def test_model_load_failure(self) -> None:
        """YOLO() raising an exception wraps as OperationError."""
        with patch("model_lens.inference_engine.YOLO", side_effect=Exception("corrupt")):
            with pytest.raises(OperationError):
                YOLOInferenceEngine(model="bad.pt", confidence_threshold=0.5)


# ===========================================================================
# Section 3 — detect() Happy Path
# ===========================================================================


class TestDetectHappyPath:
    """3.1 Happy Path — detect()."""

    @pytest.mark.unit
    def test_detect_returns_list(self, engine_with_mock_model: YOLOInferenceEngine) -> None:
        """detect() always returns a list."""
        engine_with_mock_model._model.return_value = _yolo_results([])  # type: ignore[attr-defined]
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = engine_with_mock_model.detect(frame, target_labels=[])
        assert isinstance(result, list)

    @pytest.mark.unit
    def test_detect_empty_when_no_detections(self, engine_with_mock_model: YOLOInferenceEngine) -> None:
        """No detections above threshold returns empty list."""
        engine_with_mock_model._model.return_value = _yolo_results([])  # type: ignore[attr-defined]
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = engine_with_mock_model.detect(frame, target_labels=[])
        assert result == []

    @pytest.mark.unit
    def test_detect_single_result_fields(self, engine_with_mock_model: YOLOInferenceEngine) -> None:
        """A single detection above threshold produces one DetectionResult with correct fields."""
        engine_with_mock_model._model.return_value = _yolo_results(  # type: ignore[attr-defined]
            [_det(index=0, confidence=0.9, box=[0.1, 0.2, 0.4, 0.6])]
        )
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = engine_with_mock_model.detect(frame, target_labels=[])
        assert len(result) == 1
        assert result[0].label == "person"
        assert result[0].confidence == pytest.approx(0.9)
        assert result[0].bounding_box == [0.1, 0.2, 0.4, 0.6]

    @pytest.mark.unit
    def test_detect_is_target_true(self, engine_with_mock_model: YOLOInferenceEngine) -> None:
        """is_target is True when label is in target_labels."""
        engine_with_mock_model._model.return_value = _yolo_results(  # type: ignore[attr-defined]
            [_det(index=0, confidence=0.9)]
        )
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = engine_with_mock_model.detect(frame, target_labels=["person"])
        assert result[0].is_target is True

    @pytest.mark.unit
    def test_detect_is_target_false(self, engine_with_mock_model: YOLOInferenceEngine) -> None:
        """is_target is False when label is not in target_labels."""
        engine_with_mock_model._model.return_value = _yolo_results(  # type: ignore[attr-defined]
            [_det(index=0, confidence=0.9)]
        )
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = engine_with_mock_model.detect(frame, target_labels=[])
        assert result[0].is_target is False

    @pytest.mark.unit
    def test_detect_does_not_mutate_frame(self, engine_with_mock_model: YOLOInferenceEngine) -> None:
        """detect() does not modify the input frame array."""
        engine_with_mock_model._model.return_value = _yolo_results([])  # type: ignore[attr-defined]
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame_before = frame.copy()
        engine_with_mock_model.detect(frame, target_labels=[])
        assert np.array_equal(frame, frame_before)

    @pytest.mark.unit
    def test_detect_does_not_mutate_target_labels(self, engine_with_mock_model: YOLOInferenceEngine) -> None:
        """detect() does not modify the target_labels list."""
        engine_with_mock_model._model.return_value = _yolo_results([])  # type: ignore[attr-defined]
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        target_labels = ["person", "bicycle"]
        target_labels_before = target_labels.copy()
        engine_with_mock_model.detect(frame, target_labels=target_labels)
        assert target_labels == target_labels_before


# ===========================================================================
# Section 3.2 — detect() Boundary Values: confidence_threshold
# ===========================================================================


class TestDetectThresholdFiltering:
    """3.2 Boundary Values — confidence_threshold filtering."""

    @pytest.mark.unit
    def test_detect_filters_below_threshold(self, engine_with_mock_model: YOLOInferenceEngine) -> None:
        """Detection with confidence strictly below threshold is excluded."""
        engine_with_mock_model._model.return_value = _yolo_results(  # type: ignore[attr-defined]
            [_det(index=0, confidence=0.49)]
        )
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = engine_with_mock_model.detect(frame, target_labels=[])
        assert result == []

    @pytest.mark.unit
    def test_detect_keeps_at_threshold(self, engine_with_mock_model: YOLOInferenceEngine) -> None:
        """Detection with confidence exactly equal to threshold is kept."""
        engine_with_mock_model._model.return_value = _yolo_results(  # type: ignore[attr-defined]
            [_det(index=0, confidence=0.5)]
        )
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = engine_with_mock_model.detect(frame, target_labels=[])
        assert len(result) == 1

    @pytest.mark.unit
    def test_detect_keeps_above_threshold(self, engine_with_mock_model: YOLOInferenceEngine) -> None:
        """Detection with confidence above threshold is kept."""
        engine_with_mock_model._model.return_value = _yolo_results(  # type: ignore[attr-defined]
            [_det(index=0, confidence=0.51)]
        )
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = engine_with_mock_model.detect(frame, target_labels=[])
        assert len(result) == 1


# ===========================================================================
# Section 3.3 — detect() Ordering: Descending Confidence
# ===========================================================================


class TestDetectOrdering:
    """3.3 Ordering — Descending Confidence."""

    @pytest.mark.unit
    def test_detect_results_ordered_by_descending_confidence(
        self,
        engine_with_mock_model: YOLOInferenceEngine,
    ) -> None:
        """Multiple detections are returned in descending confidence order."""
        engine_with_mock_model._model.return_value = _yolo_results(  # type: ignore[attr-defined]
            [
                _det(index=0, confidence=0.6),
                _det(index=1, confidence=0.9),
                _det(index=2, confidence=0.75),
            ]
        )
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = engine_with_mock_model.detect(frame, target_labels=[])
        assert result[0].confidence == pytest.approx(0.9)
        assert result[1].confidence == pytest.approx(0.75)
        assert result[2].confidence == pytest.approx(0.6)

    @pytest.mark.unit
    def test_detect_equal_confidence_both_present(
        self,
        engine_with_mock_model: YOLOInferenceEngine,
    ) -> None:
        """Two detections with identical confidence are both present in the result."""
        engine_with_mock_model._model.return_value = _yolo_results(  # type: ignore[attr-defined]
            [
                _det(index=0, confidence=0.8),
                _det(index=1, confidence=0.8),
            ]
        )
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = engine_with_mock_model.detect(frame, target_labels=[])
        assert len(result) == 2
        assert all(r.confidence == pytest.approx(0.8) for r in result)


# ===========================================================================
# Section 4 — detect() Error Propagation
# ===========================================================================


class TestDetectErrorPropagation:
    """4.1 Error Propagation."""

    @pytest.mark.unit
    def test_detect_inference_runtime_failure_raises_operation_error(
        self,
        engine_with_mock_model: YOLOInferenceEngine,
    ) -> None:
        """An unexpected exception from the model's __call__ raises OperationError."""
        engine_with_mock_model._model.side_effect = RuntimeError("GPU exploded")  # type: ignore[attr-defined]
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        with pytest.raises(OperationError):
            engine_with_mock_model.detect(frame, target_labels=[])

    @pytest.mark.unit
    def test_detect_inference_with_no_nn_module_raises_operation_error(
        self,
        engine_with_mock_model: YOLOInferenceEngine,
    ) -> None:
        """detect() with _model=None raises OperationError."""
        engine_with_mock_model._model = None  # type: ignore[attr-defined]
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        with pytest.raises(OperationError):
            engine_with_mock_model.detect(frame, target_labels=[])


# ===========================================================================
# Section 5 — detect() Thread Safety (Simulated)
# ===========================================================================


class TestDetectThreadSafety:
    """5.1 Concurrent Behaviour — lock acquisition."""

    @pytest.mark.race
    def test_detect_acquires_lock_on_success(self, engine_with_mock_model: YOLOInferenceEngine) -> None:
        """The per-instance lock is acquired (and released) during a successful detect() call."""
        engine_with_mock_model._model.return_value = _yolo_results([])  # type: ignore[attr-defined]
        mock_lock = MagicMock()
        mock_lock.__enter__ = MagicMock(return_value=None)
        mock_lock.__exit__ = MagicMock(return_value=False)
        engine_with_mock_model._lock = mock_lock  # type: ignore[attr-defined]

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        engine_with_mock_model.detect(frame, target_labels=[])

        mock_lock.__enter__.assert_called_once()

    @pytest.mark.race
    def test_detect_acquires_lock_on_exception(self, engine_with_mock_model: YOLOInferenceEngine) -> None:
        """The per-instance lock is acquired (and released) even when detect() raises."""
        engine_with_mock_model._model.side_effect = RuntimeError("failure")  # type: ignore[attr-defined]
        mock_lock = MagicMock()
        mock_lock.__enter__ = MagicMock(return_value=None)
        mock_lock.__exit__ = MagicMock(return_value=False)
        engine_with_mock_model._lock = mock_lock  # type: ignore[attr-defined]

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        with pytest.raises(OperationError):
            engine_with_mock_model.detect(frame, target_labels=[])

        mock_lock.__enter__.assert_called_once()


# ===========================================================================
# Section 6 — teardown()
# ===========================================================================


class TestTeardown:
    """6.1, 6.2, 6.3 — teardown() resource release, post-teardown behaviour, thread safety."""

    @pytest.mark.unit
    def test_teardown_sets_model_to_none(self, engine_with_mock_model: YOLOInferenceEngine) -> None:
        """After teardown(), the internal _model attribute is None."""
        engine_with_mock_model.teardown()
        assert engine_with_mock_model._model is None  # type: ignore[attr-defined]

    @pytest.mark.unit
    def test_teardown_is_idempotent(self, engine_with_mock_model: YOLOInferenceEngine) -> None:
        """Calling teardown() twice does not raise."""
        engine_with_mock_model.teardown()
        engine_with_mock_model.teardown()  # must not raise

    @pytest.mark.unit
    def test_detect_after_teardown_raises_operation_error(
        self, engine_with_mock_model: YOLOInferenceEngine
    ) -> None:
        """detect() called after teardown() raises OperationError."""
        engine_with_mock_model.teardown()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        with pytest.raises(OperationError):
            engine_with_mock_model.detect(frame, target_labels=[])

    @pytest.mark.unit
    def test_get_label_map_after_teardown_raises_operation_error(
        self, engine_with_mock_model: YOLOInferenceEngine
    ) -> None:
        """get_label_map() called after teardown() raises OperationError."""
        engine_with_mock_model.teardown()
        with pytest.raises(OperationError):
            engine_with_mock_model.get_label_map()

    @pytest.mark.race
    def test_teardown_acquires_lock(self, engine_with_mock_model: YOLOInferenceEngine) -> None:
        """teardown() acquires (and releases) the per-instance lock."""
        mock_lock = MagicMock()
        mock_lock.__enter__ = MagicMock(return_value=None)
        mock_lock.__exit__ = MagicMock(return_value=False)
        engine_with_mock_model._lock = mock_lock  # type: ignore[attr-defined]

        engine_with_mock_model.teardown()

        mock_lock.__enter__.assert_called_once()


# ===========================================================================
# Section 7 — get_label_map()
# ===========================================================================


class TestGetLabelMap:
    """7.1 — get_label_map() access and copy semantics."""

    @pytest.mark.unit
    def test_get_label_map_returns_copy(self, engine_with_mock_model: YOLOInferenceEngine) -> None:
        """get_label_map() returns a copy; mutating it does not affect the engine."""
        result = engine_with_mock_model.get_label_map()
        result[999] = "injected"
        assert 999 not in engine_with_mock_model.get_label_map()

    @pytest.mark.unit
    def test_get_label_map_matches_model_names(self, engine_with_mock_model: YOLOInferenceEngine) -> None:
        """Label map matches the mock model's names attribute."""
        assert engine_with_mock_model.get_label_map() == {0: "person", 1: "bicycle", 2: "car"}

    @pytest.mark.unit
    def test_get_label_map_with_no_model_loaded(self, engine_with_mock_model: YOLOInferenceEngine) -> None:
        """get_label_map() called while _model is None raises OperationError."""
        engine_with_mock_model._model = None  # type: ignore[attr-defined]
        with pytest.raises(OperationError):
            engine_with_mock_model._get_label_map()
