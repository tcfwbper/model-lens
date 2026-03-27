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

"""Shared pytest fixtures for config-layer tests."""

from pathlib import Path

import pytest

from model_lens.config import (
    AppConfig,
    CameraConfig,
    ModelConfig,
    ServerConfig,
)


@pytest.fixture()
def bundled_paths(tmp_path: Path) -> tuple[Path, Path]:
    """Create temporary files that stand in for bundled model and labels assets.

    Returns:
        A tuple of (model_path, labels_path) as Path objects, both existing on disk.
    """
    model_file = tmp_path / "model.tflite"
    labels_file = tmp_path / "labels.txt"
    model_file.write_bytes(b"")
    labels_file.write_text("person\ncar\n")
    return model_file, labels_file


@pytest.fixture()
def valid_app_config(bundled_paths: tuple[Path, Path]) -> AppConfig:
    """Return a fully valid AppConfig with real on-disk paths.

    Args:
        bundled_paths: Fixture providing existing model and labels files.

    Returns:
        A valid AppConfig instance.
    """
    model_file, labels_file = bundled_paths
    return AppConfig(
        server=ServerConfig(),
        camera=CameraConfig(),
        model=ModelConfig(
            model_path=str(model_file),
            labels_path=str(labels_file),
            confidence_threshold=0.5,
        ),
    )


@pytest.fixture()
def minimal_toml_content(bundled_paths: tuple[Path, Path]) -> str:
    """Return a minimal valid TOML string referencing real on-disk paths.

    Args:
        bundled_paths: Fixture providing existing model and labels files.

    Returns:
        A TOML string suitable for writing to a config file.
    """
    model_file, labels_file = bundled_paths
    return (
        f'[model]\n'
        f'model_path = "{model_file}"\n'
        f'labels_path = "{labels_file}"\n'
        f'confidence_threshold = 0.5\n'
    )
