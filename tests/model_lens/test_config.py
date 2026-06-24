"""Tests for model_lens.config — load, validate, ConfigLoader, and AppConfig immutability."""

from __future__ import annotations

import dataclasses
import logging
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

# Skip entire module if production config module is not yet implemented.
config_mod = pytest.importorskip(
    "model_lens.config",
    reason="Production module model_lens.config not yet implemented",
)

from model_lens.config import (  # noqa: E402
    AppConfig,
    CameraConfig,
    ConfigLoader,
    ModelConfig,
    ServerConfig,
    load,
    validate,
)
from model_lens.exceptions import ConfigurationError  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers & Fixtures
# ---------------------------------------------------------------------------

_ML_ENV_VARS = [
    "ML_SERVER_HOST",
    "ML_SERVER_PORT",
    "ML_SERVER_LOG_LEVEL",
    "ML_CAMERA_SOURCE_TYPE",
    "ML_CAMERA_DEVICE_INDEX",
    "ML_CAMERA_RTSP_URL",
    "ML_MODEL_MODEL",
    "ML_MODEL_CONFIDENCE_THRESHOLD",
]


@pytest.fixture(autouse=True)
def _clean_ml_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove all ML_* env vars so tests start from a known state."""
    for var in _ML_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture()
def _minimal_argv(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set sys.argv to bare minimum (no --config flag)."""
    monkeypatch.setattr(sys, "argv", ["prog"])


