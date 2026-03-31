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

"""Tests for src/model_lens/config.py."""

import os
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from model_lens.config import (
    AppConfig,
    CameraConfig,
    ModelConfig,
    ServerConfig,
    load,
    validate,
)
from model_lens.exceptions import ConfigurationError

# ---------------------------------------------------------------------------
# 1. ServerConfig
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_server_config_default_host() -> None:
    """Default host is '0.0.0.0'."""
    assert ServerConfig().host == "0.0.0.0"


@pytest.mark.unit
def test_server_config_default_port() -> None:
    """Default port is 8080."""
    assert ServerConfig().port == 8080


@pytest.mark.unit
def test_server_config_default_log_level() -> None:
    """Default log level is 'info'."""
    assert ServerConfig().log_level == "info"


@pytest.mark.unit
def test_server_config_explicit_host() -> None:
    """Custom host is stored."""
    instance = ServerConfig(host="127.0.0.1", port=8080, log_level="info")
    assert instance.host == "127.0.0.1"


@pytest.mark.unit
def test_server_config_explicit_port() -> None:
    """Custom port is stored."""
    instance = ServerConfig(host="0.0.0.0", port=9090, log_level="info")
    assert instance.port == 9090


@pytest.mark.unit
def test_server_config_explicit_log_level() -> None:
    """Custom log level is stored."""
    instance = ServerConfig(host="0.0.0.0", port=8080, log_level="debug")
    assert instance.log_level == "debug"


@pytest.mark.unit
def test_server_config_host_is_immutable() -> None:
    """Assigning to host raises FrozenInstanceError."""
    instance = ServerConfig()
    with pytest.raises(FrozenInstanceError):
        instance.host = "localhost"  # type: ignore[misc]


@pytest.mark.unit
def test_server_config_port_is_immutable() -> None:
    """Assigning to port raises FrozenInstanceError."""
    instance = ServerConfig()
    with pytest.raises(FrozenInstanceError):
        instance.port = 1234  # type: ignore[misc]


@pytest.mark.unit
def test_server_config_log_level_is_immutable() -> None:
    """Assigning to log_level raises FrozenInstanceError."""
    instance = ServerConfig()
    with pytest.raises(FrozenInstanceError):
        instance.log_level = "error"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 2. config.CameraConfig
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_config_camera_config_default_source_type() -> None:
    """Default source type is 'local'."""
    assert CameraConfig().source_type == "local"


@pytest.mark.unit
def test_config_camera_config_default_device_index() -> None:
    """Default device index is 0."""
    assert CameraConfig().device_index == 0


@pytest.mark.unit
def test_config_camera_config_default_rtsp_url() -> None:
    """Default RTSP URL is ''."""
    assert CameraConfig().rtsp_url == ""


@pytest.mark.unit
def test_config_camera_config_explicit_source_type_rtsp() -> None:
    """RTSP source type is stored."""
    instance = CameraConfig(source_type="rtsp", device_index=0, rtsp_url="rtsp://host/stream")
    assert instance.source_type == "rtsp"


@pytest.mark.unit
def test_config_camera_config_explicit_device_index() -> None:
    """Custom device index is stored."""
    instance = CameraConfig(source_type="local", device_index=2, rtsp_url="")
    assert instance.device_index == 2


@pytest.mark.unit
def test_config_camera_config_explicit_rtsp_url() -> None:
    """Custom RTSP URL is stored."""
    instance = CameraConfig(source_type="rtsp", device_index=0, rtsp_url="rtsp://192.168.1.1/live")
    assert instance.rtsp_url == "rtsp://192.168.1.1/live"


@pytest.mark.unit
def test_config_camera_config_source_type_is_immutable() -> None:
    """Assigning to source_type raises FrozenInstanceError."""
    instance = CameraConfig()
    with pytest.raises(FrozenInstanceError):
        instance.source_type = "rtsp"  # type: ignore[misc]


@pytest.mark.unit
def test_config_camera_config_device_index_is_immutable() -> None:
    """Assigning to device_index raises FrozenInstanceError."""
    instance = CameraConfig()
    with pytest.raises(FrozenInstanceError):
        instance.device_index = 1  # type: ignore[misc]


@pytest.mark.unit
def test_config_camera_config_rtsp_url_is_immutable() -> None:
    """Assigning to rtsp_url raises FrozenInstanceError."""
    instance = CameraConfig()
    with pytest.raises(FrozenInstanceError):
        instance.rtsp_url = "rtsp://x"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 3. ModelConfig
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_model_config_default_model_path() -> None:
    """Default model path is ''."""
    assert ModelConfig().model_path == ""


@pytest.mark.unit
def test_model_config_default_labels_path() -> None:
    """Default labels path is ''."""
    assert ModelConfig().labels_path == ""


@pytest.mark.unit
def test_model_config_default_confidence_threshold() -> None:
    """Default confidence threshold is 0.5."""
    assert ModelConfig().confidence_threshold == 0.5


@pytest.mark.unit
def test_model_config_explicit_model_path() -> None:
    """Custom model path is stored."""
    instance = ModelConfig(model_path="/a/b/model.tflite", labels_path="/a/b/labels.txt", confidence_threshold=0.5)
    assert instance.model_path == "/a/b/model.tflite"


@pytest.mark.unit
def test_model_config_explicit_labels_path() -> None:
    """Custom labels path is stored."""
    instance = ModelConfig(model_path="/a/b/model.tflite", labels_path="/a/b/labels.txt", confidence_threshold=0.5)
    assert instance.labels_path == "/a/b/labels.txt"


