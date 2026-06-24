# Copyright 2026 ModelLens Contributors
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

"""Application configuration loader, validator, and frozen data classes.

Loads, merges, validates, and exposes the application configuration as an
immutable ``AppConfig`` object. Configuration is resolved from three sources
in priority order (lowest to highest): built-in defaults, optional TOML config
file, and environment variables (``ML_*``).
"""

from __future__ import annotations

import argparse
import dataclasses
import logging
import os
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

from model_lens.exceptions import ConfigurationError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Valid value sets (module-level frozenset constants)
# ---------------------------------------------------------------------------

_VALID_LOG_LEVELS: frozenset[str] = frozenset({"debug", "info", "warning", "error", "critical"})
_VALID_SOURCE_TYPES: frozenset[str] = frozenset({"local", "rtsp"})

# ---------------------------------------------------------------------------
# Frozen dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ServerConfig:
    """Server configuration settings.

    Args:
        host: Bind address.
        port: Listening port number (1–65535).
        log_level: Logging level name.
    """

    host: str = "0.0.0.0"
    port: int = 8080
    log_level: str = "info"


@dataclass(frozen=True)
class CameraConfig:
    """Camera startup configuration.

    Args:
        source_type: One of ``"local"`` or ``"rtsp"``.
        device_index: Local device index (>= 0).
        rtsp_url: RTSP stream URL (required when source_type is ``"rtsp"``).
    """

    source_type: str = "local"
    device_index: int = 0
    rtsp_url: str = ""


@dataclass(frozen=True)
class ModelConfig:
    """Model configuration.

    Args:
        model: Model name/identifier (non-empty).
        confidence_threshold: Detection confidence threshold (0.0 < value <= 1.0).
    """

    model: str = "yolov8n"
    confidence_threshold: float = 0.5


@dataclass(frozen=True)
class AppConfig:
    """Top-level application configuration, composed of frozen sub-configs.

    Args:
        server: Server settings.
        camera: Camera startup defaults.
        model: Model settings.
    """

    server: ServerConfig = dataclasses.field(default_factory=ServerConfig)
    camera: CameraConfig = dataclasses.field(default_factory=CameraConfig)
    model: ModelConfig = dataclasses.field(default_factory=ModelConfig)


# ---------------------------------------------------------------------------
# Environment variable mapping
# ---------------------------------------------------------------------------

_ENV_VAR_MAP: dict[str, tuple[str, str, type[Any]]] = {
    "ML_SERVER_HOST": ("server", "host", str),
    "ML_SERVER_PORT": ("server", "port", int),
    "ML_SERVER_LOG_LEVEL": ("server", "log_level", str),
    "ML_CAMERA_SOURCE_TYPE": ("camera", "source_type", str),
    "ML_CAMERA_DEVICE_INDEX": ("camera", "device_index", int),
    "ML_CAMERA_RTSP_URL": ("camera", "rtsp_url", str),
    "ML_MODEL_MODEL": ("model", "model", str),
    "ML_MODEL_CONFIDENCE_THRESHOLD": ("model", "confidence_threshold", float),
}

# ---------------------------------------------------------------------------
# Section dataclass registry
# ---------------------------------------------------------------------------

