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

"""Unit tests for src/model_lens/exceptions.py."""

import pytest

from model_lens.exceptions import (
    ConfigurationError,
    DataError,
    DeviceNotFoundError,
    HardwareError,
    ModelLensError,
    OperationError,
    ParseError,
    ValidationError,
)

# ---------------------------------------------------------------------------
# 1. ModelLensError
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_model_lens_error_stores_message() -> None:
    """Message string is stored and accessible via str()."""
    exc = ModelLensError("something went wrong")
    assert str(exc) == "something went wrong"


@pytest.mark.unit
def test_model_lens_error_args() -> None:
    """Message string is accessible via exc.args[0]."""
    exc = ModelLensError("something went wrong")
    assert exc.args[0] == "something went wrong"


@pytest.mark.unit
def test_model_lens_error_zero_args() -> None:
    """Passing no arguments raises TypeError."""
    with pytest.raises(TypeError):
        ModelLensError()  # type: ignore[call-arg]


@pytest.mark.unit
def test_model_lens_error_two_args() -> None:
    """Passing two arguments raises TypeError."""
    with pytest.raises(TypeError):
        ModelLensError("a", "b")  # type: ignore[call-arg]


@pytest.mark.unit
def test_model_lens_error_is_exception() -> None:
    """ModelLensError inherits from Exception."""
    assert isinstance(ModelLensError("x"), Exception)


@pytest.mark.unit
def test_model_lens_error_caught_as_exception() -> None:
    """ModelLensError can be caught as Exception."""
    with pytest.raises(Exception):
        raise ModelLensError("x")


# ---------------------------------------------------------------------------
# 2. ConfigurationError
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_configuration_error_stores_message() -> None:
    """Message string is stored and accessible via str()."""
    exc = ConfigurationError("bad config")
    assert str(exc) == "bad config"


@pytest.mark.unit
def test_configuration_error_args() -> None:
    """Message string is accessible via exc.args[0]."""
    exc = ConfigurationError("bad config")
    assert exc.args[0] == "bad config"


@pytest.mark.unit
def test_configuration_error_zero_args() -> None:
    """Passing no arguments raises TypeError."""
    with pytest.raises(TypeError):
        ConfigurationError()  # type: ignore[call-arg]


@pytest.mark.unit
def test_configuration_error_two_args() -> None:
    """Passing two arguments raises TypeError."""
    with pytest.raises(TypeError):
        ConfigurationError("a", "b")  # type: ignore[call-arg]


@pytest.mark.unit
def test_configuration_error_is_model_lens_error() -> None:
    """ConfigurationError inherits from ModelLensError."""
    assert isinstance(ConfigurationError("x"), ModelLensError)


@pytest.mark.unit
def test_configuration_error_is_exception() -> None:
    """ConfigurationError inherits from Exception."""
    assert isinstance(ConfigurationError("x"), Exception)


@pytest.mark.unit
def test_configuration_error_caught_as_model_lens_error() -> None:
    """ConfigurationError can be caught as ModelLensError."""
    with pytest.raises(ModelLensError):
        raise ConfigurationError("x")


# ---------------------------------------------------------------------------
# 3. HardwareError
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_hardware_error_stores_message() -> None:
    """Message string is stored and accessible via str()."""
    exc = HardwareError("camera failed")
    assert str(exc) == "camera failed"


@pytest.mark.unit
def test_hardware_error_args() -> None:
    """Message string is accessible via exc.args[0]."""
    exc = HardwareError("camera failed")
    assert exc.args[0] == "camera failed"


@pytest.mark.unit
def test_hardware_error_zero_args() -> None:
    """Passing no arguments raises TypeError."""
    with pytest.raises(TypeError):
        HardwareError()  # type: ignore[call-arg]


@pytest.mark.unit
def test_hardware_error_two_args() -> None:
    """Passing two arguments raises TypeError."""
    with pytest.raises(TypeError):
        HardwareError("a", "b")  # type: ignore[call-arg]


@pytest.mark.unit
def test_hardware_error_is_model_lens_error() -> None:
    """HardwareError inherits from ModelLensError."""
    assert isinstance(HardwareError("x"), ModelLensError)


@pytest.mark.unit
def test_hardware_error_is_exception() -> None:
    """HardwareError inherits from Exception."""
    assert isinstance(HardwareError("x"), Exception)


