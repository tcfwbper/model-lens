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

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from model_lens.exceptions import ConfigurationError, OperationError, ParseError
from model_lens.inference_engine import TorchInferenceEngine, _resolve_package_resource


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_raw_detection(
    index: int,
    confidence: float,
    box: tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0),
) -> dict:
    return {"index": index, "confidence": confidence, "box": list(box)}


# ===========================================================================
# Section 1 — Constructor: Label Map Loading
# ===========================================================================


class TestLabelMapHappyPath:
    """1.1 Happy Path — Construction (label map)."""

    def _make_engine(self, tmp_path: Path, label_content: str) -> TorchInferenceEngine:
        labels_file = tmp_path / "labels.txt"
        labels_file.write_text(label_content, encoding="utf-8")
        dummy_model = tmp_path / "model.pt"
        dummy_model.write_bytes(b"")
        with patch("model_lens.inference_engine.torch.load", return_value=MagicMock()):
            return TorchInferenceEngine(
                model_path=str(dummy_model),
                confidence_threshold=0.5,
                labels_path=str(labels_file),
            )

    @pytest.mark.unit
    def test_label_map_single_label(self, tmp_path: Path) -> None:
        """A file with one non-blank line produces a single-entry map."""
        engine = self._make_engine(tmp_path, "person\n")
        assert engine._label_map == {0: "person"}  # type: ignore[attr-defined]

    @pytest.mark.unit
    def test_label_map_multiple_labels(self, tmp_path: Path) -> None:
        """Multiple non-blank lines are indexed sequentially from 0."""
        engine = self._make_engine(tmp_path, "person\nbicycle\ncar\n")
        assert engine._label_map == {0: "person", 1: "bicycle", 2: "car"}  # type: ignore[attr-defined]

    @pytest.mark.unit
    def test_label_map_blank_line_consumes_index(self, tmp_path: Path) -> None:
        """A blank line in the middle consumes an index slot and is stored as ''."""
        engine = self._make_engine(tmp_path, "person\nbicycle\n\nmotorcycle\n")
        assert engine._label_map == {0: "person", 1: "bicycle", 2: "", 3: "motorcycle"}  # type: ignore[attr-defined]

    @pytest.mark.unit
    def test_label_map_leading_trailing_whitespace_stripped(self, tmp_path: Path) -> None:
        """Leading and trailing whitespace on non-blank lines is stripped."""
        engine = self._make_engine(tmp_path, "  person  \n  bicycle\n")
        assert engine._label_map == {0: "person", 1: "bicycle"}  # type: ignore[attr-defined]

    @pytest.mark.unit
    def test_label_map_whitespace_only_line_stored_as_empty_string(self, tmp_path: Path) -> None:
        """A whitespace-only line is stored as ''."""
        engine = self._make_engine(tmp_path, "person\n   \ncar\n")
        assert engine._label_map == {0: "person", 1: "", 2: "car"}  # type: ignore[attr-defined]

    @pytest.mark.unit
    def test_label_map_no_trailing_newline(self, tmp_path: Path) -> None:
        """A file without a trailing newline is parsed correctly."""
        engine = self._make_engine(tmp_path, "person\nbicycle")
        assert engine._label_map == {0: "person", 1: "bicycle"}  # type: ignore[attr-defined]


