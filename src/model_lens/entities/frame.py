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

"""Frame entity — a single decoded image captured from a camera source."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass
class Frame:
    """A single decoded image captured from a camera source.

    The ``data`` array is stored as-is (no internal copy). Consumers must treat
    ``data`` as read-only by convention.

    Args:
        data: Image data as a NumPy array with shape (H, W, 3) and dtype uint8.
        timestamp: POSIX timestamp (seconds since epoch) with sub-second precision.
        source: Human-readable identifier for the camera source.
    """

    data: NDArray[np.uint8]
    timestamp: float
    source: str
