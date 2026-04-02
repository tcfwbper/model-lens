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

import sys
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from model_lens.config import (
    AppConfig,
    CameraConfig,
    ConfigLoader,
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
def test_model_config_default_model() -> None:
    """Default model name is 'yolov8n'."""
    assert ModelConfig().model == "yolov8n"


@pytest.mark.unit
def test_model_config_default_confidence_threshold() -> None:
    """Default confidence threshold is 0.5."""
    assert ModelConfig().confidence_threshold == 0.5


@pytest.mark.unit
def test_model_config_explicit_model() -> None:
    """Custom model name is stored."""
    instance = ModelConfig(model="yolov8s", confidence_threshold=0.5)
    assert instance.model == "yolov8s"


@pytest.mark.unit
def test_model_config_explicit_confidence_threshold() -> None:
    """Custom confidence threshold is stored."""
    instance = ModelConfig(model="yolov8n", confidence_threshold=0.9)
    assert instance.confidence_threshold == 0.9


@pytest.mark.unit
def test_model_config_model_is_immutable() -> None:
    """Assigning to model raises FrozenInstanceError."""
    instance = ModelConfig()
    with pytest.raises(FrozenInstanceError):
        instance.model = "yolov8s"  # type: ignore[misc]


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
def test_app_config_stores_server() -> None:
    """server field is stored correctly."""
    server = ServerConfig()
    instance = AppConfig(
        server=server,
        camera=CameraConfig(),
        model=ModelConfig(model="yolov8n", confidence_threshold=0.5),
    )
    assert instance.server == server


@pytest.mark.unit
def test_app_config_stores_camera() -> None:
    """camera field is stored correctly."""
    camera = CameraConfig()
    instance = AppConfig(
        server=ServerConfig(),
        camera=camera,
        model=ModelConfig(model="yolov8n", confidence_threshold=0.5),
    )
    assert instance.camera == camera


@pytest.mark.unit
def test_app_config_stores_model() -> None:
    """model field is stored correctly."""
    instance = AppConfig(
        server=ServerConfig(),
        camera=CameraConfig(),
        model=ModelConfig(model="yolov8n", confidence_threshold=0.5),
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
def test_validate_server_host_empty_raises() -> None:
    """Empty host raises ConfigurationError."""
    cfg = AppConfig(
        server=ServerConfig(host="", port=8080, log_level="info"),
        camera=CameraConfig(),
        model=ModelConfig(model="yolov8n", confidence_threshold=0.5),
    )
    with pytest.raises(ConfigurationError, match="server.host must be non-empty"):
        validate(cfg)


# --- 5.3 server.port ---


@pytest.mark.unit
def test_validate_server_port_zero_raises() -> None:
    """Port 0 raises ConfigurationError."""
    cfg = AppConfig(
        server=ServerConfig(host="0.0.0.0", port=0, log_level="info"),
        camera=CameraConfig(),
        model=ModelConfig(model="yolov8n", confidence_threshold=0.5),
    )
    with pytest.raises(ConfigurationError, match="server.port must be between 1 and 65535, got 0"):
        validate(cfg)


@pytest.mark.unit
def test_validate_server_port_negative_raises() -> None:
    """Negative port raises ConfigurationError."""
    cfg = AppConfig(
        server=ServerConfig(host="0.0.0.0", port=-1, log_level="info"),
        camera=CameraConfig(),
        model=ModelConfig(model="yolov8n", confidence_threshold=0.5),
    )
    with pytest.raises(ConfigurationError, match="server.port must be between 1 and 65535, got -1"):
        validate(cfg)


@pytest.mark.unit
def test_validate_server_port_above_max_raises() -> None:
    """Port 65536 raises ConfigurationError."""
    cfg = AppConfig(
        server=ServerConfig(host="0.0.0.0", port=65536, log_level="info"),
        camera=CameraConfig(),
        model=ModelConfig(model="yolov8n", confidence_threshold=0.5),
    )
    with pytest.raises(ConfigurationError, match="server.port must be between 1 and 65535, got 65536"):
        validate(cfg)


@pytest.mark.unit
def test_validate_server_port_min_boundary_valid() -> None:
    """Port 1 is valid."""
    cfg = AppConfig(
        server=ServerConfig(host="0.0.0.0", port=1, log_level="info"),
        camera=CameraConfig(),
        model=ModelConfig(model="yolov8n", confidence_threshold=0.5),
    )
    validate(cfg)  # must not raise


@pytest.mark.unit
def test_validate_server_port_max_boundary_valid() -> None:
    """Port 65535 is valid."""
    cfg = AppConfig(
        server=ServerConfig(host="0.0.0.0", port=65535, log_level="info"),
        camera=CameraConfig(),
        model=ModelConfig(model="yolov8n", confidence_threshold=0.5),
    )
    validate(cfg)  # must not raise


# --- 5.4 server.log_level ---


@pytest.mark.unit
def test_validate_server_log_level_invalid_raises() -> None:
    """Unknown log level raises ConfigurationError."""
    cfg = AppConfig(
        server=ServerConfig(host="0.0.0.0", port=8080, log_level="verbose"),
        camera=CameraConfig(),
        model=ModelConfig(model="yolov8n", confidence_threshold=0.5),
    )
    with pytest.raises(
        ConfigurationError,
        match='server.log_level must be one of "debug", "info", "warning", "error", "critical", got "verbose"',
    ):
        validate(cfg)


@pytest.mark.unit
def test_validate_server_log_level_debug_valid() -> None:
    """'debug' is a valid log level."""
    cfg = AppConfig(
        server=ServerConfig(host="0.0.0.0", port=8080, log_level="debug"),
        camera=CameraConfig(),
        model=ModelConfig(model="yolov8n", confidence_threshold=0.5),
    )
    validate(cfg)  # must not raise


@pytest.mark.unit
def test_validate_server_log_level_warning_valid() -> None:
    """'warning' is a valid log level."""
    cfg = AppConfig(
        server=ServerConfig(host="0.0.0.0", port=8080, log_level="warning"),
        camera=CameraConfig(),
        model=ModelConfig(model="yolov8n", confidence_threshold=0.5),
    )
    validate(cfg)  # must not raise


@pytest.mark.unit
def test_validate_server_log_level_error_valid() -> None:
    """'error' is a valid log level."""
    cfg = AppConfig(
        server=ServerConfig(host="0.0.0.0", port=8080, log_level="error"),
        camera=CameraConfig(),
        model=ModelConfig(model="yolov8n", confidence_threshold=0.5),
    )
    validate(cfg)  # must not raise


@pytest.mark.unit
def test_validate_server_log_level_critical_valid() -> None:
    """'critical' is a valid log level."""
    cfg = AppConfig(
        server=ServerConfig(host="0.0.0.0", port=8080, log_level="critical"),
        camera=CameraConfig(),
        model=ModelConfig(model="yolov8n", confidence_threshold=0.5),
    )
    validate(cfg)  # must not raise


# --- 5.5 camera.source_type ---


@pytest.mark.unit
def test_validate_camera_source_type_invalid_raises() -> None:
    """Unknown source type raises ConfigurationError."""
    cfg = AppConfig(
        server=ServerConfig(),
        camera=CameraConfig(source_type="usb", device_index=0, rtsp_url=""),
        model=ModelConfig(model="yolov8n", confidence_threshold=0.5),
    )
    with pytest.raises(
        ConfigurationError,
        match='camera.source_type must be one of "local", "rtsp", got "usb"',
    ):
        validate(cfg)


# --- 5.6 camera.device_index ---


@pytest.mark.unit
def test_validate_camera_device_index_negative_raises() -> None:
    """Negative device index raises ConfigurationError."""
    cfg = AppConfig(
        server=ServerConfig(),
        camera=CameraConfig(source_type="local", device_index=-1, rtsp_url=""),
        model=ModelConfig(model="yolov8n", confidence_threshold=0.5),
    )
    with pytest.raises(ConfigurationError, match="camera.device_index must be >= 0, got -1"):
        validate(cfg)


@pytest.mark.unit
def test_validate_camera_device_index_zero_valid() -> None:
    """Device index 0 is valid."""
    cfg = AppConfig(
        server=ServerConfig(),
        camera=CameraConfig(source_type="local", device_index=0, rtsp_url=""),
        model=ModelConfig(model="yolov8n", confidence_threshold=0.5),
    )
    validate(cfg)  # must not raise


# --- 5.7 camera.rtsp_url ---


@pytest.mark.unit
def test_validate_camera_rtsp_url_empty_when_rtsp_raises() -> None:
    """Empty RTSP URL with source_type='rtsp' raises ConfigurationError."""
    cfg = AppConfig(
        server=ServerConfig(),
        camera=CameraConfig(source_type="rtsp", device_index=0, rtsp_url=""),
        model=ModelConfig(model="yolov8n", confidence_threshold=0.5),
    )
    with pytest.raises(
        ConfigurationError,
        match='camera.rtsp_url must be non-empty when source_type is "rtsp"',
    ):
        validate(cfg)


@pytest.mark.unit
def test_validate_camera_rtsp_url_empty_when_local_valid() -> None:
    """Empty RTSP URL with source_type='local' is valid."""
    cfg = AppConfig(
        server=ServerConfig(),
        camera=CameraConfig(source_type="local", device_index=0, rtsp_url=""),
        model=ModelConfig(model="yolov8n", confidence_threshold=0.5),
    )
    validate(cfg)  # must not raise


# --- 5.8 model.model ---


@pytest.mark.unit
def test_validate_model_path_empty_raises() -> None:
    """Empty model name raises ConfigurationError."""
    cfg = AppConfig(
        server=ServerConfig(),
        camera=CameraConfig(),
        model=ModelConfig(model="", confidence_threshold=0.5),
    )
    with pytest.raises(ConfigurationError, match="model.model must be non-empty"):
        validate(cfg)


# --- 5.9 model.confidence_threshold ---


@pytest.mark.unit
def test_validate_confidence_threshold_zero_raises() -> None:
    """Threshold 0.0 raises ConfigurationError."""
    cfg = AppConfig(
        server=ServerConfig(),
        camera=CameraConfig(),
        model=ModelConfig(model="yolov8n", confidence_threshold=0.0),
    )
    with pytest.raises(
        ConfigurationError,
        match="model.confidence_threshold must satisfy 0.0 < value <= 1.0, got 0.0",
    ):
        validate(cfg)


@pytest.mark.unit
def test_validate_confidence_threshold_negative_raises() -> None:
    """Negative threshold raises ConfigurationError."""
    cfg = AppConfig(
        server=ServerConfig(),
        camera=CameraConfig(),
        model=ModelConfig(model="yolov8n", confidence_threshold=-0.1),
    )
    with pytest.raises(
        ConfigurationError,
        match="model.confidence_threshold must satisfy 0.0 < value <= 1.0, got -0.1",
    ):
        validate(cfg)


@pytest.mark.unit
def test_validate_confidence_threshold_above_one_raises() -> None:
    """Threshold 1.5 raises ConfigurationError."""
    cfg = AppConfig(
        server=ServerConfig(),
        camera=CameraConfig(),
        model=ModelConfig(model="yolov8n", confidence_threshold=1.5),
    )
    with pytest.raises(
        ConfigurationError,
        match="model.confidence_threshold must satisfy 0.0 < value <= 1.0, got 1.5",
    ):
        validate(cfg)


@pytest.mark.unit
def test_validate_confidence_threshold_min_boundary_valid() -> None:
    """Threshold just above 0.0 (0.01) is valid."""
    cfg = AppConfig(
        server=ServerConfig(),
        camera=CameraConfig(),
        model=ModelConfig(model="yolov8n", confidence_threshold=0.01),
    )
    validate(cfg)  # must not raise


@pytest.mark.unit
def test_validate_confidence_threshold_max_boundary_valid() -> None:
    """Threshold exactly 1.0 is valid."""
    cfg = AppConfig(
        server=ServerConfig(),
        camera=CameraConfig(),
        model=ModelConfig(model="yolov8n", confidence_threshold=1.0),
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


# --- 6.1 No config file — uses defaults ---


@pytest.mark.unit
def test_load_no_config_file_uses_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When no --config flag and no model_lens.toml in cwd, built-in defaults are used."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])

    cfg = load()

    assert cfg.server.port == 8080


@pytest.mark.unit
def test_load_no_config_file_logs_warning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Warning is logged when no config file is found."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])

    with patch("model_lens.config.logger") as mock_logger:
        load()

    mock_logger.warning.assert_called_once_with("No config file found; using built-in defaults.")


# --- 6.2 Default config file discovered ---


@pytest.mark.unit
def test_load_default_config_file_discovered(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """model_lens.toml in cwd is loaded automatically."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])

    config_file = tmp_path / "model_lens.toml"
    config_file.write_text("[server]\nport = 7777\n")

    cfg = load()
    assert cfg.server.port == 7777


@pytest.mark.unit
def test_load_default_config_file_logs_info(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Info is logged when config file is found."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])

    config_file = tmp_path / "model_lens.toml"
    config_file.write_text("[server]\nport = 8080\n")

    with patch("model_lens.config.logger") as mock_logger:
        load()

    _assert_log_call(mock_logger.info, "Loading config from", str(config_file))


# --- 6.3 Explicit --config flag ---


@pytest.mark.unit
def test_load_explicit_config_flag_loads_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """--config path is loaded."""
    monkeypatch.chdir(tmp_path)

    config_file = tmp_path / "custom.toml"
    config_file.write_text("[server]\nport = 6543\n")
    monkeypatch.setattr(sys, "argv", ["prog", "--config", str(config_file)])

    cfg = load()
    assert cfg.server.port == 6543


@pytest.mark.unit
def test_load_explicit_config_flag_logs_info(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Info is logged for explicit config path."""
    monkeypatch.chdir(tmp_path)

    config_file = tmp_path / "custom.toml"
    config_file.write_text("[server]\nport = 8080\n")
    monkeypatch.setattr(sys, "argv", ["prog", "--config", str(config_file)])

    with patch("model_lens.config.logger") as mock_logger:
        load()

    _assert_log_call(mock_logger.info, "Loading config from", str(config_file))


# --- 6.4 TOML overrides ---


@pytest.mark.unit
def test_load_toml_overrides_server_port(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TOML [server] port = 9090 overrides default."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])

    config_file = tmp_path / "model_lens.toml"
    config_file.write_text("[server]\nport = 9090\n")

    cfg = load()
    assert cfg.server.port == 9090


@pytest.mark.unit
def test_load_toml_overrides_camera_source_type(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TOML [camera] source_type = 'rtsp' overrides default."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])

    config_file = tmp_path / "model_lens.toml"
    config_file.write_text(
        '[camera]\nsource_type = "rtsp"\nrtsp_url = "rtsp://host/s"\n'
    )

    cfg = load()
    assert cfg.camera.source_type == "rtsp"


@pytest.mark.unit
def test_load_toml_overrides_confidence_threshold(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TOML [model] confidence_threshold = 0.8 overrides default."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])

    config_file = tmp_path / "model_lens.toml"
    config_file.write_text("[model]\nconfidence_threshold = 0.8\n")

    cfg = load()
    assert cfg.model.confidence_threshold == 0.8


@pytest.mark.unit
def test_load_toml_unknown_keys_ignored(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unknown TOML keys do not raise."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])

    config_file = tmp_path / "model_lens.toml"
    config_file.write_text('[server]\nunknown_key = "x"\n')

    load()  # must not raise


@pytest.mark.unit
def test_load_toml_missing_keys_retain_defaults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keys absent from TOML retain built-in defaults."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])

    config_file = tmp_path / "model_lens.toml"
    config_file.write_text("[server]\nport = 9090\n")

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


@pytest.mark.unit
def test_load_env_override_server_host(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ML_SERVER_HOST overrides host."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setenv("ML_SERVER_HOST", "192.168.0.1")

    cfg = load()

    assert cfg.server.host == "192.168.0.1"


@pytest.mark.unit
def test_load_env_override_server_port(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ML_SERVER_PORT overrides port."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setenv("ML_SERVER_PORT", "9999")

    cfg = load()

    assert cfg.server.port == 9999


@pytest.mark.unit
def test_load_env_override_server_log_level(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ML_SERVER_LOG_LEVEL overrides log level."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setenv("ML_SERVER_LOG_LEVEL", "debug")

    cfg = load()

    assert cfg.server.log_level == "debug"


@pytest.mark.unit
def test_load_env_override_camera_source_type(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ML_CAMERA_SOURCE_TYPE overrides source type."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setenv("ML_CAMERA_SOURCE_TYPE", "rtsp")
    monkeypatch.setenv("ML_CAMERA_RTSP_URL", "rtsp://h/s")

    cfg = load()

    assert cfg.camera.source_type == "rtsp"


@pytest.mark.unit
def test_load_env_override_camera_device_index(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ML_CAMERA_DEVICE_INDEX overrides device index."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setenv("ML_CAMERA_DEVICE_INDEX", "2")

    cfg = load()

    assert cfg.camera.device_index == 2


@pytest.mark.unit
def test_load_env_override_camera_rtsp_url(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ML_CAMERA_RTSP_URL overrides RTSP URL."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setenv("ML_CAMERA_SOURCE_TYPE", "rtsp")
    monkeypatch.setenv("ML_CAMERA_RTSP_URL", "rtsp://cam/live")

    cfg = load()

    assert cfg.camera.rtsp_url == "rtsp://cam/live"


@pytest.mark.unit
def test_load_env_override_model_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ML_MODEL_MODEL overrides model name."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setenv("ML_MODEL_MODEL", "yolov8s")

    cfg = load()

    assert cfg.model.model == "yolov8s"


@pytest.mark.unit
def test_load_env_override_model_confidence_threshold(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ML_MODEL_CONFIDENCE_THRESHOLD overrides threshold."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setenv("ML_MODEL_CONFIDENCE_THRESHOLD", "0.75")

    cfg = load()

    assert cfg.model.confidence_threshold == 0.75


@pytest.mark.unit
def test_load_env_override_logs_debug(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Debug log is emitted for each env override applied."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setenv("ML_SERVER_PORT", "9999")

    with patch("model_lens.config.logger") as mock_logger:
        load()

    _assert_log_call(mock_logger.debug, "ML_SERVER_PORT", "9999", "server", "port")


# --- 7.2 Validation failures ---


@pytest.mark.unit
def test_load_env_coercion_int_failure_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-integer value for an int field raises ConfigurationError."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setenv("ML_SERVER_PORT", "abc")

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
) -> None:
    """Non-float value for a float field raises ConfigurationError."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setenv("ML_MODEL_CONFIDENCE_THRESHOLD", "xyz")

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
) -> None:
    """String env var is always accepted as-is."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setenv("ML_SERVER_HOST", "any-string")

    cfg = load()

    assert cfg.server.host == "any-string"


# ---------------------------------------------------------------------------
# 8. ConfigLoader
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_config_loader_instantiation() -> None:
    """ConfigLoader can be instantiated without arguments."""
    ConfigLoader()  # must not raise


@pytest.mark.unit
def test_config_loader_load_returns_app_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ConfigLoader().load() returns an AppConfig instance."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])

    result = ConfigLoader().load()

    assert isinstance(result, AppConfig)


@pytest.mark.unit
def test_config_loader_load_uses_defaults_when_no_config_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When no --config flag and no model_lens.toml in cwd, built-in defaults are used."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])

    result = ConfigLoader().load()

    assert result.server.port == 8080


@pytest.mark.unit
def test_config_loader_load_raises_configuration_error_on_invalid_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ConfigLoader().load() raises ConfigurationError when validation fails."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])
    monkeypatch.setenv("ML_SERVER_PORT", "0")

    with pytest.raises(ConfigurationError):
        ConfigLoader().load()


@pytest.mark.unit
def test_config_loader_load_raises_configuration_error_on_invalid_toml(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ConfigLoader().load() raises ConfigurationError when TOML is malformed."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["prog"])

    config_file = tmp_path / "model_lens.toml"
    config_file.write_text("not valid toml :::")

    with pytest.raises(ConfigurationError, match="Failed to parse config file at "):
        ConfigLoader().load()