class TestLabelMapValidationFailures:
    """1.2 Validation Failures — labels_path."""

    def _make_model_file(self, tmp_path: Path) -> Path:
        model_file = tmp_path / "model.pt"
        model_file.write_bytes(b"")
        return model_file

    @pytest.mark.unit
    def test_label_map_file_not_found(self, tmp_path: Path) -> None:
        """A non-existent labels_path raises ConfigurationError."""
        model_file = self._make_model_file(tmp_path)
        with patch("model_lens.inference_engine.torch.load", return_value=MagicMock()):
            with pytest.raises(ConfigurationError):
                TorchInferenceEngine(
                    model_path=str(model_file),
                    confidence_threshold=0.5,
                    labels_path="/nonexistent/labels.txt",
                )

    @pytest.mark.unit
    def test_label_map_empty_file(self, tmp_path: Path) -> None:
        """A completely empty file (zero bytes) raises ParseError."""
        model_file = self._make_model_file(tmp_path)
        labels_file = tmp_path / "labels.txt"
        labels_file.write_text("", encoding="utf-8")
        with patch("model_lens.inference_engine.torch.load", return_value=MagicMock()):
            with pytest.raises(ParseError):
                TorchInferenceEngine(
                    model_path=str(model_file),
                    confidence_threshold=0.5,
                    labels_path=str(labels_file),
                )

    @pytest.mark.unit
    def test_label_map_only_blank_lines(self, tmp_path: Path) -> None:
        """A file containing only blank lines raises ParseError."""
        model_file = self._make_model_file(tmp_path)
        labels_file = tmp_path / "labels.txt"
        labels_file.write_text("\n\n\n", encoding="utf-8")
        with patch("model_lens.inference_engine.torch.load", return_value=MagicMock()):
            with pytest.raises(ParseError):
                TorchInferenceEngine(
                    model_path=str(model_file),
                    confidence_threshold=0.5,
                    labels_path=str(labels_file),
                )


class TestLabelMapLoadingValidationFailures:
    """1.3 Validation Failures — Label Map Loading.

    Exercises branches inside ``InferenceEngine._load_label_map`` that are not
    reachable through the normal ``TorchInferenceEngine`` constructor path:

    * The ``not path.exists()`` branch when called directly.
    * The ``OSError`` branch triggered when the file exists but cannot be read.
    """

    @pytest.mark.unit
    def test_inference_engine_label_map_file_not_found_raises_configuration_error(
        self,
        tmp_path: Path,
    ) -> None:
        """Raises ConfigurationError when the label map file does not exist."""
        from model_lens.inference_engine import InferenceEngine

        missing_path = str(tmp_path / "nonexistent_labels.txt")
        with pytest.raises(ConfigurationError):
            InferenceEngine._load_label_map(missing_path)

    @pytest.mark.unit
    def test_inference_engine_label_map_file_unreadable_raises_configuration_error(
        self,
        tmp_path: Path,
    ) -> None:
        """Raises ConfigurationError when the label map file exists but cannot be read."""
        from model_lens.inference_engine import InferenceEngine

        labels_file = tmp_path / "labels.txt"
        labels_file.write_text("person\n", encoding="utf-8")

        with patch.object(Path, "read_text", side_effect=OSError("permission denied")):
            with pytest.raises(ConfigurationError):
                InferenceEngine._load_label_map(str(labels_file))


class TestPackageDataResourceResolution:
    """1.4 Error Propagation — Package-Data Fallback.

    Exercises the ``except Exception`` block inside ``_resolve_package_resource``
    that wraps any resolution failure as ``FileNotFoundError``, and verifies that
    ``TorchInferenceEngine._resolve_path`` surfaces this as ``ConfigurationError``.
    """

    @pytest.mark.unit
    def test_resolve_package_resource_wraps_exception_as_file_not_found_error(self) -> None:
        """_resolve_package_resource wraps any internal exception as FileNotFoundError."""
        with patch(
            "importlib.resources.files",
            side_effect=Exception("unexpected internal error"),
        ):
            with pytest.raises(FileNotFoundError):
                _resolve_package_resource("model.pt")

    @pytest.mark.unit
    def test_torch_inference_engine_package_data_unresolvable_raises_configuration_error(
        self,
        tmp_path: Path,
        label_map_file: Path,
    ) -> None:
        """Raises ConfigurationError when the package-data resource cannot be located.

        Patches ``importlib.resources.files`` to raise an arbitrary exception,
        simulating a broken or missing package-data installation, and confirms
        that ``TorchInferenceEngine`` surfaces this as ``ConfigurationError``
        rather than leaking the internal ``FileNotFoundError``.
        """
        with patch(
            "importlib.resources.files",
            side_effect=Exception("package data unavailable"),
        ):
            with pytest.raises(ConfigurationError):
                TorchInferenceEngine(
                    model_path="",  # triggers package-data resolution for model_path
                    confidence_threshold=0.5,
                    labels_path=str(label_map_file),
                )


