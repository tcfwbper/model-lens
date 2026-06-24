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

"""Pydantic v2 request models for API routers.

Defines all request body models used for HTTP request validation. These models
are the single source of truth for request body structure and constraints.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator


class LocalCameraRequest(BaseModel):
    """Request to select a local camera source.

    Attributes:
        source_type: Literal discriminator value ``"local"``.
        device_index: Zero-based index of the local camera device.
    """

    source_type: Literal["local"]
    device_index: int = Field(default=0, ge=0)


class RtspCameraRequest(BaseModel):
    """Request to select an RTSP camera source.

    Attributes:
        source_type: Literal discriminator value ``"rtsp"``.
        rtsp_url: URL of the RTSP stream. Must start with ``rtsp://``.
    """

    source_type: Literal["rtsp"]
    rtsp_url: str

    @field_validator("rtsp_url")
    @classmethod
    def _validate_rtsp_url(cls, v: str) -> str:
        """Validate that rtsp_url starts with 'rtsp://'.

        Args:
            v: The URL value to validate.

        Returns:
            The validated URL.

        Raises:
            ValueError: If the URL does not start with ``rtsp://``.
        """
        if not v.startswith("rtsp://"):
            raise ValueError("rtsp_url must start with 'rtsp://'")
        return v


class UpdateCameraRequest(BaseModel):
    """Wraps a polymorphic camera request body.

    Attributes:
        camera: Discriminated union of camera request types.
    """

    camera: Annotated[LocalCameraRequest | RtspCameraRequest, Field(discriminator="source_type")]


class UpdateLabelsRequest(BaseModel):
    """Request to replace the target label filter.

    Attributes:
        target_labels: List of label strings. May be empty.
    """

    target_labels: list[str]