@pytest.mark.unit
def test_model_config_explicit_confidence_threshold() -> None:
    """Custom confidence threshold is stored."""
    instance = ModelConfig(model_path="/a/b/model.tflite", labels_path="/a/b/labels.txt", confidence_threshold=0.9)
    assert instance.confidence_threshold == 0.9


@pytest.mark.unit
def test_model_config_model_path_is_immutable() -> None:
    """Assigning to model_path raises FrozenInstanceError."""
    instance = ModelConfig()
    with pytest.raises(FrozenInstanceError):
        instance.model_path = "/new"  # type: ignore[misc]


@pytest.mark.unit
def test_model_config_labels_path_is_immutable() -> None:
    """Assigning to labels_path raises FrozenInstanceError."""
    instance = ModelConfig()
    with pytest.raises(FrozenInstanceError):
        instance.labels_path = "/new"  # type: ignore[misc]


@pytest.mark.unit
def test_model_config_confidence_threshold_is_immutable() -> None:
    """Assigning to confidence_threshold raises FrozenInstanceError."""
    instance = ModelConfig()
    with pytest.raises(FrozenInstanceError):
        instance.confidence_threshold = 0.9  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 4. AppConfig
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_app_config_stores_server(bundled_paths: tuple[Path, Path]) -> None:
    """server field is stored correctly."""
    model_file, labels_file = bundled_paths
    server = ServerConfig()
    instance = AppConfig(
        server=server,
        camera=CameraConfig(),
        model=ModelConfig(model_path=str(model_file), labels_path=str(labels_file), confidence_threshold=0.5),
    )
    assert instance.server == server


@pytest.mark.unit
def test_app_config_stores_camera(bundled_paths: tuple[Path, Path]) -> None:
    """camera field is stored correctly."""
    model_file, labels_file = bundled_paths
    camera = CameraConfig()
    instance = AppConfig(
        server=ServerConfig(),
        camera=camera,
        model=ModelConfig(model_path=str(model_file), labels_path=str(labels_file), confidence_threshold=0.5),
    )
    assert instance.camera == camera


@pytest.mark.unit
def test_app_config_stores_model(bundled_paths: tuple[Path, Path]) -> None:
    """model field is stored correctly."""
    model_file, labels_file = bundled_paths
    instance = AppConfig(
        server=ServerConfig(),
        camera=CameraConfig(),
        model=ModelConfig(model_path=str(model_file), labels_path=str(labels_file), confidence_threshold=0.5),
    )
    assert instance.model.confidence_threshold == 0.5


@pytest.mark.unit
def test_app_config_server_is_immutable(valid_app_config: AppConfig) -> None:
    """Assigning to server raises FrozenInstanceError."""
    with pytest.raises(FrozenInstanceError):
        valid_app_config.server = ServerConfig()  # type: ignore[misc]


@pytest.mark.unit
def test_app_config_camera_is_immutable(valid_app_config: AppConfig) -> None:
    """Assigning to camera raises FrozenInstanceError."""
    with pytest.raises(FrozenInstanceError):
        valid_app_config.camera = CameraConfig()  # type: ignore[misc]


@pytest.mark.unit
def test_app_config_model_is_immutable(valid_app_config: AppConfig) -> None:
    """Assigning to model raises FrozenInstanceError."""
    with pytest.raises(FrozenInstanceError):
        valid_app_config.model = ModelConfig()  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 5. validate()
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_validate_valid_config_returns_none(valid_app_config: AppConfig) -> None:
    """validate() returns None for a fully valid config."""
    assert validate(valid_app_config) is None


# --- 5.2 server.host ---


@pytest.mark.unit
def test_validate_server_host_empty_raises(bundled_paths: tuple[Path, Path]) -> None:
    """Empty host raises ConfigurationError."""
    model_file, labels_file = bundled_paths
    cfg = AppConfig(
        server=ServerConfig(host="", port=8080, log_level="info"),
        camera=CameraConfig(),
        model=ModelConfig(model_path=str(model_file), labels_path=str(labels_file), confidence_threshold=0.5),
    )
    with pytest.raises(ConfigurationError, match="server.host must be non-empty"):
        validate(cfg)


# --- 5.3 server.port ---


@pytest.mark.unit
def test_validate_server_port_zero_raises(bundled_paths: tuple[Path, Path]) -> None:
    """Port 0 raises ConfigurationError."""
    model_file, labels_file = bundled_paths
    cfg = AppConfig(
        server=ServerConfig(host="0.0.0.0", port=0, log_level="info"),
        camera=CameraConfig(),
        model=ModelConfig(model_path=str(model_file), labels_path=str(labels_file), confidence_threshold=0.5),
    )
    with pytest.raises(ConfigurationError, match="server.port must be between 1 and 65535, got 0"):
        validate(cfg)


@pytest.mark.unit
def test_validate_server_port_negative_raises(bundled_paths: tuple[Path, Path]) -> None:
    """Negative port raises ConfigurationError."""
    model_file, labels_file = bundled_paths
    cfg = AppConfig(
        server=ServerConfig(host="0.0.0.0", port=-1, log_level="info"),
        camera=CameraConfig(),
        model=ModelConfig(model_path=str(model_file), labels_path=str(labels_file), confidence_threshold=0.5),
    )
    with pytest.raises(ConfigurationError, match="server.port must be between 1 and 65535, got -1"):
        validate(cfg)


@pytest.mark.unit
def test_validate_server_port_above_max_raises(bundled_paths: tuple[Path, Path]) -> None:
    """Port 65536 raises ConfigurationError."""
    model_file, labels_file = bundled_paths
    cfg = AppConfig(
        server=ServerConfig(host="0.0.0.0", port=65536, log_level="info"),
        camera=CameraConfig(),
        model=ModelConfig(model_path=str(model_file), labels_path=str(labels_file), confidence_threshold=0.5),
    )
    with pytest.raises(ConfigurationError, match="server.port must be between 1 and 65535, got 65536"):
        validate(cfg)