# ===========================================================================
# Section 2 — Constructor: Model Loading
# ===========================================================================


class TestModelLoadingHappyPath:
    """2.1 Happy Path — Construction (model loading)."""

    @pytest.mark.unit
    def test_model_loads_successfully(self, tmp_path: Path, label_map_file: Path) -> None:
        """A valid model_path pointing to an existing file constructs without error."""
        model_file = tmp_path / "model.pt"
        model_file.write_bytes(b"")
        with patch("model_lens.inference_engine.torch.load", return_value=MagicMock()):
            engine = TorchInferenceEngine(
                model_path=str(model_file),
                confidence_threshold=0.5,
                labels_path=str(label_map_file),
            )
        assert engine is not None


class TestModelLoadingValidationFailures:
    """2.2 & 2.3 Validation Failures — model_path and confidence_threshold."""

    @pytest.mark.unit
    def test_model_path_not_found(self, tmp_path: Path, label_map_file: Path) -> None:
        """A non-existent model_path raises ConfigurationError."""
        with pytest.raises(ConfigurationError):
            TorchInferenceEngine(
                model_path="/nonexistent/model.pt",
                confidence_threshold=0.5,
                labels_path=str(label_map_file),
            )

    @pytest.mark.unit
    def test_model_load_failure(self, tmp_path: Path, label_map_file: Path) -> None:
        """An existing file that PyTorch cannot load raises OperationError."""
        model_file = tmp_path / "model.pt"
        model_file.write_bytes(b"")
        with patch("model_lens.inference_engine.torch.load", side_effect=Exception("corrupt")):
            with pytest.raises(OperationError):
                TorchInferenceEngine(
                    model_path=str(model_file),
                    confidence_threshold=0.5,
                    labels_path=str(label_map_file),
                )

    @pytest.mark.unit
    def test_confidence_threshold_zero_raises(self, tmp_path: Path, label_map_file: Path) -> None:
        """confidence_threshold=0.0 violates 0.0 < value constraint."""
        model_file = tmp_path / "model.pt"
        model_file.write_bytes(b"")
        with patch("model_lens.inference_engine.torch.load", return_value=MagicMock()):
            with pytest.raises(ConfigurationError):
                TorchInferenceEngine(
                    model_path=str(model_file),
                    confidence_threshold=0.0,
                    labels_path=str(label_map_file),
                )

    @pytest.mark.unit
    def test_confidence_threshold_negative_raises(self, tmp_path: Path, label_map_file: Path) -> None:
        """Negative confidence_threshold raises ConfigurationError."""
        model_file = tmp_path / "model.pt"
        model_file.write_bytes(b"")
        with patch("model_lens.inference_engine.torch.load", return_value=MagicMock()):
            with pytest.raises(ConfigurationError):
                TorchInferenceEngine(
                    model_path=str(model_file),
                    confidence_threshold=-0.1,
                    labels_path=str(label_map_file),
                )

    @pytest.mark.unit
    def test_confidence_threshold_above_one_raises(self, tmp_path: Path, label_map_file: Path) -> None:
        """confidence_threshold > 1.0 raises ConfigurationError."""
        model_file = tmp_path / "model.pt"
        model_file.write_bytes(b"")
        with patch("model_lens.inference_engine.torch.load", return_value=MagicMock()):
            with pytest.raises(ConfigurationError):
                TorchInferenceEngine(
                    model_path=str(model_file),
                    confidence_threshold=1.001,
                    labels_path=str(label_map_file),
                )

    @pytest.mark.unit
    def test_confidence_threshold_at_upper_boundary(self, tmp_path: Path, label_map_file: Path) -> None:
        """confidence_threshold=1.0 is valid."""
        model_file = tmp_path / "model.pt"
        model_file.write_bytes(b"")
        with patch("model_lens.inference_engine.torch.load", return_value=MagicMock()):
            engine = TorchInferenceEngine(
                model_path=str(model_file),
                confidence_threshold=1.0,
                labels_path=str(label_map_file),
            )
        assert engine is not None

    @pytest.mark.unit
    def test_confidence_threshold_just_above_zero(self, tmp_path: Path, label_map_file: Path) -> None:
        """confidence_threshold just above 0.0 is valid."""
        model_file = tmp_path / "model.pt"
        model_file.write_bytes(b"")
        with patch("model_lens.inference_engine.torch.load", return_value=MagicMock()):
            engine = TorchInferenceEngine(
                model_path=str(model_file),
                confidence_threshold=1e-9,
                labels_path=str(label_map_file),
            )
        assert engine is not None


