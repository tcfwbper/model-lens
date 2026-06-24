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

"""Project-specific exception hierarchy for ModelLens.

All exceptions derive from ``ModelLensError``. Each class accepts exactly one
positional argument — a human-readable, actionable message string.
"""

from __future__ import annotations


class ModelLensError(Exception):
    """Base exception for all ModelLens errors.

    Args:
        message: Human-readable, actionable description of the error.
    """

    def __init__(self, message: str) -> None:
        """Initialize with a single message string.

        Args:
            message: Human-readable, actionable description of the error.
        """
        super().__init__(message)


class ConfigurationError(ModelLensError):
    """Invalid or missing configuration."""


class HardwareError(ModelLensError):
    """Hardware interaction failures."""


class DeviceNotFoundError(HardwareError):
    """A specific device cannot be found."""


class DataError(ModelLensError):
    """Unexpected or malformed data (grouping base)."""


class ValidationError(DataError):
    """Input fails validation rules."""


class ParseError(DataError):
    """Data cannot be parsed or decoded."""


class OperationError(ModelLensError):
    """A valid operation failed at runtime."""