_SECTION_DATACLASS: dict[str, type[Any]] = {
    "server": ServerConfig,
    "camera": CameraConfig,
    "model": ModelConfig,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load() -> AppConfig:
    """Load, merge, and validate the application configuration.

    Resolution order (lowest to highest priority):
    1. Built-in defaults.
    2. Optional TOML config file (``--config`` CLI flag or ``model_lens.toml`` in cwd).
    3. Environment variables (``ML_<SECTION>_<KEY>``).

    Returns:
        Fully validated, immutable ``AppConfig``.

    Raises:
        ConfigurationError: On TOML parse failure, env var coercion failure, or
            validation failure.
    """
    # Step 1: Parse --config from sys.argv
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--config", default=None)
    known, _ = parser.parse_known_args()

    # Step 2: Resolve config file path
    config_path: Path | None = None
    if known.config is not None:
        config_path = Path(known.config)
    else:
        cwd_toml = Path.cwd() / "model_lens.toml"
        if cwd_toml.is_file():
            config_path = cwd_toml

    # Step 3/4: Read config file or log warning
    toml_data: dict[str, Any] = {}
    if config_path is not None:
        logger.info("Loading config file: %s", config_path)
        try:
            content = config_path.read_text(encoding="utf-8")
            toml_data = tomllib.loads(content)
        except Exception as exc:
            raise ConfigurationError(f"Failed to parse config file: {config_path}") from exc
    else:
        logger.warning("No config file found; using built-in defaults.")

    # Step 5: Merge TOML values onto defaults per section
    section_dicts: dict[str, dict[str, Any]] = {
        "server": {"host": "0.0.0.0", "port": 8080, "log_level": "info"},
        "camera": {"source_type": "local", "device_index": 0, "rtsp_url": ""},
        "model": {"model": "yolov8n", "confidence_threshold": 0.5},
    }

    for section_name, dc_class in _SECTION_DATACLASS.items():
        valid_keys = {f.name for f in fields(dc_class)}
        toml_section = toml_data.get(section_name, {})
        for key, value in toml_section.items():
            if key in valid_keys:
                section_dicts[section_name][key] = value

    # Step 6: Apply environment variable overrides
    for env_var, (section, field_name, target_type) in _ENV_VAR_MAP.items():
        raw_value = os.environ.get(env_var)
        if raw_value is not None:
            if target_type is str:
                coerced_value: Any = raw_value
            else:
                try:
                    coerced_value = target_type(raw_value)
                except (ValueError, TypeError) as exc:
                    raise ConfigurationError(
                        f'Cannot coerce {env_var}="{raw_value}" to {target_type.__name__}'
                    ) from exc
            section_dicts[section][field_name] = coerced_value
            logger.debug("Env override applied: %s=%r", env_var, coerced_value)

    # Step 7: Construct config objects
    cfg = AppConfig(
        server=ServerConfig(**section_dicts["server"]),
        camera=CameraConfig(**section_dicts["camera"]),
        model=ModelConfig(**section_dicts["model"]),
    )

    # Step 8: Validate and return
    validate(cfg)
    return cfg


def validate(config: AppConfig) -> None:
    """Validate all constraints on a constructed AppConfig.

    Raises ``ConfigurationError`` on the first violation found.

    Args:
        config: The application configuration to validate.

    Raises:
        ConfigurationError: If any field violates its constraints.
    """
    # server.host must be non-empty
    if not config.server.host:
        raise ConfigurationError("server.host must be non-empty")

    # server.port must be 1–65535
    if not (1 <= config.server.port <= 65535):
        raise ConfigurationError(
            f"server.port must be between 1 and 65535, got {config.server.port}"
        )

    # server.log_level must be valid
    if config.server.log_level not in _VALID_LOG_LEVELS:
        raise ConfigurationError(
            f"server.log_level must be one of {sorted(_VALID_LOG_LEVELS)}, got {config.server.log_level!r}"
        )

    # camera.source_type must be valid
    if config.camera.source_type not in _VALID_SOURCE_TYPES:
        raise ConfigurationError(
            f"camera.source_type must be one of {sorted(_VALID_SOURCE_TYPES)}, got {config.camera.source_type!r}"
        )

    # camera.device_index must be >= 0
    if config.camera.device_index < 0:
        raise ConfigurationError(
            f"camera.device_index must be >= 0, got {config.camera.device_index}"
        )

    # camera.rtsp_url must be non-empty when source_type is "rtsp"
    if config.camera.source_type == "rtsp" and not config.camera.rtsp_url:
        raise ConfigurationError(
            "camera.rtsp_url must be non-empty when source_type is 'rtsp'"
        )

    # model.model must be non-empty
    if not config.model.model:
        raise ConfigurationError(
            f'model.model must be non-empty, got "{config.model.model}"'
        )

    # model.confidence_threshold must satisfy 0.0 < value <= 1.0
    if not (0.0 < config.model.confidence_threshold <= 1.0):
        raise ConfigurationError(
            f"model.confidence_threshold must be between 0.0 (exclusive) and 1.0 (inclusive),"
            f" got {config.model.confidence_threshold}"
        )


class ConfigLoader:
    """Thin class wrapper around ``load()`` for dependency injection.

    Provides a single ``load()`` method that delegates entirely to the
    module-level ``load()`` function.
    """

    def load(self) -> AppConfig:
        """Load and return a validated AppConfig.

        Returns:
            Fully validated, immutable ``AppConfig``.

        Raises:
            ConfigurationError: On any configuration error.
        """
        return load()