@pytest.fixture()
def no_config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide a tmp directory guaranteed to have no model_lens.toml."""
    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
    return tmp_path


def write_toml(tmp_path: Path, content: str) -> Path:
    """Write a TOML file in the given directory and return its path."""
    toml_file = tmp_path / "config.toml"
    toml_file.write_text(content)
    return toml_file


def make_default_app_config(**overrides: Any) -> AppConfig:
    """Construct an AppConfig with defaults, applying nested overrides.

    Overrides use dotted keys: ``server.port=9090``, ``model.model="yolov8s"``.
    """
    server_kw: dict[str, Any] = {"host": "0.0.0.0", "port": 8080, "log_level": "info"}
    camera_kw: dict[str, Any] = {"source_type": "local", "device_index": 0, "rtsp_url": ""}
    model_kw: dict[str, Any] = {"model": "yolov8n", "confidence_threshold": 0.5}

    section_map = {"server": server_kw, "camera": camera_kw, "model": model_kw}

    for key, value in overrides.items():
        section, field = key.split(".", 1)
        section_map[section][field] = value

    return AppConfig(
        server=ServerConfig(**server_kw),
        camera=CameraConfig(**camera_kw),
        model=ModelConfig(**model_kw),
    )


# ---------------------------------------------------------------------------
# load — Happy Path
# ---------------------------------------------------------------------------


class TestLoadHappyPath:
    """Happy-path tests for the module-level load() function."""

    def test_load_defaults_when_no_config_file(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Returns AppConfig with all built-in defaults when no TOML file exists."""
        monkeypatch.setattr(sys, "argv", ["prog"])
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

        cfg = load()

        assert cfg.server.host == "0.0.0.0"
        assert cfg.server.port == 8080
        assert cfg.server.log_level == "info"
        assert cfg.camera.source_type == "local"
        assert cfg.camera.device_index == 0
        assert cfg.camera.rtsp_url == ""
        assert cfg.model.model == "yolov8n"
        assert cfg.model.confidence_threshold == 0.5

    def test_load_reads_toml_from_cli_config_flag(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Reads and applies the TOML file specified by --config."""
        toml_file = write_toml(tmp_path, "[server]\nport = 9090\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--config", str(toml_file)])

        cfg = load()

        assert cfg.server.port == 9090
        # Other fields remain at defaults
        assert cfg.server.host == "0.0.0.0"
        assert cfg.model.model == "yolov8n"

    def test_load_reads_toml_from_cwd(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Reads model_lens.toml from the current working directory."""
        (tmp_path / "model_lens.toml").write_text('[model]\nmodel = "yolov8s"\n')
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        monkeypatch.setattr(sys, "argv", ["prog"])

        cfg = load()

        assert cfg.model.model == "yolov8s"

    def test_load_env_var_overrides_toml_value(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Environment variable takes precedence over TOML file value."""
        toml_file = write_toml(tmp_path, "[server]\nport = 9090\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--config", str(toml_file)])
        monkeypatch.setenv("ML_SERVER_PORT", "7070")

        cfg = load()

        assert cfg.server.port == 7070

    def test_load_env_var_overrides_default(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Environment variable overrides built-in default when no TOML file exists."""
        monkeypatch.setattr(sys, "argv", ["prog"])
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        monkeypatch.setenv("ML_MODEL_CONFIDENCE_THRESHOLD", "0.8")

        cfg = load()

        assert cfg.model.confidence_threshold == 0.8

    def test_load_ignores_unknown_toml_keys(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Unknown keys in TOML file are silently ignored."""
        toml_file = write_toml(tmp_path, '[server]\nport = 9090\nunknown_key = "value"\n')
        monkeypatch.setattr(sys, "argv", ["prog", "--config", str(toml_file)])

        cfg = load()

        assert cfg.server.port == 9090

    def test_load_empty_toml_uses_defaults(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """An empty but valid TOML file results in all defaults."""
        toml_file = write_toml(tmp_path, "")
        monkeypatch.setattr(sys, "argv", ["prog", "--config", str(toml_file)])

        cfg = load()

        assert cfg.server.host == "0.0.0.0"
        assert cfg.server.port == 8080
        assert cfg.model.model == "yolov8n"

    def test_load_ignores_unrecognized_argv(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Unrecognized CLI arguments are ignored via parse_known_args()."""
        monkeypatch.setattr(sys, "argv", ["prog", "--unknown-flag", "value"])
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

        cfg = load()

        assert cfg.server.host == "0.0.0.0"
        assert cfg.server.port == 8080


# ---------------------------------------------------------------------------
# load — Error Propagation
# ---------------------------------------------------------------------------


class TestLoadErrorPropagation:
    """Error-propagation tests for load()."""

    def test_load_raises_on_nonexistent_config_file(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Raises ConfigurationError when --config points to a non-existent file."""
        monkeypatch.setattr(sys, "argv", ["prog", "--config", "/nonexistent/path.toml"])

        with pytest.raises(ConfigurationError, match="Failed to parse config file"):
            load()

    def test_load_raises_on_invalid_toml_syntax(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Raises ConfigurationError wrapping the TOML parse error."""
        toml_file = write_toml(tmp_path, "[server\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--config", str(toml_file)])

        with pytest.raises(ConfigurationError) as exc_info:
            load()

        # __cause__ should be the original tomllib exception
        assert exc_info.value.__cause__ is not None

    def test_load_raises_on_env_var_coercion_failure(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Raises ConfigurationError when an env var cannot be coerced to the target type."""
        monkeypatch.setattr(sys, "argv", ["prog"])
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        monkeypatch.setenv("ML_SERVER_PORT", "abc")

        with pytest.raises(ConfigurationError, match=r'Cannot coerce ML_SERVER_PORT="abc" to int'):
            load()


# ---------------------------------------------------------------------------
# load — Mock / Dependency Interaction (Logging)
# ---------------------------------------------------------------------------


class TestLoadLogging:
    """Verify load() logging behavior."""

    def test_load_logs_info_when_config_file_found(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Logs at INFO level when a config file is successfully located."""
        toml_file = write_toml(tmp_path, "[server]\nport = 9090\n")
        monkeypatch.setattr(sys, "argv", ["prog", "--config", str(toml_file)])

        with caplog.at_level(logging.INFO, logger="model_lens.config"):
            load()

        assert any(str(toml_file) in record.message and record.levelno == logging.INFO for record in caplog.records)

    def test_load_logs_warning_when_no_config_file(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Logs at WARNING level when no config file is found."""
        monkeypatch.setattr(sys, "argv", ["prog"])
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

        with caplog.at_level(logging.WARNING, logger="model_lens.config"):
            load()

        assert any(record.levelno == logging.WARNING for record in caplog.records)

    def test_load_logs_debug_for_each_env_override(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Logs at DEBUG level for each applied environment variable override."""
        monkeypatch.setattr(sys, "argv", ["prog"])
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        monkeypatch.setenv("ML_SERVER_PORT", "9090")
        monkeypatch.setenv("ML_MODEL_MODEL", "yolov8s")

        with caplog.at_level(logging.DEBUG, logger="model_lens.config"):
            load()

        debug_records = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert len(debug_records) >= 2


# ---------------------------------------------------------------------------
# validate — Happy Path
# ---------------------------------------------------------------------------


class TestValidateHappyPath:
    """Happy-path tests for validate()."""

    def test_validate_accepts_valid_config(self) -> None:
        """Returns None for a fully valid AppConfig."""
        cfg = make_default_app_config()

        result = validate(cfg)

        assert result is None

    def test_validate_accepts_rtsp_with_non_empty_url(self) -> None:
        """Passes when source_type is 'rtsp' and rtsp_url is non-empty."""
        cfg = make_default_app_config(**{"camera.source_type": "rtsp", "camera.rtsp_url": "rtsp://host/stream"})

        result = validate(cfg)

        assert result is None


# ---------------------------------------------------------------------------
# validate — Validation Failures
# ---------------------------------------------------------------------------


class TestValidateServerHost:
    """Validation failures for server.host."""

    def test_validate_rejects_empty_host(self) -> None:
        """Raises ConfigurationError when server.host is empty."""
        cfg = make_default_app_config(**{"server.host": ""})

        with pytest.raises(ConfigurationError, match="server.host"):
            validate(cfg)


class TestValidateServerPort:
    """Validation failures for server.port."""

    def test_validate_rejects_port_zero(self) -> None:
        """Raises ConfigurationError when server.port is 0."""
        cfg = make_default_app_config(**{"server.port": 0})

        with pytest.raises(ConfigurationError, match="server.port") as exc_info:
            validate(cfg)

        assert "0" in str(exc_info.value)
        assert "1" in str(exc_info.value) and "65535" in str(exc_info.value)

    def test_validate_rejects_port_above_65535(self) -> None:
        """Raises ConfigurationError when server.port exceeds 65535."""
        cfg = make_default_app_config(**{"server.port": 65536})

        with pytest.raises(ConfigurationError, match="server.port") as exc_info:
            validate(cfg)

        assert "65536" in str(exc_info.value)
        assert "1" in str(exc_info.value) and "65535" in str(exc_info.value)


class TestValidateServerLogLevel:
    """Validation failures for server.log_level."""

    def test_validate_rejects_invalid_log_level(self) -> None:
        """Raises ConfigurationError for an unrecognized log level."""
        cfg = make_default_app_config(**{"server.log_level": "verbose"})

        with pytest.raises(ConfigurationError, match="server.log_level") as exc_info:
            validate(cfg)

        assert "verbose" in str(exc_info.value)


class TestValidateCameraSourceType:
    """Validation failures for camera.source_type."""

    def test_validate_rejects_invalid_source_type(self) -> None:
        """Raises ConfigurationError for an unrecognized source type."""
        cfg = make_default_app_config(**{"camera.source_type": "usb"})

        with pytest.raises(ConfigurationError, match="camera.source_type") as exc_info:
            validate(cfg)

        assert "usb" in str(exc_info.value)


class TestValidateCameraDeviceIndex:
    """Validation failures for camera.device_index."""

    def test_validate_rejects_negative_device_index(self) -> None:
        """Raises ConfigurationError when device_index is negative."""
        cfg = make_default_app_config(**{"camera.device_index": -1})

        with pytest.raises(ConfigurationError, match="camera.device_index") as exc_info:
            validate(cfg)

        assert "-1" in str(exc_info.value)


class TestValidateCameraRtspUrl:
    """Validation failures for camera.rtsp_url."""

    def test_validate_rejects_empty_rtsp_url_when_rtsp(self) -> None:
        """Raises ConfigurationError when source_type is 'rtsp' but rtsp_url is empty."""
        cfg = make_default_app_config(**{"camera.source_type": "rtsp", "camera.rtsp_url": ""})

        with pytest.raises(ConfigurationError, match="camera.rtsp_url"):
            validate(cfg)


class TestValidateModelName:
    """Validation failures for model.model."""

    def test_validate_rejects_empty_model_name(self) -> None:
        """Raises ConfigurationError when model.model is empty."""
        cfg = make_default_app_config(**{"model.model": ""})

        with pytest.raises(ConfigurationError, match=r"model\.model") as exc_info:
            validate(cfg)

        # Message should reference the empty value
        assert '""' in str(exc_info.value) or "empty" in str(exc_info.value).lower()


class TestValidateConfidenceThreshold:
    """Validation failures for model.confidence_threshold."""

    def test_validate_rejects_threshold_zero(self) -> None:
        """Raises ConfigurationError when confidence_threshold is 0.0."""
        cfg = make_default_app_config(**{"model.confidence_threshold": 0.0})

        with pytest.raises(ConfigurationError, match="model.confidence_threshold") as exc_info:
            validate(cfg)

        assert "0.0" in str(exc_info.value) and "1.0" in str(exc_info.value)

    def test_validate_rejects_threshold_above_one(self) -> None:
        """Raises ConfigurationError when confidence_threshold exceeds 1.0."""
        cfg = make_default_app_config(**{"model.confidence_threshold": 1.1})

        with pytest.raises(ConfigurationError, match="model.confidence_threshold") as exc_info:
            validate(cfg)

        assert "0.0" in str(exc_info.value) and "1.0" in str(exc_info.value)

    def test_validate_rejects_negative_threshold(self) -> None:
        """Raises ConfigurationError when confidence_threshold is negative."""
        cfg = make_default_app_config(**{"model.confidence_threshold": -0.1})

        with pytest.raises(ConfigurationError, match="model.confidence_threshold") as exc_info:
            validate(cfg)

        assert "0.0" in str(exc_info.value) and "1.0" in str(exc_info.value)


# ---------------------------------------------------------------------------
# validate — Boundary Values
# ---------------------------------------------------------------------------


class TestValidateBoundaryThreshold:
    """Boundary value tests for model.confidence_threshold."""

    def test_validate_accepts_threshold_at_one(self) -> None:
        """Passes when confidence_threshold is exactly 1.0."""
        cfg = make_default_app_config(**{"model.confidence_threshold": 1.0})

        result = validate(cfg)

        assert result is None

    def test_validate_accepts_threshold_just_above_zero(self) -> None:
        """Passes when confidence_threshold is just above 0.0."""
        cfg = make_default_app_config(**{"model.confidence_threshold": 0.001})

        result = validate(cfg)

        assert result is None


class TestValidateBoundaryPort:
    """Boundary value tests for server.port."""

    def test_validate_accepts_port_one(self) -> None:
        """Passes when server.port is exactly 1."""
        cfg = make_default_app_config(**{"server.port": 1})

        result = validate(cfg)

        assert result is None

    def test_validate_accepts_port_65535(self) -> None:
        """Passes when server.port is exactly 65535."""
        cfg = make_default_app_config(**{"server.port": 65535})

        result = validate(cfg)

        assert result is None


# ---------------------------------------------------------------------------
# ConfigLoader
# ---------------------------------------------------------------------------


class TestConfigLoader:
    """Tests for the ConfigLoader class wrapper."""

    def test_config_loader_delegates_to_module_load(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """ConfigLoader.load() delegates to the module-level load() function."""
        mock_config = MagicMock(spec=AppConfig)
        monkeypatch.setattr(config_mod, "load", lambda: mock_config)

        loader = ConfigLoader()
        result = loader.load()

        assert result is mock_config


# ---------------------------------------------------------------------------
# AppConfig — Immutability
# ---------------------------------------------------------------------------


class TestImmutability:
    """Verify that config dataclasses are frozen."""

    def test_app_config_is_frozen(self) -> None:
        """Assignment to an AppConfig field raises FrozenInstanceError."""
        cfg = make_default_app_config()
        new_server = ServerConfig(host="127.0.0.1", port=9090, log_level="debug")

        with pytest.raises(dataclasses.FrozenInstanceError):
            cfg.server = new_server  # type: ignore[misc]

    def test_server_config_is_frozen(self) -> None:
        """Assignment to a ServerConfig field raises FrozenInstanceError."""
        server = ServerConfig(host="0.0.0.0", port=8080, log_level="info")

        with pytest.raises(dataclasses.FrozenInstanceError):
            server.port = 9090  # type: ignore[misc]

    def test_camera_config_is_frozen(self) -> None:
        """Assignment to a CameraConfig field raises FrozenInstanceError."""
        camera = CameraConfig(source_type="local", device_index=0, rtsp_url="")

        with pytest.raises(dataclasses.FrozenInstanceError):
            camera.device_index = 1  # type: ignore[misc]

    def test_model_config_is_frozen(self) -> None:
        """Assignment to a ModelConfig field raises FrozenInstanceError."""
        model = ModelConfig(model="yolov8n", confidence_threshold=0.5)

        with pytest.raises(dataclasses.FrozenInstanceError):
            model.model = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# load — Environment Variable Coercion
# ---------------------------------------------------------------------------


class TestLoadEnvVarCoercion:
    """Tests for environment variable type coercion in load()."""

    def test_load_coerces_env_int(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Coerces string env var to int for integer fields."""
        monkeypatch.setattr(sys, "argv", ["prog"])
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        monkeypatch.setenv("ML_CAMERA_DEVICE_INDEX", "2")

        cfg = load()

        assert cfg.camera.device_index == 2

    def test_load_coerces_env_float(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Coerces string env var to float for float fields."""
        monkeypatch.setattr(sys, "argv", ["prog"])
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        monkeypatch.setenv("ML_MODEL_CONFIDENCE_THRESHOLD", "0.75")

        cfg = load()

        assert cfg.model.confidence_threshold == 0.75

    def test_load_applies_empty_string_env_var(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Empty string env var is applied as override (triggers validation failure)."""
        monkeypatch.setattr(sys, "argv", ["prog"])
        monkeypatch.setattr(Path, "cwd", lambda: tmp_path)
        monkeypatch.setenv("ML_SERVER_HOST", "")

        with pytest.raises(ConfigurationError):
            load()
