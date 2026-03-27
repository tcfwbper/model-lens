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

"""Shared fixtures for TorchInferenceEngine tests."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from model_lens.inference_engine import TorchInferenceEngine


@pytest.fixture()
def label_map_file(tmp_path: Path) -> Path:
    """Write a standard three-label map file and return its path.

    Labels:
        0: person
        1: bicycle
        2: car
    """
    labels = tmp_path / "labels.txt"
    labels.write_text("person\nbicycle\ncar\n")
    return labels


@pytest.fixture()
def dummy_model_file(tmp_path: Path) -> Path:
    """Create a dummy (empty) model file and return its path."""
    model = tmp_path / "model.pt"
    model.write_bytes(b"")
    return model


@pytest.fixture()
def engine_with_mock_model(
    tmp_path: Path,
    label_map_file: Path,
    dummy_model_file: Path,
) -> TorchInferenceEngine:
    """Return a TorchInferenceEngine with torch.load patched to a MagicMock model.

    The mock model's __call__ returns an empty list by default; individual tests
    may reconfigure it as needed.
    """
    mock_model = MagicMock()
    mock_model.return_value = []

    with patch("model_lens.inference_engine.torch.load", return_value=mock_model):
        engine = TorchInferenceEngine(
            model_path=str(dummy_model_file),
            labels_path=str(label_map_file),
            confidence_threshold=0.5,
        )

    # Expose the mock so tests can reconfigure __call__
    engine._model = mock_model  # type: ignore[attr-defined]
    return engine