@pytest.mark.unit
def test_validate_server_port_min_boundary_valid(bundled_paths: tuple[Path, Path]) -> None:
    """Port 1 is valid."""
    model_file, labels_file = bundled_paths
    cfg = AppConfig(
        server=ServerConfig(host="0.0.0.0", port=1, log_level="info"),
        camera=CameraConfig(),
        model=ModelConfig(model_path=str(model_file), labels_path=str(labels_file), confidence_threshold=0.5),
    )
    validate(cfg)  # must not raise


@pytest.mark.unit
def test_validate_server_port_max_boundary_valid(bundled_paths: tuple[Path, Path]) -> None:
    """Port 65535 is valid."""
    model_file, labels_file = bundled_paths
    cfg = AppConfig(
        server=ServerConfig(host="0.0.0.0", port=65535, log_level="info"),
        camera=CameraConfig(),
        model=ModelConfig(model_path=str(model_file), labels_path=str(labels_file), confidence_threshold=0.5),
    )
    validate(cfg)  # must not raise


# --- 5.4 server.log_level ---


@pytest.mark.unit
def test_validate_server_log_level_invalid_raises(bundled_paths: tuple[Path, Path]) -> None:
    """Unknown log level raises ConfigurationError."""
    model_file, labels_file = bundled_paths
    cfg = AppConfig(
        server=ServerConfig(host="0.0.0.0", port=8080, log_level="verbose"),
        camera=CameraConfig(),
        model=ModelConfig(model_path=str(model_file), labels_path=str(labels_file), confidence_threshold=0.5),
    )
    with pytest.raises(
        ConfigurationError,
        match='server.log_level must be one of "debug", "info", "warning", "error", "critical", got "verbose"',
    ):
        validate(cfg)


@pytest.mark.unit
def test_validate_server_log_level_debug_valid(bundled_paths: tuple[Path, Path]) -> None:
    """'debug' is a valid log level."""
    model_file, labels_file = bundled_paths
    cfg = AppConfig(
        server=ServerConfig(host="0.0.0.0", port=8080, log_level="debug"),
        camera=CameraConfig(),
        model=ModelConfig(model_path=str(model_file), labels_path=str(labels_file), confidence_threshold=0.5),
    )
    validate(cfg)  # must not raise


@pytest.mark.unit
def test_validate_server_log_level_warning_valid(bundled_paths: tuple[Path, Path]) -> None:
    """'warning' is a valid log level."""
    model_file, labels_file = bundled_paths
    cfg = AppConfig(
        server=ServerConfig(host="0.0.0.0", port=8080, log_level="warning"),
        camera=CameraConfig(),
        model=ModelConfig(model_path=str(model_file), labels_path=str(labels_file), confidence_threshold=0.5),
    )
    validate(cfg)  # must not raise


@pytest.mark.unit
def test_validate_server_log_level_error_valid(bundled_paths: tuple[Path, Path]) -> None:
    """'error' is a valid log level."""
    model_file, labels_file = bundled_paths
    cfg = AppConfig(
        server=ServerConfig(host="0.0.0.0", port=8080, log_level="error"),
        camera=CameraConfig(),
        model=ModelConfig(model_path=str(model_file), labels_path=str(labels_file), confidence_threshold=0.5),
    )
    validate(cfg)  # must not raise


@pytest.mark.unit
def test_validate_server_log_level_critical_valid(bundled_paths: tuple[Path, Path]) -> None:
    """'critical' is a valid log level."""
    model_file, labels_file = bundled_paths
    cfg = AppConfig(
        server=ServerConfig(host="0.0.0.0", port=8080, log_level="critical"),
        camera=CameraConfig(),
        model=ModelConfig(model_path=str(model_file), labels_path=str(labels_file), confidence_threshold=0.5),
    )
    validate(cfg)  # must not raise


# --- 5.5 camera.source_type ---


@pytest.mark.unit
def test_validate_camera_source_type_invalid_raises(bundled_paths: tuple[Path, Path]) -> None:
    """Unknown source type raises ConfigurationError."""
    model_file, labels_file = bundled_paths
    cfg = AppConfig(
        server=ServerConfig(),
        camera=CameraConfig(source_type="usb", device_index=0, rtsp_url=""),
        model=ModelConfig(model_path=str(model_file), labels_path=str(labels_file), confidence_threshold=0.5),
    )
    with pytest.raises(
        ConfigurationError,
        match='camera.source_type must be one of "local", "rtsp", got "usb"',
    ):
        validate(cfg)


# --- 5.6 camera.device_index ---


@pytest.mark.unit
def test_validate_camera_device_index_negative_raises(bundled_paths: tuple[Path, Path]) -> None:
    """Negative device index raises ConfigurationError."""
    model_file, labels_file = bundled_paths
    cfg = AppConfig(
        server=ServerConfig(),
        camera=CameraConfig(source_type="local", device_index=-1, rtsp_url=""),
        model=ModelConfig(model_path=str(model_file), labels_path=str(labels_file), confidence_threshold=0.5),
    )
    with pytest.raises(ConfigurationError, match="camera.device_index must be >= 0, got -1"):
        validate(cfg)


