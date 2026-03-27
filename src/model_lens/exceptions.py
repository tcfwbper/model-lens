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
"""Project-specific exception hierarchy for ModelLens.

All exceptions derive from :class:`ModelLensError`, which itself inherits from
the built-in :class:`Exception`.  Every class accepts exactly one positional
argument — a human-readable, actionable message string.
"""


class ModelLensError(Exception):
    """Base class for all ModelLens project-specific exceptions.

    Args:
        message: A human-readable description of the error.

    Raises:
        TypeError: If called with zero or more than one positional argument.
    """

    def __init__(self, message: str) -> None:  # pylint: disable=useless-super-delegation
        """Initialise the exception with a single message string.

        Args:
            message: A human-readable description of the error.
        """
        super().__init__(message)


class ConfigurationError(ModelLensError):
    """Raised when configuration is invalid or missing.

    Typical triggers: a config key fails validation, a required path does not exist.

    Args:
        message: A human-readable description of the configuration problem.
    """


class HardwareError(ModelLensError):
    """Raised when an interaction with hardware fails.

    Typical triggers: camera device cannot be opened, GPU is unavailable.

    Args:
        message: A human-readable description of the hardware failure.
    """


class DeviceNotFoundError(HardwareError):
    """Raised when a specific hardware device cannot be found.

    Typical triggers: the requested camera device index does not exist,
    an RTSP URL is unreachable.

    Args:
        message: A human-readable description of which device was not found.
    """


class DataError(ModelLensError):
    """Raised when data is unexpected or malformed.

    Acts as a grouping base; prefer :class:`ValidationError` or
    :class:`ParseError` over raising :class:`DataError` directly.

    Args:
        message: A human-readable description of the data problem.
    """


class ValidationError(DataError):
    """Raised when input fails validation rules.

    Typical triggers: a field value is out of range, a required field is empty.

    Args:
        message: A human-readable description of the validation failure.
    """


class ParseError(DataError):
    """Raised when data cannot be parsed or decoded.

    Typical triggers: a label map file is empty or contains unparseable content,
    a TOML config file is malformed.

    Args:
        message: A human-readable description of the parse failure.
    """


class OperationError(ModelLensError):
    """Raised when a valid operation fails at runtime.

    Typical triggers: a model file cannot be loaded, an inference call fails
    unexpectedly.

    Args:
        message: A human-readable description of the operation failure.
    """
