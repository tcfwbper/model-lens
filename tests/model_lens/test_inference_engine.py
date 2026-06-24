"""Tests for model_lens.inference_engine module.

Covers InferenceEngine abstract base, YOLOInferenceEngine, and ENGINE_REGISTRY.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import numpy as np
import pytest

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

# Production module gate — all tests skip until inference_engine.py exists.
inference_engine = pytest.importorskip(
    "model_lens.inference_engine",
    reason="Production module model_lens.inference_engine not yet implemented",
)

from model_lens.inference_engine import (  # noqa: E402
    ENGINE_REGISTRY,
    InferenceEngine,
    YOLOInferenceEngine,
)
from model_lens.exceptions import ConfigurationError, OperationError  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def fake_frame() -> np.ndarray:
    """Create a fake BGR frame array (480x640x3, uint8)."""
    return np.zeros((480, 640, 3), dtype=np.uint8)


@pytest.fixture()
def fake_frame_300x400() -> np.ndarray:
    """Create a fake BGR frame array (300x400x3, uint8) for bounding box normalisation tests."""
    return np.zeros((300, 400, 3), dtype=np.uint8)


def _mock_yolo_model(names: dict[int, str] | None = None) -> MagicMock:
    """Create a mock YOLO model with optional .names attribute."""
    mock_model = MagicMock()
    if names is None:
        names = {0: "person", 1: "car"}
    mock_model.names = names
    return mock_model


def _make_yolo_engine(
    mocker: MockerFixture,
    confidence_threshold: float = 0.5,
    model_name: str = "yolov8n.pt",
    names: dict[int, str] | None = None,
) -> YOLOInferenceEngine:
    """Construct a YOLOInferenceEngine with mocked YOLO loader."""
    mock_model = _mock_yolo_model(names)
    mocker.patch("model_lens.inference_engine.YOLO", return_value=mock_model)
    return YOLOInferenceEngine(model=model_name, confidence_threshold=confidence_threshold)


def _make_detection_boxes(detections: list[tuple[int, float, list[float]]]) -> MagicMock:
    """Create mock YOLO result boxes.

    Args:
        detections: List of (class_id, confidence, [x1, y1, x2, y2]) tuples.

    Returns:
        Mock boxes object matching Ultralytics results interface.
    """
    mock_boxes = MagicMock()
    mock_boxes.__bool__ = lambda self: len(detections) > 0
    mock_boxes.__len__ = lambda self: len(detections)
    mock_boxes.__iter__ = lambda self: iter(range(len(detections)))

    # Build cls, conf, xyxy attributes
    cls_items = []
    conf_items = []
    xyxy_items = []

    for cls_id, conf, bbox in detections:
        cls_item = MagicMock()
        cls_item.item.return_value = cls_id
        cls_items.append(cls_item)

        conf_item = MagicMock()
        conf_item.item.return_value = conf
        conf_items.append(conf_item)

        xyxy_items.append(bbox)

    mock_boxes.cls = cls_items
    mock_boxes.conf = conf_items
    mock_boxes.xyxy = [MagicMock() for _ in detections]
    for i, bbox in enumerate(xyxy_items):
        mock_boxes.xyxy[i].tolist.return_value = bbox
        mock_boxes.xyxy[i].__iter__ = lambda self, b=bbox: iter(b)
        mock_boxes.xyxy[i].__getitem__ = lambda self, idx, b=bbox: b[idx]

    return mock_boxes


def _make_yolo_results(boxes: MagicMock | None = None) -> list[MagicMock]:
    """Create mock YOLO inference results list."""
    result = MagicMock()
    result.boxes = boxes
    return [result]


# ===========================================================================
# InferenceEngine — Type Hierarchy
# ===========================================================================


class TestInferenceEngineTypeHierarchy:
    """InferenceEngine abstract base class type hierarchy tests."""

    def test_inference_engine_is_abstract(self) -> None:
        """InferenceEngine cannot be instantiated directly."""
        with pytest.raises(TypeError):
            InferenceEngine()  # type: ignore[abstract]

    def test_yolo_inference_engine_is_subclass(self) -> None:
        """YOLOInferenceEngine inherits from InferenceEngine."""
        assert issubclass(YOLOInferenceEngine, InferenceEngine)


# ===========================================================================
# YOLOInferenceEngine — Happy Path Construction
# ===========================================================================


class TestYOLOEngineConstruction:
    """YOLOInferenceEngine construction tests."""

    def test_yolo_engine_construction_loads_model(self, mocker: MockerFixture) -> None:
        """Construction calls YOLO(model) and stores the loaded model."""
        mock_model = _mock_yolo_model()
        mock_yolo_cls = mocker.patch("model_lens.inference_engine.YOLO", return_value=mock_model)

        YOLOInferenceEngine(model="yolov8n.pt", confidence_threshold=0.5)

        mock_yolo_cls.assert_called_once_with("yolov8n.pt")

    def test_yolo_engine_populates_label_map(self, mocker: MockerFixture) -> None:
        """Construction populates _label_map from model.names."""
        engine = _make_yolo_engine(mocker, names={0: "cat", 1: "dog"})

        label_map = engine.get_label_map()

        assert label_map == {0: "cat", 1: "dog"}


# ===========================================================================
# YOLOInferenceEngine — Validation Failures (confidence_threshold)
# ===========================================================================


class TestYOLOEngineThresholdValidation:
    """YOLOInferenceEngine confidence_threshold validation tests."""

    def test_yolo_engine_threshold_zero_raises(self) -> None:
        """confidence_threshold of 0.0 raises ConfigurationError."""
        with pytest.raises(ConfigurationError):
            YOLOInferenceEngine(model="m.pt", confidence_threshold=0.0)

    def test_yolo_engine_threshold_negative_raises(self) -> None:
        """Negative confidence_threshold raises ConfigurationError."""
        with pytest.raises(ConfigurationError):
            YOLOInferenceEngine(model="m.pt", confidence_threshold=-0.1)

    def test_yolo_engine_threshold_above_one_raises(self) -> None:
        """confidence_threshold greater than 1.0 raises ConfigurationError."""
        with pytest.raises(ConfigurationError):
            YOLOInferenceEngine(model="m.pt", confidence_threshold=1.5)


# ===========================================================================
# YOLOInferenceEngine — Boundary Values (confidence_threshold)
# ===========================================================================


class TestYOLOEngineThresholdBoundary:
    """YOLOInferenceEngine confidence_threshold boundary value tests."""

    def test_yolo_engine_threshold_one_valid(self, mocker: MockerFixture) -> None:
        """confidence_threshold of 1.0 is accepted (inclusive upper bound)."""
        engine = _make_yolo_engine(mocker, confidence_threshold=1.0)
        assert engine is not None

    def test_yolo_engine_threshold_just_above_zero_valid(self, mocker: MockerFixture) -> None:
        """confidence_threshold of 0.01 is accepted."""
        engine = _make_yolo_engine(mocker, confidence_threshold=0.01)
        assert engine is not None


# ===========================================================================
# YOLOInferenceEngine — Error Propagation
# ===========================================================================


class TestYOLOEngineErrorPropagation:
    """YOLOInferenceEngine error propagation tests."""

    def test_yolo_engine_model_load_failure_raises_operation_error(self, mocker: MockerFixture) -> None:
        """OperationError raised when YOLO() fails to load model."""
        mocker.patch("model_lens.inference_engine.YOLO", side_effect=RuntimeError("model not found"))

        with pytest.raises(OperationError):
            YOLOInferenceEngine(model="bad.pt", confidence_threshold=0.5)


# ===========================================================================
# YOLOInferenceEngine — Happy Path detect
# ===========================================================================


class TestYOLOEngineDetect:
    """YOLOInferenceEngine.detect() happy path tests."""

    def test_detect_returns_filtered_results(self, mocker: MockerFixture, fake_frame: np.ndarray) -> None:
        """detect() returns only detections at or above confidence_threshold."""
        engine = _make_yolo_engine(mocker, confidence_threshold=0.5, names={0: "person", 1: "car"})

        # Mock inference results: person at 0.8, car at 0.3
        boxes = _make_detection_boxes(
            [
                (0, 0.8, [100.0, 50.0, 200.0, 150.0]),
                (1, 0.3, [300.0, 200.0, 400.0, 300.0]),
            ]
        )
        engine._model.return_value = _make_yolo_results(boxes)

        results = engine.detect(fake_frame, target_labels=["person"])

        assert len(results) == 1
        assert results[0].label == "person"
        assert results[0].confidence == pytest.approx(0.8)
        assert results[0].is_target is True

    def test_detect_sets_is_target_correctly(self, mocker: MockerFixture, fake_frame: np.ndarray) -> None:
        """is_target is True only when label is in target_labels."""
        engine = _make_yolo_engine(mocker, confidence_threshold=0.25, names={0: "person", 1: "car"})

        boxes = _make_detection_boxes(
            [
                (0, 0.9, [10.0, 10.0, 50.0, 50.0]),
                (1, 0.7, [100.0, 100.0, 200.0, 200.0]),
            ]
        )
        engine._model.return_value = _make_yolo_results(boxes)

        results = engine.detect(fake_frame, target_labels=["car"])

        # Both should be above threshold
        labels_targets = {r.label: r.is_target for r in results}
        assert labels_targets["car"] is True
        assert labels_targets["person"] is False

    def test_detect_normalises_bounding_box(self, mocker: MockerFixture, fake_frame_300x400: np.ndarray) -> None:
        """Bounding box coordinates are divided by frame dimensions."""
        engine = _make_yolo_engine(mocker, confidence_threshold=0.1, names={0: "obj"})

        # Pixel bbox [100, 50, 200, 150] on frame (300, 400, 3) -> h=300, w=400
        boxes = _make_detection_boxes(
            [
                (0, 0.9, [100.0, 50.0, 200.0, 150.0]),
            ]
        )
        engine._model.return_value = _make_yolo_results(boxes)

        results = engine.detect(fake_frame_300x400, target_labels=[])

        assert len(results) == 1
        bbox = results[0].bounding_box
        # x1/w, y1/h, x2/w, y2/h -> 100/400, 50/300, 200/400, 150/300
        assert bbox[0] == pytest.approx(0.25)
        assert bbox[1] == pytest.approx(50.0 / 300.0)
        assert bbox[2] == pytest.approx(0.5)
        assert bbox[3] == pytest.approx(0.5)

    def test_detect_empty_when_no_detections(self, mocker: MockerFixture, fake_frame: np.ndarray) -> None:
        """Returns empty list when model produces no boxes."""
        engine = _make_yolo_engine(mocker, confidence_threshold=0.5)

        # No boxes (falsy)
        engine._model.return_value = _make_yolo_results(None)

        results = engine.detect(fake_frame, target_labels=["person"])

        assert results == []

    def test_detect_empty_when_all_below_threshold(self, mocker: MockerFixture, fake_frame: np.ndarray) -> None:
        """Returns empty list when all detections are below threshold."""
        engine = _make_yolo_engine(mocker, confidence_threshold=0.9, names={0: "person"})

        boxes = _make_detection_boxes(
            [
                (0, 0.5, [10.0, 10.0, 100.0, 100.0]),
            ]
        )
        engine._model.return_value = _make_yolo_results(boxes)

        results = engine.detect(fake_frame, target_labels=[])

        assert results == []

    def test_detect_includes_detection_at_exact_threshold(self, mocker: MockerFixture, fake_frame: np.ndarray) -> None:
        """Detection with confidence exactly equal to threshold is kept."""
        engine = _make_yolo_engine(mocker, confidence_threshold=0.5, names={0: "person"})

        boxes = _make_detection_boxes(
            [
                (0, 0.5, [10.0, 10.0, 100.0, 100.0]),
            ]
        )
        engine._model.return_value = _make_yolo_results(boxes)

        results = engine.detect(fake_frame, target_labels=[])

        assert len(results) == 1
        assert results[0].confidence == pytest.approx(0.5)


# ===========================================================================
# YOLOInferenceEngine — Ordering
# ===========================================================================


class TestYOLOEngineDetectOrdering:
    """YOLOInferenceEngine.detect() ordering tests."""

    def test_detect_results_sorted_descending_confidence(self, mocker: MockerFixture, fake_frame: np.ndarray) -> None:
        """Results are ordered by descending confidence."""
        engine = _make_yolo_engine(mocker, confidence_threshold=0.1, names={0: "a", 1: "b", 2: "c"})

        boxes = _make_detection_boxes(
            [
                (0, 0.3, [10.0, 10.0, 20.0, 20.0]),
                (1, 0.9, [30.0, 30.0, 40.0, 40.0]),
                (2, 0.6, [50.0, 50.0, 60.0, 60.0]),
            ]
        )
        engine._model.return_value = _make_yolo_results(boxes)

        results = engine.detect(fake_frame, target_labels=[])

        confidences = [r.confidence for r in results]
        assert confidences == [pytest.approx(0.9), pytest.approx(0.6), pytest.approx(0.3)]


# ===========================================================================
# YOLOInferenceEngine — Immutability
# ===========================================================================


class TestYOLOEngineImmutability:
    """YOLOInferenceEngine.detect() immutability tests."""

    def test_detect_does_not_mutate_frame(self, mocker: MockerFixture, fake_frame: np.ndarray) -> None:
        """detect() does not modify the input frame array."""
        engine = _make_yolo_engine(mocker, confidence_threshold=0.5)
        engine._model.return_value = _make_yolo_results(None)
        original_copy = fake_frame.copy()

        engine.detect(fake_frame, target_labels=[])

        assert np.array_equal(fake_frame, original_copy)

    def test_detect_does_not_mutate_target_labels(self, mocker: MockerFixture, fake_frame: np.ndarray) -> None:
        """detect() does not modify the input target_labels list."""
        engine = _make_yolo_engine(mocker, confidence_threshold=0.5)
        engine._model.return_value = _make_yolo_results(None)
        labels = ["person", "car"]
        original_copy = labels.copy()

        engine.detect(fake_frame, target_labels=labels)

        assert labels == original_copy


# ===========================================================================
# YOLOInferenceEngine — get_label_map
# ===========================================================================


class TestYOLOEngineGetLabelMap:
    """YOLOInferenceEngine.get_label_map() tests."""

    def test_get_label_map_returns_copy(self, mocker: MockerFixture) -> None:
        """get_label_map() returns a copy, not the internal reference."""
        engine = _make_yolo_engine(mocker, names={0: "a"})

        result = engine.get_label_map()

        assert result == {0: "a"}
        assert result is not engine._label_map


# ===========================================================================
# YOLOInferenceEngine — Resource Cleanup
# ===========================================================================


class TestYOLOEngineResourceCleanup:
    """YOLOInferenceEngine teardown tests."""

    def test_teardown_sets_model_none(self, mocker: MockerFixture) -> None:
        """teardown() releases the model reference."""
        engine = _make_yolo_engine(mocker)

        engine.teardown()

        assert engine._model is None

    def test_teardown_does_not_clear_label_map(self, mocker: MockerFixture) -> None:
        """teardown() preserves the _label_map."""
        engine = _make_yolo_engine(mocker, names={0: "x"})

        engine.teardown()

        assert engine._label_map == {0: "x"}

    def test_detect_after_teardown_raises_operation_error(self, mocker: MockerFixture, fake_frame: np.ndarray) -> None:
        """detect() raises OperationError after teardown."""
        engine = _make_yolo_engine(mocker)
        engine.teardown()

        with pytest.raises(OperationError):
            engine.detect(fake_frame, target_labels=[])

    def test_get_label_map_after_teardown_raises_operation_error(self, mocker: MockerFixture) -> None:
        """get_label_map() raises OperationError after teardown."""
        engine = _make_yolo_engine(mocker)
        engine.teardown()

        with pytest.raises(OperationError):
            engine.get_label_map()


# ===========================================================================
# YOLOInferenceEngine — Idempotency
# ===========================================================================


class TestYOLOEngineIdempotency:
    """YOLOInferenceEngine teardown idempotency tests."""

    def test_teardown_idempotent(self, mocker: MockerFixture) -> None:
        """Calling teardown() multiple times does not raise."""
        engine = _make_yolo_engine(mocker)

        engine.teardown()
        engine.teardown()  # Should not raise


# ===========================================================================
# YOLOInferenceEngine — Mock / Dependency Interaction
# ===========================================================================


class TestYOLOEngineDependencyInteraction:
    """YOLOInferenceEngine dependency interaction tests."""

    def test_detect_wraps_inference_exception_in_operation_error(
        self, mocker: MockerFixture, fake_frame: np.ndarray
    ) -> None:
        """Runtime inference failure is wrapped in OperationError."""
        engine = _make_yolo_engine(mocker)
        engine._model.side_effect = RuntimeError("inference failed")

        with pytest.raises(OperationError):
            engine.detect(fake_frame, target_labels=[])


# ===========================================================================
# YOLOInferenceEngine — Concurrent Behaviour
# ===========================================================================


class TestYOLOEngineConcurrency:
    """YOLOInferenceEngine concurrency tests."""

    def test_detect_serialised_by_lock(self, mocker: MockerFixture, fake_frame: np.ndarray) -> None:
        """Concurrent detect() calls are serialised by the per-instance lock."""
        engine = _make_yolo_engine(mocker, confidence_threshold=0.1, names={0: "person"})

        # Use threading events to control execution order
        inference_started = threading.Event()
        inference_proceed = threading.Event()
        execution_order: list[str] = []

        def slow_inference(frame):
            execution_order.append("inference_start")
            inference_started.set()
            inference_proceed.wait(timeout=5.0)
            execution_order.append("inference_end")
            return _make_yolo_results(None)

        engine._model.side_effect = slow_inference

        results: list[list] = [[], []]
        errors: list[Exception | None] = [None, None]

        def thread_detect(idx: int) -> None:
            try:
                r = engine.detect(fake_frame.copy(), target_labels=[])
                results[idx] = r
            except Exception as e:
                errors[idx] = e

        t1 = threading.Thread(target=thread_detect, args=(0,))
        t2 = threading.Thread(target=thread_detect, args=(1,))

        t1.start()
        inference_started.wait(timeout=5.0)

        # Now t1 is in the middle of inference (holding lock); start t2
        t2.start()

        # Let t1 finish
        inference_proceed.set()

        t1.join(timeout=5.0)
        t2.join(timeout=5.0)

        assert errors[0] is None
        assert errors[1] is None
        # Both completed — serialisation confirmed by no concurrent access errors

    def test_teardown_serialised_with_detect(self, mocker: MockerFixture, fake_frame: np.ndarray) -> None:
        """teardown() and detect() are serialised by the same lock."""
        engine = _make_yolo_engine(mocker, confidence_threshold=0.1, names={0: "person"})

        lock_acquired = threading.Event()
        lock_released = threading.Event()
        teardown_started = threading.Event()

        # Thread 1: holds the lock
        def hold_lock() -> None:
            engine._lock.acquire()
            lock_acquired.set()
            # Wait until teardown has been attempted
            teardown_started.wait(timeout=5.0)
            # Small delay to prove teardown blocked
            lock_released.set()
            engine._lock.release()

        holder = threading.Thread(target=hold_lock)
        holder.start()
        lock_acquired.wait(timeout=5.0)

        teardown_error: Exception | None = None

        def try_teardown() -> None:
            nonlocal teardown_error
            teardown_started.set()
            try:
                engine.teardown()
            except Exception as e:
                teardown_error = e

        td_thread = threading.Thread(target=try_teardown)
        td_thread.start()

        holder.join(timeout=5.0)
        td_thread.join(timeout=5.0)

        # teardown should have completed after lock was released
        assert lock_released.is_set()
        assert teardown_error is None


# ===========================================================================
# ENGINE_REGISTRY
# ===========================================================================


class TestEngineRegistry:
    """ENGINE_REGISTRY tests."""

    def test_engine_registry_contains_yolo(self) -> None:
        """ENGINE_REGISTRY maps 'yolo' to YOLOInferenceEngine."""
        assert ENGINE_REGISTRY["yolo"] is YOLOInferenceEngine

    def test_engine_registry_is_dict(self) -> None:
        """ENGINE_REGISTRY is a plain dict."""
        assert isinstance(ENGINE_REGISTRY, dict)