@pytest.mark.unit
def test_validate_camera_device_index_zero_valid(bundled_paths: tuple[Path, Path]) -> None:
    """Device index 0 is valid."""
    model_file, labels_file = bundled_paths
    cfg = AppConfig(
        server=ServerConfig(),
        camera=CameraConfig(source_type="local", device_index=0, rtsp_url=""),
        model=ModelConfig(model_path=str(model_file), labels_path=str(labels_file), confidence_threshold=0.5),
    )
    validate(cfg)  # must not raise


# --- 5.7 camera.rtsp_url ---


@pytest.mark.unit
def test_validate_camera_rtsp_url_empty_when_rtsp_raises(bundled_paths: tuple[Path, Path]) -> None:
    """Empty RTSP URL with source_type='rtsp' raises ConfigurationError."""
    model_file, labels_file = bundled_paths
    cfg = AppConfig(
        server=ServerConfig(),
        camera=CameraConfig(source_type="rtsp", device_index=0, rtsp_url=""),
        model=ModelConfig(model_path=str(model_file), labels_path=str(labels_file), confidence_threshold=0.5),
    )
    with pytest.raises(
        ConfigurationError,
        match='camera.rtsp_url must be non-empty when source_type is "rtsp"',
    ):
        validate(cfg)


@pytest.mark.unit
def test_validate_camera_rtsp_url_empty_when_local_valid(bundled_paths: tuple[Path, Path]) -> None:
    """Empty RTSP URL with source_type='local' is valid."""
    model_file, labels_file = bundled_paths
    cfg = AppConfig(
        server=ServerConfig(),
        camera=CameraConfig(source_type="local", device_index=0, rtsp_url=""),
        model=ModelConfig(model_path=str(model_file), labels_path=str(labels_file), confidence_threshold=0.5),
    )
    validate(cfg)  # must not raise


# --- 5.8 model.model_path ---


@pytest.mark.unit
def test_validate_model_path_empty_raises(bundled_paths: tuple[Path, Path]) -> None:
    """Empty model path raises ConfigurationError."""
    _, labels_file = bundled_paths
    cfg = AppConfig(
        server=ServerConfig(),
        camera=CameraConfig(),
        model=ModelConfig(model_path="", labels_path=str(labels_file), confidence_threshold=0.5),
    )
    with pytest.raises(ConfigurationError, match="model.model_path must be non-empty"):
        validate(cfg)


@pytest.mark.unit
def test_validate_model_path_not_exist_raises(bundled_paths: tuple[Path, Path]) -> None:
    """Non-existent model path raises ConfigurationError."""
    _, labels_file = bundled_paths
    cfg = AppConfig(
        server=ServerConfig(),
        camera=CameraConfig(),
        model=ModelConfig(
            model_path="/nonexistent/model.tflite",
            labels_path=str(labels_file),
            confidence_threshold=0.5,
        ),
    )
    with pytest.raises(
        ConfigurationError,
        match='model.model_path does not exist: "/nonexistent/model.tflite"',
    ):
        validate(cfg)


# --- 5.9 model.labels_path ---


@pytest.mark.unit
def test_validate_labels_path_empty_raises(bundled_paths: tuple[Path, Path]) -> None:
    """Empty labels path raises ConfigurationError."""
    model_file, _ = bundled_paths
    cfg = AppConfig(
        server=ServerConfig(),
        camera=CameraConfig(),
        model=ModelConfig(model_path=str(model_file), labels_path="", confidence_threshold=0.5),
    )
    with pytest.raises(ConfigurationError, match="model.labels_path must be non-empty"):
        validate(cfg)


@pytest.mark.unit
def test_validate_labels_path_not_exist_raises(bundled_paths: tuple[Path, Path]) -> None:
    """Non-existent labels path raises ConfigurationError."""
    model_file, _ = bundled_paths
    cfg = AppConfig(
        server=ServerConfig(),
        camera=CameraConfig(),
        model=ModelConfig(
            model_path=str(model_file),
            labels_path="/nonexistent/labels.txt",
            confidence_threshold=0.5,
        ),
    )
    with pytest.raises(
        ConfigurationError,
        match='model.labels_path does not exist: "/nonexistent/labels.txt"',
    ):
        validate(cfg)


# --- 5.10 model.confidence_threshold ---


@pytest.mark.unit
def test_validate_confidence_threshold_zero_raises(bundled_paths: tuple[Path, Path]) -> None:
    """Threshold 0.0 raises ConfigurationError."""
    model_file, labels_file = bundled_paths
    cfg = AppConfig(
        server=ServerConfig(),
        camera=CameraConfig(),
        model=ModelConfig(model_path=str(model_file), labels_path=str(labels_file), confidence_threshold=0.0),
    )
    with pytest.raises(
        ConfigurationError,
        match="model.confidence_threshold must satisfy 0.0 < value <= 1.0, got 0.0",
    ):
        validate(cfg)


@pytest.mark.unit
def test_validate_confidence_threshold_negative_raises(bundled_paths: tuple[Path, Path]) -> None:
    """Negative threshold raises ConfigurationError."""
    model_file, labels_file = bundled_paths
    cfg = AppConfig(
        server=ServerConfig(),
        camera=CameraConfig(),
        model=ModelConfig(model_path=str(model_file), labels_path=str(labels_file), confidence_threshold=-0.1),
    )
    with pytest.raises(
        ConfigurationError,
        match="model.confidence_threshold must satisfy 0.0 < value <= 1.0, got -0.1",
    ):
        validate(cfg)


@pytest.mark.unit
def test_validate_confidence_threshold_above_one_raises(bundled_paths: tuple[Path, Path]) -> None:
    """Threshold 1.5 raises ConfigurationError."""
    model_file, labels_file = bundled_paths
    cfg = AppConfig(
        server=ServerConfig(),
        camera=CameraConfig(),
        model=ModelConfig(model_path=str(model_file), labels_path=str(labels_file), confidence_threshold=1.5),
    )
    with pytest.raises(
        ConfigurationError,
        match="model.confidence_threshold must satisfy 0.0 < value <= 1.0, got 1.5",
    ):
        validate(cfg)