# ===========================================================================
# Section 3 — Constructor: Package-Data Fallback
# ===========================================================================


class TestPackageDataFallback:
    """3.1 & 3.2 Package-data fallback — empty model_path / labels_path."""

    @pytest.mark.unit
    def test_empty_model_path_uses_package_data(self, tmp_path: Path, label_map_file: Path) -> None:
        """model_path='' triggers package-data resolution; succeeds when resource is found."""
        dummy_model = tmp_path / "model.pt"
        dummy_model.write_bytes(b"")
        with (
            patch(
                "model_lens.inference_engine._resolve_package_resource",
                return_value=str(dummy_model),
            ),
            patch("model_lens.inference_engine.torch.load", return_value=MagicMock()),
        ):
            engine = TorchInferenceEngine(
                model_path="",
                confidence_threshold=0.5,
                labels_path=str(label_map_file),
            )
        assert engine is not None

    @pytest.mark.unit
    def test_empty_labels_path_uses_package_data(self, tmp_path: Path, dummy_model_file: Path) -> None:
        """labels_path='' triggers package-data resolution; succeeds when resource is found."""
        labels = tmp_path / "pkg_labels.txt"
        labels.write_text("person\nbicycle\ncar\n", encoding="utf-8")
        with (
            patch(
                "model_lens.inference_engine._resolve_package_resource",
                return_value=str(labels),
            ),
            patch("model_lens.inference_engine.torch.load", return_value=MagicMock()),
        ):
            engine = TorchInferenceEngine(
                model_path=str(dummy_model_file),
                confidence_threshold=0.5,
                labels_path="",
            )
        assert engine is not None

    @pytest.mark.unit
    def test_empty_model_path_package_data_missing(self, tmp_path: Path, label_map_file: Path) -> None:
        """model_path='' and package-data resource cannot be resolved raises ConfigurationError."""
        with patch(
            "model_lens.inference_engine._resolve_package_resource",
            side_effect=FileNotFoundError("no package data"),
        ):
            with pytest.raises(ConfigurationError):
                TorchInferenceEngine(
                    model_path="",
                    confidence_threshold=0.5,
                    labels_path=str(label_map_file),
                )

    @pytest.mark.unit
    def test_empty_labels_path_package_data_missing(self, tmp_path: Path, dummy_model_file: Path) -> None:
        """labels_path='' and package-data resource cannot be resolved raises ConfigurationError."""
        with patch(
            "model_lens.inference_engine._resolve_package_resource",
            side_effect=FileNotFoundError("no package data"),
        ):
            with pytest.raises(ConfigurationError):
                TorchInferenceEngine(
                    model_path=str(dummy_model_file),
                    confidence_threshold=0.5,
                    labels_path="",
                )


# ===========================================================================
# Section 4 — detect() Happy Path
# ===========================================================================


