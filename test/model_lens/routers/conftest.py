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

"""Shared fixtures for router tests."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from model_lens.entities import LocalCameraConfig, RuntimeConfig


@pytest.fixture
def mock_pipeline():
    pipeline = MagicMock()
    pipeline.get_config.return_value = RuntimeConfig(
        camera=LocalCameraConfig(device_index=0),
        target_labels=[],
        confidence_threshold=0.5,
    )
    return pipeline


@pytest.fixture
def client(mock_pipeline, tmp_path):
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