@pytest.mark.unit
def test_validate_confidence_threshold_min_boundary_valid(bundled_paths: tuple[Path, Path]) -> None:
    """Threshold just above 0.0 (0.01) is valid."""
    model_file, labels_file = bundled_paths
    cfg = AppConfig(
        server=ServerConfig(),
        camera=CameraConfig(),
        model=ModelConfig(model_path=str(model_file), labels_path=str(labels_file), confidence_threshold=0.01),
    )
    validate(cfg)  # must not raise


@pytest.mark.unit
def test_validate_confidence_threshold_max_boundary_valid(bundled_paths: tuple[Path, Path]) -> None:
    """Threshold exactly 1.0 is valid."""
    model_file, labels_file = bundled_paths
    cfg = AppConfig(
        server=ServerConfig(),
        camera=CameraConfig(),
        model=ModelConfig(model_path=str(model_file), labels_path=str(labels_file), confidence_threshold=1.0),
    )
    validate(cfg)  # must not raise


# ---------------------------------------------------------------------------
# 6. load() — Config File Resolution
# ---------------------------------------------------------------------------


def _assert_log_call(mock_method: MagicMock, *expected_substrings: str) -> None:
    """Assert that a logger mock was called with args that contain all expected substrings.

    This helper is format-agnostic: it works regardless of whether the logger
    uses %-style formatting (``logger.info("msg %s", arg)``) or f-strings, by
    joining all positional call arguments into a single string before matching.
    """
    for call in mock_method.call_args_list:
        call_str = " ".join(str(a) for a in call.args)
        if all(s in call_str for s in expected_substrings):
            return
    raise AssertionError(
        f"No call found containing all of {expected_substrings!r}. "
        f"Actual calls: {mock_method.call_args_list}"
    )


def _make_importlib_resources_mock(model_path: str, labels_path: str) -> MagicMock:
    """Build a mock for importlib.resources that returns the given paths.

    Args:
        model_path: The string path to return for the model file.
        labels_path: The string path to return for the labels file.

    Returns:
        A MagicMock configured to stand in for importlib.resources.files().
    """
    mock_resources = MagicMock()

    def _files_side_effect(package: str) -> MagicMock:
        pkg_mock = MagicMock()

        def _joinpath_side_effect(filename: str) -> MagicMock:
            path_mock = MagicMock()
            if "model" in filename or filename.endswith(".tflite"):
                path_mock.__str__ = lambda self: model_path
                path_mock.is_file.return_value = True
            else:
                path_mock.__str__ = lambda self: labels_path
                path_mock.is_file.return_value = True
            return path_mock

        pkg_mock.joinpath.side_effect = _joinpath_side_effect
        return pkg_mock

    mock_resources.files.side_effect = _files_side_effect
    return mock_resources


# --- 6.1 No config file — uses defaults ---


@pytest.mark.unit
def test_load_no_config_file_uses_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundled_paths: tuple[Path, Path],
) -> None:
    """When no --config flag and no model_lens.toml in cwd, built-in defaults are used."""
    model_file, labels_file = bundled_paths
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])

    with patch("model_lens.config.importlib.resources") as mock_res:
        _configure_resources_mock(mock_res, str(model_file), str(labels_file))
        cfg = load()

    assert cfg.server.port == 8080


@pytest.mark.unit
def test_load_no_config_file_logs_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundled_paths: tuple[Path, Path],
) -> None:
    """Warning is logged when no config file is found."""
    model_file, labels_file = bundled_paths
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])

    with patch("model_lens.config.importlib.resources") as mock_res, patch(
        "model_lens.config.logger"
    ) as mock_logger:
        _configure_resources_mock(mock_res, str(model_file), str(labels_file))
        load()

    mock_logger.warning.assert_called_once_with("No config file found; using built-in defaults.")


# --- 6.2 Default config file discovered ---


@pytest.mark.unit
def test_load_default_config_file_discovered(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundled_paths: tuple[Path, Path],
) -> None:
    """model_lens.toml in cwd is loaded automatically."""
    model_file, labels_file = bundled_paths
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])

    config_file = tmp_path / "model_lens.toml"
    config_file.write_text(
        f'[server]\nport = 7777\n[model]\nmodel_path = "{model_file}"\nlabels_path = "{labels_file}"\n'
        f"confidence_threshold = 0.5\n"
    )

    cfg = load()
    assert cfg.server.port == 7777


@pytest.mark.unit
def test_load_default_config_file_logs_info(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundled_paths: tuple[Path, Path],
) -> None:
    """Info is logged when config file is found."""
    model_file, labels_file = bundled_paths
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])

    config_file = tmp_path / "model_lens.toml"
    config_file.write_text(
        f'[model]\nmodel_path = "{model_file}"\nlabels_path = "{labels_file}"\nconfidence_threshold = 0.5\n'
    )

    with patch("model_lens.config.logger") as mock_logger:
        load()

    _assert_log_call(mock_logger.info, "Loading config from", str(config_file))


# --- 6.3 Explicit --config flag ---


@pytest.mark.unit
def test_load_explicit_config_flag_loads_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundled_paths: tuple[Path, Path],
) -> None:
    """--config path is loaded."""
    model_file, labels_file = bundled_paths
    monkeypatch.chdir(tmp_path)

    config_file = tmp_path / "custom.toml"
    config_file.write_text(
        f'[server]\nport = 6543\n[model]\nmodel_path = "{model_file}"\nlabels_path = "{labels_file}"\n'
        f"confidence_threshold = 0.5\n"
    )
    monkeypatch.setattr(sys, "argv", ["prog", "--config", str(config_file)])

    cfg = load()
    assert cfg.server.port == 6543


