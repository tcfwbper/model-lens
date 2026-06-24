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

"""RuntimeConfig entity — the full runtime state of the server."""

from __future__ import annotations

from dataclasses import dataclass, field

from model_lens.entities.camera_config import CameraConfig, LocalCameraConfig


@dataclass(frozen=True)
class RuntimeConfig:
    """The full runtime state of the server.

    Holds the active camera configuration, the list of target labels, and the
    model confidence threshold. Replaced atomically on each update; never mutated
    in place.

    Args:
        camera: The active camera configuration.
        target_labels: List of label strings to flag as targets.
        confidence_threshold: Model confidence threshold.
    """

    camera: CameraConfig = field(default_factory=lambda: LocalCameraConfig(device_index=0))
    target_labels: list[str] = field(default_factory=list)
    confidence_threshold: float = 0.5