class TestDetectHappyPath:
    """4.1 Happy Path — detect()."""

    @pytest.mark.unit
    def test_detect_returns_list(self, engine_with_mock_model: TorchInferenceEngine) -> None:
        """detect() always returns a list."""
        engine_with_mock_model._model.return_value = []  # type: ignore[attr-defined]
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = engine_with_mock_model.detect(frame, target_labels=[])
        assert isinstance(result, list)

    @pytest.mark.unit
    def test_detect_empty_when_no_detections(self, engine_with_mock_model: TorchInferenceEngine) -> None:
        """No detections above threshold returns empty list."""
        engine_with_mock_model._model.return_value = []  # type: ignore[attr-defined]
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = engine_with_mock_model.detect(frame, target_labels=[])
        assert result == []

    @pytest.mark.unit
    def test_detect_single_result_fields(self, engine_with_mock_model: TorchInferenceEngine) -> None:
        """A single detection above threshold produces one DetectionResult with correct fields."""
        engine_with_mock_model._model.return_value = [  # type: ignore[attr-defined]
            _make_raw_detection(index=0, confidence=0.9, box=(0.1, 0.2, 0.4, 0.6))
        ]
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = engine_with_mock_model.detect(frame, target_labels=[])
        assert len(result) == 1
        assert result[0].label == "person"
        assert result[0].confidence == pytest.approx(0.9)
        assert result[0].bounding_box == (0.1, 0.2, 0.4, 0.6)

    @pytest.mark.unit
    def test_detect_is_target_true(self, engine_with_mock_model: TorchInferenceEngine) -> None:
        """is_target is True when label is in target_labels."""
        engine_with_mock_model._model.return_value = [  # type: ignore[attr-defined]
            _make_raw_detection(index=0, confidence=0.9)
        ]
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = engine_with_mock_model.detect(frame, target_labels=["person"])
        assert result[0].is_target is True

    @pytest.mark.unit
    def test_detect_is_target_false(self, engine_with_mock_model: TorchInferenceEngine) -> None:
        """is_target is False when label is not in target_labels."""
        engine_with_mock_model._model.return_value = [  # type: ignore[attr-defined]
            _make_raw_detection(index=0, confidence=0.9)
        ]
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = engine_with_mock_model.detect(frame, target_labels=[])
        assert result[0].is_target is False

    @pytest.mark.unit
    def test_detect_does_not_mutate_frame(self, engine_with_mock_model: TorchInferenceEngine) -> None:
        """detect() does not modify the input frame array."""
        engine_with_mock_model._model.return_value = []  # type: ignore[attr-defined]
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame_before = frame.copy()
        engine_with_mock_model.detect(frame, target_labels=[])
        assert np.array_equal(frame, frame_before)

    @pytest.mark.unit
    def test_detect_does_not_mutate_target_labels(self, engine_with_mock_model: TorchInferenceEngine) -> None:
        """detect() does not modify the target_labels list."""
        engine_with_mock_model._model.return_value = []  # type: ignore[attr-defined]
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        target_labels = ["person", "bicycle"]
        target_labels_before = target_labels.copy()
        engine_with_mock_model.detect(frame, target_labels=target_labels)
        assert target_labels == target_labels_before


# ===========================================================================
# Section 4 — detect() Boundary Values: confidence_threshold
# ===========================================================================


class TestDetectThresholdFiltering:
    """4.2 Boundary Values — confidence_threshold filtering."""

    @pytest.mark.unit
    def test_detect_filters_below_threshold(self, engine_with_mock_model: TorchInferenceEngine) -> None:
        """Detection with confidence strictly below threshold is excluded."""
        engine_with_mock_model._model.return_value = [  # type: ignore[attr-defined]
            _make_raw_detection(index=0, confidence=0.49)
        ]
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = engine_with_mock_model.detect(frame, target_labels=[])
        assert result == []

    @pytest.mark.unit
    def test_detect_keeps_at_threshold(self, engine_with_mock_model: TorchInferenceEngine) -> None:
        """Detection with confidence exactly equal to threshold is kept."""
        engine_with_mock_model._model.return_value = [  # type: ignore[attr-defined]
            _make_raw_detection(index=0, confidence=0.5)
        ]
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = engine_with_mock_model.detect(frame, target_labels=[])
        assert len(result) == 1

    @pytest.mark.unit
    def test_detect_keeps_above_threshold(self, engine_with_mock_model: TorchInferenceEngine) -> None:
        """Detection with confidence above threshold is kept."""
        engine_with_mock_model._model.return_value = [  # type: ignore[attr-defined]
            _make_raw_detection(index=0, confidence=0.51)
        ]
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = engine_with_mock_model.detect(frame, target_labels=[])
        assert len(result) == 1