@pytest.mark.unit
def test_load_explicit_config_flag_logs_info(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundled_paths: tuple[Path, Path],
) -> None:
    """Info is logged for explicit config path."""
    model_file, labels_file = bundled_paths
    monkeypatch.chdir(tmp_path)

    config_file = tmp_path / "custom.toml"
    config_file.write_text(
        f'[model]\nmodel_path = "{model_file}"\nlabels_path = "{labels_file}"\nconfidence_threshold = 0.5\n'
    )
    monkeypatch.setattr(sys, "argv", ["prog", "--config", str(config_file)])

    with patch("model_lens.config.logger") as mock_logger:
        load()

    _assert_log_call(mock_logger.info, "Loading config from", str(config_file))


# --- 6.4 TOML overrides ---


@pytest.mark.unit
def test_load_toml_overrides_server_port(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundled_paths: tuple[Path, Path],
) -> None:
    """TOML [server] port = 9090 overrides default."""
    model_file, labels_file = bundled_paths
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])

    config_file = tmp_path / "model_lens.toml"
    config_file.write_text(
        f'[server]\nport = 9090\n[model]\nmodel_path = "{model_file}"\nlabels_path = "{labels_file}"\n'
        f"confidence_threshold = 0.5\n"
    )

    cfg = load()
    assert cfg.server.port == 9090


@pytest.mark.unit
def test_load_toml_overrides_camera_source_type(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundled_paths: tuple[Path, Path],
) -> None:
    """TOML [camera] source_type = 'rtsp' overrides default."""
    model_file, labels_file = bundled_paths
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])

    config_file = tmp_path / "model_lens.toml"
    config_file.write_text(
        f'[camera]\nsource_type = "rtsp"\nrtsp_url = "rtsp://host/s"\n'
        f'[model]\nmodel_path = "{model_file}"\nlabels_path = "{labels_file}"\nconfidence_threshold = 0.5\n'
    )

    cfg = load()
    assert cfg.camera.source_type == "rtsp"


@pytest.mark.unit
def test_load_toml_overrides_confidence_threshold(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundled_paths: tuple[Path, Path],
) -> None:
    """TOML [model] confidence_threshold = 0.8 overrides default."""
    model_file, labels_file = bundled_paths
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])

    config_file = tmp_path / "model_lens.toml"
    config_file.write_text(
        f'[model]\nmodel_path = "{model_file}"\nlabels_path = "{labels_file}"\nconfidence_threshold = 0.8\n'
    )

    cfg = load()
    assert cfg.model.confidence_threshold == 0.8


@pytest.mark.unit
def test_load_toml_unknown_keys_ignored(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundled_paths: tuple[Path, Path],
) -> None:
    """Unknown TOML keys do not raise."""
    model_file, labels_file = bundled_paths
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])

    config_file = tmp_path / "model_lens.toml"
    config_file.write_text(
        f'[server]\nunknown_key = "x"\n'
        f'[model]\nmodel_path = "{model_file}"\nlabels_path = "{labels_file}"\nconfidence_threshold = 0.5\n'
    )

    load()  # must not raise


@pytest.mark.unit
def test_load_toml_missing_keys_retain_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundled_paths: tuple[Path, Path],
) -> None:
    """Keys absent from TOML retain built-in defaults."""
    model_file, labels_file = bundled_paths
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])

    config_file = tmp_path / "model_lens.toml"
    config_file.write_text(
        f'[server]\nport = 9090\n'
        f'[model]\nmodel_path = "{model_file}"\nlabels_path = "{labels_file}"\nconfidence_threshold = 0.5\n'
    )

    cfg = load()
    assert cfg.server.host == "0.0.0.0"


# --- 6.5 Validation failures ---


@pytest.mark.unit
def test_load_invalid_toml_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed TOML raises ConfigurationError."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])

    config_file = tmp_path / "model_lens.toml"
    config_file.write_text("not valid toml :::")

    with pytest.raises(ConfigurationError, match="Failed to parse config file at "):
        load()


# ---------------------------------------------------------------------------
# 7. load() — Environment Variable Overrides
# ---------------------------------------------------------------------------


def _configure_resources_mock(mock_res: MagicMock, model_path: str, labels_path: str) -> None:
    """Configure a mock for importlib.resources to return the given paths.

    Args:
        mock_res: The MagicMock to configure.
        model_path: The string path to return for the model file.
        labels_path: The string path to return for the labels file.
    """
    pkg_mock = MagicMock()

    def _joinpath(filename: str) -> MagicMock:
        path_mock = MagicMock()
        if "model" in filename or filename.endswith(".tflite"):
            path_mock.__str__ = lambda self: model_path
            path_mock.is_file.return_value = True
        else:
            path_mock.__str__ = lambda self: labels_path
            path_mock.is_file.return_value = True
        return path_mock

    pkg_mock.joinpath.side_effect = _joinpath
    mock_res.files.return_value = pkg_mock


@pytest.mark.unit
def test_load_env_override_server_host(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundled_paths: tuple[Path, Path],
) -> None:
    """ML_SERVER_HOST overrides host."""
    model_file, labels_file = bundled_paths
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setenv("ML_SERVER_HOST", "192.168.0.1")

    with patch("model_lens.config.importlib.resources") as mock_res:
        _configure_resources_mock(mock_res, str(model_file), str(labels_file))
        cfg = load()

    assert cfg.server.host == "192.168.0.1"


