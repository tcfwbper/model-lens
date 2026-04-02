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
"""Configuration loading and validation for ModelLens.

Provides frozen dataclasses for server, camera, and model configuration,
a ``validate()`` function that checks all constraints, and a ``load()``
function that merges built-in defaults, TOML file values, and environment
variable overrides into a single immutable ``AppConfig``.
"""

import argparse
import logging
import os
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

from model_lens.exceptions import ConfigurationError

logger = logging.getLogger(__name__)

_VALID_LOG_LEVELS = frozenset({"debug", "info", "warning", "error", "critical"})
_VALID_SOURCE_TYPES = frozenset({"local", "rtsp"})

# ---------------------------------------------------------------------------
# Frozen dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ServerConfig:
    """Server configuration.

    Attributes:
        host: Host address the HTTP server binds to.
        port: Port the HTTP server listens on.
        log_level: Logging level.
    """

    host: str = "0.0.0.0"
    port: int = 8080
    log_level: str = "info"


@dataclass(frozen=True)
class CameraConfig:
    """Camera startup configuration.

    Attributes:
        source_type: Camera source type (``"local"`` or ``"rtsp"``).
        device_index: Device index for local webcam.
        rtsp_url: RTSP stream URL.
    """

    source_type: str = "local"
    device_index: int = 0
    rtsp_url: str = ""


@dataclass(frozen=True)
class ModelConfig:
    """Model configuration.

    Attributes:
        model: YOLO model name.
        confidence_threshold: Minimum confidence score for a detection.
    """

    model: str = "yolov8n"
    confidence_threshold: float = 0.5


@dataclass(frozen=True)
class AppConfig:
    """Top-level application configuration.

    Attributes:
        server: Server configuration.
        camera: Camera configuration.
        model: Model configuration.
    """

    server: ServerConfig
    camera: CameraConfig
    model: ModelConfig


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate(cfg: AppConfig) -> None:
    """Validate all configuration constraints.

    Args:
        cfg: The application configuration to validate.

    Raises:
        ConfigurationError: If any constraint is violated.
    """
    # server.host
    if not cfg.server.host:
        raise ConfigurationError("server.host must be non-empty")

    # server.port
    if not 1 <= cfg.server.port <= 65535:
        raise ConfigurationError(f"server.port must be between 1 and 65535, got {cfg.server.port}")

    # server.log_level
    if cfg.server.log_level not in _VALID_LOG_LEVELS:
        raise ConfigurationError(
            f'server.log_level must be one of "debug", "info", "warning", "error", "critical", '
            f'got "{cfg.server.log_level}"'
        )

    # camera.source_type
    if cfg.camera.source_type not in _VALID_SOURCE_TYPES:
        raise ConfigurationError(f'camera.source_type must be one of "local", "rtsp", got "{cfg.camera.source_type}"')

    # camera.device_index
    if cfg.camera.device_index < 0:
        raise ConfigurationError(f"camera.device_index must be >= 0, got {cfg.camera.device_index}")

    # camera.rtsp_url
    if cfg.camera.source_type == "rtsp" and not cfg.camera.rtsp_url:
        raise ConfigurationError('camera.rtsp_url must be non-empty when source_type is "rtsp"')

    # model.model
    if not cfg.model.model:
        raise ConfigurationError("model.model must be non-empty")

    # model.confidence_threshold
    if cfg.model.confidence_threshold <= 0.0 or cfg.model.confidence_threshold > 1.0:
        raise ConfigurationError(
            f"model.confidence_threshold must satisfy 0.0 < value <= 1.0, got {cfg.model.confidence_threshold}"
        )


# ---------------------------------------------------------------------------
# Environment variable mapping
# ---------------------------------------------------------------------------

