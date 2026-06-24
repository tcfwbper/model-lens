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

"""Domain entities for ModelLens."""

from __future__ import annotations

from model_lens.entities.camera_config import (
    CameraConfig,
    LocalCameraConfig,
    RtspCameraConfig,
)
from model_lens.entities.detection_result import DetectionResult
from model_lens.entities.frame import Frame
from model_lens.entities.runtime_config import RuntimeConfig

__all__ = [
    "CameraConfig",
    "DetectionResult",
    "Frame",
    "LocalCameraConfig",
    "RtspCameraConfig",
    "RuntimeConfig",
]