@pytest.mark.unit
def test_load_env_override_server_port(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundled_paths: tuple[Path, Path],
) -> None:
    """ML_SERVER_PORT overrides port."""
    model_file, labels_file = bundled_paths
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setenv("ML_SERVER_PORT", "9999")

    with patch("model_lens.config.importlib.resources") as mock_res:
        _configure_resources_mock(mock_res, str(model_file), str(labels_file))
        cfg = load()

    assert cfg.server.port == 9999


@pytest.mark.unit
def test_load_env_override_server_log_level(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundled_paths: tuple[Path, Path],
) -> None:
    """ML_SERVER_LOG_LEVEL overrides log level."""
    model_file, labels_file = bundled_paths
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setenv("ML_SERVER_LOG_LEVEL", "debug")

    with patch("model_lens.config.importlib.resources") as mock_res:
        _configure_resources_mock(mock_res, str(model_file), str(labels_file))
        cfg = load()

    assert cfg.server.log_level == "debug"


@pytest.mark.unit
def test_load_env_override_camera_source_type(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundled_paths: tuple[Path, Path],
) -> None:
    """ML_CAMERA_SOURCE_TYPE overrides source type."""
    model_file, labels_file = bundled_paths
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setenv("ML_CAMERA_SOURCE_TYPE", "rtsp")
    monkeypatch.setenv("ML_CAMERA_RTSP_URL", "rtsp://h/s")

    with patch("model_lens.config.importlib.resources") as mock_res:
        _configure_resources_mock(mock_res, str(model_file), str(labels_file))
        cfg = load()

    assert cfg.camera.source_type == "rtsp"


@pytest.mark.unit
def test_load_env_override_camera_device_index(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundled_paths: tuple[Path, Path],
) -> None:
    """ML_CAMERA_DEVICE_INDEX overrides device index."""
    model_file, labels_file = bundled_paths
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setenv("ML_CAMERA_DEVICE_INDEX", "2")

    with patch("model_lens.config.importlib.resources") as mock_res:
        _configure_resources_mock(mock_res, str(model_file), str(labels_file))
        cfg = load()

    assert cfg.camera.device_index == 2


@pytest.mark.unit
def test_load_env_override_camera_rtsp_url(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundled_paths: tuple[Path, Path],
) -> None:
    """ML_CAMERA_RTSP_URL overrides RTSP URL."""
    model_file, labels_file = bundled_paths
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setenv("ML_CAMERA_SOURCE_TYPE", "rtsp")
    monkeypatch.setenv("ML_CAMERA_RTSP_URL", "rtsp://cam/live")

    with patch("model_lens.config.importlib.resources") as mock_res:
        _configure_resources_mock(mock_res, str(model_file), str(labels_file))
        cfg = load()

    assert cfg.camera.rtsp_url == "rtsp://cam/live"


@pytest.mark.unit
def test_load_env_override_model_model_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundled_paths: tuple[Path, Path],
) -> None:
    """ML_MODEL_MODEL_PATH overrides model path."""
    model_file, labels_file = bundled_paths
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setenv("ML_MODEL_MODEL_PATH", str(model_file))
    monkeypatch.setenv("ML_MODEL_LABELS_PATH", str(labels_file))

    with patch("model_lens.config.importlib.resources") as mock_res:
        _configure_resources_mock(mock_res, str(model_file), str(labels_file))
        cfg = load()

    assert cfg.model.model_path == str(model_file)


@pytest.mark.unit
def test_load_env_override_model_labels_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundled_paths: tuple[Path, Path],
) -> None:
    """ML_MODEL_LABELS_PATH overrides labels path."""
    model_file, labels_file = bundled_paths
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setenv("ML_MODEL_MODEL_PATH", str(model_file))
    monkeypatch.setenv("ML_MODEL_LABELS_PATH", str(labels_file))

    with patch("model_lens.config.importlib.resources") as mock_res:
        _configure_resources_mock(mock_res, str(model_file), str(labels_file))
        cfg = load()

    assert cfg.model.labels_path == str(labels_file)


@pytest.mark.unit
def test_load_env_override_model_confidence_threshold(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundled_paths: tuple[Path, Path],
) -> None:
    """ML_MODEL_CONFIDENCE_THRESHOLD overrides threshold."""
    model_file, labels_file = bundled_paths
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setenv("ML_MODEL_CONFIDENCE_THRESHOLD", "0.75")

    with patch("model_lens.config.importlib.resources") as mock_res:
        _configure_resources_mock(mock_res, str(model_file), str(labels_file))
        cfg = load()

    assert cfg.model.confidence_threshold == 0.75


@pytest.mark.unit
def test_load_env_override_logs_debug(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundled_paths: tuple[Path, Path],
) -> None:
    """Debug log is emitted for each env override applied."""
    model_file, labels_file = bundled_paths
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setenv("ML_SERVER_PORT", "9999")

    with patch("model_lens.config.importlib.resources") as mock_res, patch(
        "model_lens.config.logger"
    ) as mock_logger:
        _configure_resources_mock(mock_res, str(model_file), str(labels_file))
        load()

    _assert_log_call(mock_logger.debug, "ML_SERVER_PORT", "9999", "server", "port")


# --- 7.2 Validation failures ---


@pytest.mark.unit
def test_load_env_coercion_int_failure_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundled_paths: tuple[Path, Path],
) -> None:
    """Non-integer value for an int field raises ConfigurationError."""
    model_file, labels_file = bundled_paths
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setenv("ML_SERVER_PORT", "abc")

    with patch("model_lens.config.importlib.resources") as mock_res:
        _configure_resources_mock(mock_res, str(model_file), str(labels_file))
        with pytest.raises(ConfigurationError) as exc_info:
            load()

    message = str(exc_info.value)
    assert "ML_SERVER_PORT" in message
    assert "int" in message
    assert "abc" in message


