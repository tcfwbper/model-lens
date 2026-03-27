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

"""Shared fixtures for test_app.py."""

from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from model_lens.entities import (
    DetectionResult,
    LocalCameraConfig,
    RuntimeConfig,
)


@pytest.fixture
def mock_pipeline() -> MagicMock:
    """A MagicMock standing in for a DetectionPipeline instance."""
    pipeline = MagicMock()
    pipeline.get_config.return_value = RuntimeConfig(
        camera=LocalCameraConfig(device_index=0),
        target_labels=[],
        confidence_threshold=0.5,
    )
    return pipeline


@pytest.fixture
def client(mock_pipeline: MagicMock, tmp_path: Path) -> Generator[TestClient, None, None]:
    """A TestClient wrapping the FastAPI app with mock_pipeline injected and lifespan bypassed."""
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    index_html = dist_dir / "index.html"
    index_html.write_bytes(b"<html><body>ModelLens</body></html>")
    static_dir = dist_dir / "static"
    static_dir.mkdir()

    with patch("model_lens.app.resolve_dist_dir", return_value=dist_dir):
        from model_lens.app import create_app

        app = create_app()

    app.state.pipeline = mock_pipeline

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture
def static_client(
    mock_pipeline: MagicMock, tmp_path: Path
) -> Generator[tuple[TestClient, bytes], None, None]:
    """A TestClient fixture with a known index.html and a static asset file."""
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    index_content = b"<html><body>ModelLens</body></html>"
    (dist_dir / "index.html").write_bytes(index_content)
    static_dir = dist_dir / "static"
    static_dir.mkdir()
    (static_dir / "app.js").write_bytes(b"console.log('hello');")

    with patch("model_lens.app.resolve_dist_dir", return_value=dist_dir):
        from model_lens.app import create_app

        app = create_app()

    app.state.pipeline = mock_pipeline

    with TestClient(app) as c:
        yield c, index_content


@pytest.fixture
def make_pipeline_result():
    """Factory fixture that creates PipelineResult-like MagicMock objects."""

    def _make(label: str = "cat", confidence: float = 0.9, is_target: bool = True) -> MagicMock:
        result = MagicMock()
        result.jpeg_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 16  # minimal fake JPEG bytes
        result.timestamp = 1748000400.123456
        result.source = "local:0"
        detection = DetectionResult(
            label=label,
            confidence=confidence,
            bounding_box=(0.1, 0.2, 0.4, 0.6),
            is_target=is_target,
        )
        result.detections = [detection]
        return result

    return _make


@pytest.fixture
def lifespan_mocks(tmp_path: Path) -> Generator[dict, None, None]:
    """Patches all external dependencies so the lifespan can run without real hardware or files."""
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_bytes(b"<html></html>")
    (dist_dir / "static").mkdir()

    mock_config = MagicMock()
    mock_config.model.model_path = "fake.pt"
    mock_config.model.confidence_threshold = 0.5
    mock_config.model.labels_path = "fake_labels.txt"
    mock_config.camera.source_type = "local"
    mock_config.camera.device_index = 0

    with (
        patch("model_lens.app.ConfigLoader") as mock_loader_cls,
        patch("model_lens.app.TorchInferenceEngine") as mock_engine_cls,
        patch("model_lens.app.DetectionPipeline") as mock_pipeline_cls,
        patch("model_lens.app.resolve_dist_dir", return_value=dist_dir),
    ):
        mock_loader_cls.return_value.load.return_value = mock_config
        mock_engine = MagicMock()
        mock_engine_cls.return_value = mock_engine
        mock_pipeline = MagicMock()
        mock_pipeline_cls.return_value = mock_pipeline

        yield {
            "loader_cls": mock_loader_cls,
            "engine_cls": mock_engine_cls,
            "engine": mock_engine,
            "pipeline_cls": mock_pipeline_cls,
            "pipeline": mock_pipeline,
            "config": mock_config,
        }


@pytest.fixture
def client_with_broken_pipeline(
    mock_pipeline: MagicMock, tmp_path: Path
) -> Generator[TestClient, None, None]:
    """A TestClient where mock_pipeline.get_config raises RuntimeError to simulate HTTP 500."""
    mock_pipeline.get_config.side_effect = RuntimeError("unexpected failure")

    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_bytes(b"<html></html>")
    (dist_dir / "static").mkdir()

    with patch("model_lens.app.resolve_dist_dir", return_value=dist_dir):
        from model_lens.app import create_app

        app = create_app()

    app.state.pipeline = mock_pipeline

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