_ENV_MAP: list[tuple[str, str, str, type]] = [
    ("ML_SERVER_HOST", "server", "host", str),
    ("ML_SERVER_PORT", "server", "port", int),
    ("ML_SERVER_LOG_LEVEL", "server", "log_level", str),
    ("ML_CAMERA_SOURCE_TYPE", "camera", "source_type", str),
    ("ML_CAMERA_DEVICE_INDEX", "camera", "device_index", int),
    ("ML_CAMERA_RTSP_URL", "camera", "rtsp_url", str),
    ("ML_MODEL_MODEL", "model", "model", str),
    ("ML_MODEL_CONFIDENCE_THRESHOLD", "model", "confidence_threshold", float),
]


# ---------------------------------------------------------------------------
# load()
# ---------------------------------------------------------------------------


def load() -> AppConfig:
    """Load, merge, and validate application configuration.

    Resolution order (highest priority wins):
    1. Built-in defaults
    2. TOML config file
    3. Environment variables

    Returns:
        A fully validated, immutable ``AppConfig``.

    Raises:
        ConfigurationError: If the TOML file is malformed, an env var cannot
            be coerced, or the merged config fails validation.
    """
    # --- Parse CLI for --config ------------------------------------------------
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--config", default=None)
    args, _ = parser.parse_known_args()

    # --- Determine config file path -------------------------------------------
    config_path: Path | None = None
    if args.config is not None:
        config_path = Path(args.config)
    else:
        candidate = Path.cwd() / "model_lens.toml"
        if candidate.is_file():
            config_path = candidate

    # --- Load TOML ------------------------------------------------------------
    raw: dict[str, dict[str, Any]] = {}
    if config_path is not None:
        logger.info("Loading config from %s", config_path)
        try:
            raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ConfigurationError(f"Failed to parse config file at {config_path}: {exc}") from exc
    else:
        logger.warning("No config file found; using built-in defaults.")

    # --- Merge TOML onto defaults into plain dicts ----------------------------
    server_kw: dict[str, Any] = {}
    camera_kw: dict[str, Any] = {}
    model_kw: dict[str, Any] = {}

    section_map: dict[str, tuple[dict[str, Any], type]] = {
        "server": (server_kw, ServerConfig),
        "camera": (camera_kw, CameraConfig),
        "model": (model_kw, ModelConfig),
    }

    for section_name, (kw_dict, dc_cls) in section_map.items():
        toml_section = raw.get(section_name, {})
        valid_keys = {f.name for f in fields(dc_cls)}
        for key, value in toml_section.items():
            if key in valid_keys:
                kw_dict[key] = value

    # --- Apply environment variable overrides ---------------------------------
    for env_var, section, key, coerce_type in _ENV_MAP:
        value = os.environ.get(env_var)
        if value is None:
            continue

        if coerce_type is int:
            try:
                coerced: Any = int(value)
            except ValueError as exc:
                raise ConfigurationError(f'Cannot coerce {env_var}="{value}" to int') from exc
        elif coerce_type is float:
            try:
                coerced = float(value)
            except ValueError as exc:
                raise ConfigurationError(f'Cannot coerce {env_var}="{value}" to float') from exc
        else:
            coerced = value

        kw_dict_for_section = section_map[section][0]
        kw_dict_for_section[key] = coerced
        logger.debug('Env override: %s="%s" \u2192 %s.%s', env_var, value, section, key)

    # --- Build and validate ---------------------------------------------------
    cfg = AppConfig(
        server=ServerConfig(**server_kw),
        camera=CameraConfig(**camera_kw),
        model=ModelConfig(**model_kw),
    )
    validate(cfg)
    return cfg


# ---------------------------------------------------------------------------
# ConfigLoader
# ---------------------------------------------------------------------------


class ConfigLoader:
    """Thin object wrapper around :func:`load`.

    Provides an instantiable interface for loading application configuration, useful in contexts that require dependency
    injection or subclassing.
    """

    def load(self) -> AppConfig:
        """Load, merge, and validate application configuration.

        Delegates entirely to the module-level :func:`load` function.

        Returns:
            A fully validated, immutable ``AppConfig``.

        Raises:
            ConfigurationError: If the TOML file is malformed, an env var cannot
                be coerced, or the merged config fails validation.
        """
        return load()