@pytest.mark.unit
def test_hardware_error_caught_as_model_lens_error() -> None:
    """HardwareError can be caught as ModelLensError."""
    with pytest.raises(ModelLensError):
        raise HardwareError("x")


# ---------------------------------------------------------------------------
# 4. DeviceNotFoundError
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_device_not_found_error_stores_message() -> None:
    """Message string is stored and accessible via str()."""
    exc = DeviceNotFoundError("device 2 not found")
    assert str(exc) == "device 2 not found"


@pytest.mark.unit
def test_device_not_found_error_args() -> None:
    """Message string is accessible via exc.args[0]."""
    exc = DeviceNotFoundError("device 2 not found")
    assert exc.args[0] == "device 2 not found"


@pytest.mark.unit
def test_device_not_found_error_zero_args() -> None:
    """Passing no arguments raises TypeError."""
    with pytest.raises(TypeError):
        DeviceNotFoundError()  # type: ignore[call-arg]


@pytest.mark.unit
def test_device_not_found_error_two_args() -> None:
    """Passing two arguments raises TypeError."""
    with pytest.raises(TypeError):
        DeviceNotFoundError("a", "b")  # type: ignore[call-arg]


@pytest.mark.unit
def test_device_not_found_error_is_hardware_error() -> None:
    """DeviceNotFoundError inherits from HardwareError."""
    assert isinstance(DeviceNotFoundError("x"), HardwareError)


@pytest.mark.unit
def test_device_not_found_error_is_model_lens_error() -> None:
    """DeviceNotFoundError inherits from ModelLensError."""
    assert isinstance(DeviceNotFoundError("x"), ModelLensError)


@pytest.mark.unit
def test_device_not_found_error_is_exception() -> None:
    """DeviceNotFoundError inherits from Exception."""
    assert isinstance(DeviceNotFoundError("x"), Exception)


@pytest.mark.unit
def test_device_not_found_error_caught_as_hardware_error() -> None:
    """DeviceNotFoundError can be caught as HardwareError."""
    with pytest.raises(HardwareError):
        raise DeviceNotFoundError("x")


@pytest.mark.unit
def test_device_not_found_error_caught_as_model_lens_error() -> None:
    """DeviceNotFoundError can be caught as ModelLensError."""
    with pytest.raises(ModelLensError):
        raise DeviceNotFoundError("x")


# ---------------------------------------------------------------------------
# 5. DataError
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_data_error_stores_message() -> None:
    """Message string is stored and accessible via str()."""
    exc = DataError("malformed data")
    assert str(exc) == "malformed data"


@pytest.mark.unit
def test_data_error_args() -> None:
    """Message string is accessible via exc.args[0]."""
    exc = DataError("malformed data")
    assert exc.args[0] == "malformed data"


@pytest.mark.unit
def test_data_error_zero_args() -> None:
    """Passing no arguments raises TypeError."""
    with pytest.raises(TypeError):
        DataError()  # type: ignore[call-arg]


@pytest.mark.unit
def test_data_error_two_args() -> None:
    """Passing two arguments raises TypeError."""
    with pytest.raises(TypeError):
        DataError("a", "b")  # type: ignore[call-arg]


@pytest.mark.unit
def test_data_error_is_model_lens_error() -> None:
    """DataError inherits from ModelLensError."""
    assert isinstance(DataError("x"), ModelLensError)


@pytest.mark.unit
def test_data_error_is_exception() -> None:
    """DataError inherits from Exception."""
    assert isinstance(DataError("x"), Exception)


@pytest.mark.unit
def test_data_error_caught_as_model_lens_error() -> None:
    """DataError can be caught as ModelLensError."""
    with pytest.raises(ModelLensError):
        raise DataError("x")


# ---------------------------------------------------------------------------
# 6. ValidationError
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_validation_error_stores_message() -> None:
    """Message string is stored and accessible via str()."""
    exc = ValidationError("value out of range")
    assert str(exc) == "value out of range"


@pytest.mark.unit
def test_validation_error_args() -> None:
    """Message string is accessible via exc.args[0]."""
    exc = ValidationError("value out of range")
    assert exc.args[0] == "value out of range"


@pytest.mark.unit
def test_validation_error_zero_args() -> None:
    """Passing no arguments raises TypeError."""
    with pytest.raises(TypeError):
        ValidationError()  # type: ignore[call-arg]


