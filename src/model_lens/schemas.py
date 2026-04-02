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
"""Request schemas for model_lens API."""

from typing import Annotated, Literal

import pydantic


class LocalCameraRequest(pydantic.BaseModel):
    """Request body for selecting a local camera source."""

    source_type: Literal["local"]
    device_index: Annotated[int, pydantic.Field(ge=0)] = 0


class RtspCameraRequest(pydantic.BaseModel):
    """Request body for selecting an RTSP camera source."""

    source_type: Literal["rtsp"]
    rtsp_url: str

    @pydantic.field_validator("rtsp_url")
    @classmethod
    def validate_rtsp_url(cls, v: str) -> str:
        """Validate that the RTSP URL uses the rtsp:// scheme."""
        if not v.startswith("rtsp://"):
            raise ValueError("rtsp_url must start with 'rtsp://'")
        return v


class UpdateCameraRequest(pydantic.BaseModel):
    """Request body for updating the camera source."""

    camera: Annotated[
        LocalCameraRequest | RtspCameraRequest,
        pydantic.Field(discriminator="source_type"),
    ]


class UpdateLabelsRequest(pydantic.BaseModel):
    """Request body for updating the target label filter."""

    target_labels: list[str]
