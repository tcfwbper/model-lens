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

"""Shared fixtures for YOLOInferenceEngine tests."""

from unittest.mock import MagicMock, patch

import pytest

from model_lens.inference_engine import YOLOInferenceEngine

_DEFAULT_NAMES = {0: "person", 1: "bicycle", 2: "car"}


@pytest.fixture()
def engine_with_mock_model() -> YOLOInferenceEngine:
    """Return a YOLOInferenceEngine with ultralytics.YOLO patched to a MagicMock.

    The mock model's names is set to {0: "person", 1: "bicycle", 2: "car"}.
    Its __call__ returns empty YOLO results by default; individual tests may
    reconfigure engine._model.return_value as needed.
    """
    mock_yolo = MagicMock()
    mock_yolo.names = _DEFAULT_NAMES.copy()
    mock_yolo.return_value = _yolo_results([])

    with patch("model_lens.inference_engine.YOLO", return_value=mock_yolo):
        engine = YOLOInferenceEngine(model="yolov8n.pt", confidence_threshold=0.5)

    return engine


# ---------------------------------------------------------------------------
# YOLO result helpers
# ---------------------------------------------------------------------------


class _FakeTensor:
    """Minimal tensor-like object supporting .item() and .tolist()."""

    def __init__(self, val):
        self._val = val

    def item(self):
        return self._val

    def tolist(self):
        return self._val


class _FakeBoxes:
    """Mimics ultralytics Boxes, indexable via .cls, .conf, .xyxy."""

    def __init__(self, detections: list[dict]) -> None:
        self.cls = [_FakeTensor(d["index"]) for d in detections]
        self.conf = [_FakeTensor(d["confidence"]) for d in detections]
        self.xyxy = [_FakeTensor(d["box"]) for d in detections]

    def __len__(self) -> int:
        return len(self.cls)


class _FakeResults:
    """Mimics a single ultralytics Results object."""

    def __init__(self, detections: list[dict]) -> None:
        self.boxes = _FakeBoxes(detections)


def _yolo_results(detections: list[dict]) -> list[_FakeResults]:
    """Wrap a list of detection dicts in a YOLO-like results list."""
    return [_FakeResults(detections)]


def _det(
    index: int,
    confidence: float,
    box: list[float] | None = None,
) -> dict:
    """Shorthand for building a detection dict."""
    return {"index": index, "confidence": confidence, "box": box or [0.0, 0.0, 1.0, 1.0]}