# ===========================================================================
# Section 4 — detect() Ordering: Descending Confidence
# ===========================================================================


class TestDetectOrdering:
    """4.3 Ordering — Descending Confidence."""

    @pytest.mark.unit
    def test_detect_results_ordered_by_descending_confidence(
        self,
        engine_with_mock_model: TorchInferenceEngine,
    ) -> None:
        """Multiple detections are returned in descending confidence order."""
        engine_with_mock_model._model.return_value = [  # type: ignore[attr-defined]
            _make_raw_detection(index=0, confidence=0.6),
            _make_raw_detection(index=1, confidence=0.9),
            _make_raw_detection(index=2, confidence=0.75),
        ]
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = engine_with_mock_model.detect(frame, target_labels=[])
        assert result[0].confidence == pytest.approx(0.9)
        assert result[1].confidence == pytest.approx(0.75)
        assert result[2].confidence == pytest.approx(0.6)

    @pytest.mark.unit
    def test_detect_equal_confidence_both_present(
        self,
        engine_with_mock_model: TorchInferenceEngine,
    ) -> None:
        """Two detections with identical confidence are both present in the result."""
        engine_with_mock_model._model.return_value = [  # type: ignore[attr-defined]
            _make_raw_detection(index=0, confidence=0.8),
            _make_raw_detection(index=1, confidence=0.8),
        ]
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = engine_with_mock_model.detect(frame, target_labels=[])
        assert len(result) == 2
        assert all(r.confidence == pytest.approx(0.8) for r in result)


# ===========================================================================
# Section 5 — detect() Validation Failures / Error Propagation
# ===========================================================================


class TestDetectErrorPropagation:
    """5.1 Error Propagation."""

    @pytest.mark.unit
    def test_detect_unknown_label_index_raises_parse_error(
        self,
        engine_with_mock_model: TorchInferenceEngine,
    ) -> None:
        """A raw model output index with no entry in the label map raises ParseError."""
        engine_with_mock_model._model.return_value = [  # type: ignore[attr-defined]
            _make_raw_detection(index=999, confidence=0.9)
        ]
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        with pytest.raises(ParseError):
            engine_with_mock_model.detect(frame, target_labels=[])

    @pytest.mark.unit
    def test_detect_inference_runtime_failure_raises_operation_error(
        self,
        engine_with_mock_model: TorchInferenceEngine,
    ) -> None:
        """An unexpected exception from the model's __call__ raises OperationError."""
        engine_with_mock_model._model.side_effect = RuntimeError("GPU exploded")  # type: ignore[attr-defined]
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        with pytest.raises(OperationError):
            engine_with_mock_model.detect(frame, target_labels=[])


# ===========================================================================
# Section 6 — detect() Thread Safety (Simulated)
# ===========================================================================


class TestDetectThreadSafety:
    """6.1 Concurrent Behaviour — lock acquisition."""

    @pytest.mark.race
    def test_detect_acquires_lock_on_success(self, engine_with_mock_model: TorchInferenceEngine) -> None:
        """The per-instance lock is acquired (and released) during a successful detect() call."""
        engine_with_mock_model._model.return_value = []  # type: ignore[attr-defined]
        mock_lock = MagicMock()
        mock_lock.__enter__ = MagicMock(return_value=None)
        mock_lock.__exit__ = MagicMock(return_value=False)
        engine_with_mock_model._lock = mock_lock  # type: ignore[attr-defined]

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        engine_with_mock_model.detect(frame, target_labels=[])

        mock_lock.__enter__.assert_called_once()

    @pytest.mark.race
    def test_detect_acquires_lock_on_exception(self, engine_with_mock_model: TorchInferenceEngine) -> None:
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