@pytest.mark.unit
def test_validation_error_two_args() -> None:
    """Passing two arguments raises TypeError."""
    with pytest.raises(TypeError):
        ValidationError("a", "b")  # type: ignore[call-arg]


@pytest.mark.unit
def test_validation_error_is_data_error() -> None:
    """ValidationError inherits from DataError."""
    assert isinstance(ValidationError("x"), DataError)


@pytest.mark.unit
def test_validation_error_is_model_lens_error() -> None:
    """ValidationError inherits from ModelLensError."""
    assert isinstance(ValidationError("x"), ModelLensError)


@pytest.mark.unit
def test_validation_error_is_exception() -> None:
    """ValidationError inherits from Exception."""
    assert isinstance(ValidationError("x"), Exception)


@pytest.mark.unit
def test_validation_error_caught_as_data_error() -> None:
    """ValidationError can be caught as DataError."""
    with pytest.raises(DataError):
        raise ValidationError("x")


@pytest.mark.unit
def test_validation_error_caught_as_model_lens_error() -> None:
    """ValidationError can be caught as ModelLensError."""
    with pytest.raises(ModelLensError):
        raise ValidationError("x")


# ---------------------------------------------------------------------------
# 7. ParseError
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_parse_error_stores_message() -> None:
    """Message string is stored and accessible via str()."""
    exc = ParseError("cannot decode line 3")
    assert str(exc) == "cannot decode line 3"


@pytest.mark.unit
def test_parse_error_args() -> None:
    """Message string is accessible via exc.args[0]."""
    exc = ParseError("cannot decode line 3")
    assert exc.args[0] == "cannot decode line 3"


@pytest.mark.unit
def test_parse_error_zero_args() -> None:
    """Passing no arguments raises TypeError."""
    with pytest.raises(TypeError):
        ParseError()  # type: ignore[call-arg]


@pytest.mark.unit
def test_parse_error_two_args() -> None:
    """Passing two arguments raises TypeError."""
    with pytest.raises(TypeError):
        ParseError("a", "b")  # type: ignore[call-arg]


@pytest.mark.unit
def test_parse_error_is_data_error() -> None:
    """ParseError inherits from DataError."""
    assert isinstance(ParseError("x"), DataError)


@pytest.mark.unit
def test_parse_error_is_model_lens_error() -> None:
    """ParseError inherits from ModelLensError."""
    assert isinstance(ParseError("x"), ModelLensError)


@pytest.mark.unit
def test_parse_error_is_exception() -> None:
    """ParseError inherits from Exception."""
    assert isinstance(ParseError("x"), Exception)


@pytest.mark.unit
def test_parse_error_caught_as_data_error() -> None:
    """ParseError can be caught as DataError."""
    with pytest.raises(DataError):
        raise ParseError("x")


@pytest.mark.unit
def test_parse_error_caught_as_model_lens_error() -> None:
    """ParseError can be caught as ModelLensError."""
    with pytest.raises(ModelLensError):
        raise ParseError("x")


# ---------------------------------------------------------------------------
# 8. OperationError
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_operation_error_stores_message() -> None:
    """Message string is stored and accessible via str()."""
    exc = OperationError("inference call failed")
    assert str(exc) == "inference call failed"


@pytest.mark.unit
def test_operation_error_args() -> None:
    """Message string is accessible via exc.args[0]."""
    exc = OperationError("inference call failed")
    assert exc.args[0] == "inference call failed"


@pytest.mark.unit
def test_operation_error_zero_args() -> None:
    """Passing no arguments raises TypeError."""
    with pytest.raises(TypeError):
        OperationError()  # type: ignore[call-arg]


@pytest.mark.unit
def test_operation_error_two_args() -> None:
    """Passing two arguments raises TypeError."""
    with pytest.raises(TypeError):
        OperationError("a", "b")  # type: ignore[call-arg]


@pytest.mark.unit
def test_operation_error_is_model_lens_error() -> None:
    """OperationError inherits from ModelLensError."""
    assert isinstance(OperationError("x"), ModelLensError)


@pytest.mark.unit
def test_operation_error_is_exception() -> None:
    """OperationError inherits from Exception."""
    assert isinstance(OperationError("x"), Exception)


@pytest.mark.unit
def test_operation_error_caught_as_model_lens_error() -> None:
    """OperationError can be caught as ModelLensError."""
    with pytest.raises(ModelLensError):
        raise OperationError("x")
