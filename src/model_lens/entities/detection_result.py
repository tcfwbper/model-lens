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

"""DetectionResult entity — a single detected object from one inference pass."""

from __future__ import annotations

from dataclasses import dataclass

from model_lens.exceptions import ValidationError


@dataclass(frozen=True)
class DetectionResult:
    """A single detected object produced by one inference pass.

    Args:
        label: Human-readable label for the detected object.
        confidence: Confidence score in the range (0.0, 1.0].
        bounding_box: Normalised bounding box as (x1, y1, x2, y2).
        is_target: Whether the label is in the configured target list.

    Raises:
        ValidationError: If label is empty or confidence is out of range.
    """

    label: str
    confidence: float
    bounding_box: tuple[float, float, float, float]
    is_target: bool

    def __post_init__(self) -> None:
        """Validate label and confidence after construction.

        Raises:
            ValidationError: If label is empty or confidence is out of range.
        """
        if self.label == "":
            raise ValidationError("label must not be empty")
        if not (0.0 < self.confidence <= 1.0):
            raise ValidationError(
                f"confidence must be in (0.0, 1.0], got {self.confidence}"
            )