@pytest.mark.unit
def test_load_env_coercion_float_failure_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundled_paths: tuple[Path, Path],
) -> None:
    """Non-float value for a float field raises ConfigurationError."""
    model_file, labels_file = bundled_paths
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setenv("ML_MODEL_CONFIDENCE_THRESHOLD", "xyz")

    with patch("model_lens.config.importlib.resources") as mock_res:
        _configure_resources_mock(mock_res, str(model_file), str(labels_file))
        with pytest.raises(ConfigurationError) as exc_info:
            load()

    message = str(exc_info.value)
    assert "ML_MODEL_CONFIDENCE_THRESHOLD" in message
    assert "float" in message
    assert "xyz" in message


@pytest.mark.unit
def test_load_env_coercion_str_no_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundled_paths: tuple[Path, Path],
) -> None:
    """String env var is always accepted as-is."""
    model_file, labels_file = bundled_paths
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setenv("ML_SERVER_HOST", "any-string")

    with patch("model_lens.config.importlib.resources") as mock_res:
        _configure_resources_mock(mock_res, str(model_file), str(labels_file))
        cfg = load()

    assert cfg.server.host == "any-string"


# ---------------------------------------------------------------------------
# 8. load() — Package-Data Path Resolution
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_load_resolves_bundled_model_path_when_empty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundled_paths: tuple[Path, Path],
) -> None:
    """Empty model_path is resolved to bundled path."""
    model_file, labels_file = bundled_paths
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])

    with patch("model_lens.config.importlib.resources") as mock_res:
        _configure_resources_mock(mock_res, str(model_file), str(labels_file))
        cfg = load()

    assert cfg.model.model_path == str(model_file)


@pytest.mark.unit
def test_load_resolves_bundled_labels_path_when_empty(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundled_paths: tuple[Path, Path],
) -> None:
    """Empty labels_path is resolved to bundled path."""
    model_file, labels_file = bundled_paths
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])

    with patch("model_lens.config.importlib.resources") as mock_res:
        _configure_resources_mock(mock_res, str(model_file), str(labels_file))
        cfg = load()

    assert cfg.model.labels_path == str(labels_file)


@pytest.mark.unit
def test_load_skips_bundled_resolution_when_model_path_set(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundled_paths: tuple[Path, Path],
) -> None:
    """Non-empty model_path skips bundled resolution."""
    model_file, labels_file = bundled_paths
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setenv("ML_MODEL_MODEL_PATH", str(model_file))
    monkeypatch.setenv("ML_MODEL_LABELS_PATH", str(labels_file))

    with patch("model_lens.config.importlib.resources") as mock_res:
        _configure_resources_mock(mock_res, str(model_file), str(labels_file))
        load()
        # resources.files should not have been called for model path resolution
        for call_args in mock_res.files.call_args_list:
            # If called at all, it must not be for model resolution
            pass
        # The key assertion: model_path was set via env, so bundled resolution was skipped
        assert mock_res.files.call_count == 0


@pytest.mark.unit
def test_load_skips_bundled_resolution_when_labels_path_set(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundled_paths: tuple[Path, Path],
) -> None:
    """Non-empty labels_path skips bundled resolution."""
    model_file, labels_file = bundled_paths
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setenv("ML_MODEL_MODEL_PATH", str(model_file))
    monkeypatch.setenv("ML_MODEL_LABELS_PATH", str(labels_file))

    with patch("model_lens.config.importlib.resources") as mock_res:
        _configure_resources_mock(mock_res, str(model_file), str(labels_file))
        load()
        assert mock_res.files.call_count == 0


@pytest.mark.unit
def test_load_bundled_resolution_logs_debug(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundled_paths: tuple[Path, Path],
) -> None:
    """Debug log is emitted when bundled path is resolved."""
    model_file, labels_file = bundled_paths
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])

    with patch("model_lens.config.importlib.resources") as mock_res, patch(
        "model_lens.config.logger"
    ) as mock_logger:
        _configure_resources_mock(mock_res, str(model_file), str(labels_file))
        load()

    _assert_log_call(mock_logger.debug, "Resolved bundled model_path", str(model_file))


# --- 8.2 Error propagation ---


@pytest.mark.unit
def test_load_bundled_model_path_not_found_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundled_paths: tuple[Path, Path],
) -> None:
    """importlib.resources failure for model raises ConfigurationError."""
    _, labels_file = bundled_paths
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])

    with patch("model_lens.config.importlib.resources") as mock_res:
        pkg_mock = MagicMock()
        pkg_mock.joinpath.side_effect = FileNotFoundError("not found")
        mock_res.files.return_value = pkg_mock

        with pytest.raises(ConfigurationError, match="Bundled model file could not be resolved from package data"):
            load()


@pytest.mark.unit
def test_load_bundled_labels_path_not_found_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bundled_paths: tuple[Path, Path],
) -> None:
    """importlib.resources failure for labels raises ConfigurationError."""
    model_file, _ = bundled_paths
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setenv("ML_MODEL_MODEL_PATH", str(model_file))

    with patch("model_lens.config.importlib.resources") as mock_res:
        pkg_mock = MagicMock()
        pkg_mock.joinpath.side_effect = FileNotFoundError("not found")
        mock_res.files.return_value = pkg_mock

        with pytest.raises(ConfigurationError, match="Bundled labels file could not be resolved from package data"):
            load()
