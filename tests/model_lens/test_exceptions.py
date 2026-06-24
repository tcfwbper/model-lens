"""Tests for model_lens.exceptions — exception hierarchy, construction, and catch behaviour."""

from __future__ import annotations

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
# Type Hierarchy
# ---------------------------------------------------------------------------


class TestTypeHierarchy:
    """Verify the exception inheritance tree."""

    def test_model_lens_error_inherits_exception(self) -> None:
        """ModelLensError is a subclass of Exception."""
        assert issubclass(ModelLensError, Exception)

    def test_configuration_error_inherits_model_lens_error(self) -> None:
        """ConfigurationError is a subclass of ModelLensError."""
        assert issubclass(ConfigurationError, ModelLensError)

    def test_hardware_error_inherits_model_lens_error(self) -> None:
        """HardwareError is a subclass of ModelLensError."""
        assert issubclass(HardwareError, ModelLensError)

    def test_device_not_found_error_inherits_hardware_error(self) -> None:
        """DeviceNotFoundError is a subclass of HardwareError."""
        assert issubclass(DeviceNotFoundError, HardwareError)

    def test_data_error_inherits_model_lens_error(self) -> None:
        """DataError is a subclass of ModelLensError."""
        assert issubclass(DataError, ModelLensError)

    def test_validation_error_inherits_data_error(self) -> None:
        """ValidationError is a subclass of DataError."""
        assert issubclass(ValidationError, DataError)

    def test_parse_error_inherits_data_error(self) -> None:
        """ParseError is a subclass of DataError."""
        assert issubclass(ParseError, DataError)

    def test_operation_error_inherits_model_lens_error(self) -> None:
        """OperationError is a subclass of ModelLensError."""
        assert issubclass(OperationError, ModelLensError)


# ---------------------------------------------------------------------------
# Happy Path — Construction
# ---------------------------------------------------------------------------


class TestConstruction:
    """Verify message storage via single-argument constructor."""

    def test_model_lens_error_stores_message(self) -> None:
        """Message is accessible via args[0] and str()."""
        exc = ModelLensError("something failed")
        assert exc.args[0] == "something failed"
        assert str(exc) == "something failed"

    def test_subclass_stores_message(self) -> None:
        """Subclasses inherit the single-message constructor."""
        exc = ValidationError("field is invalid")
        assert exc.args[0] == "field is invalid"
        assert str(exc) == "field is invalid"


# ---------------------------------------------------------------------------
# Validation Failures
# ---------------------------------------------------------------------------


class TestValidationFailures:
    """Verify constructor enforcement — exactly one positional argument required."""

    def test_model_lens_error_no_args(self) -> None:
        """Instantiation with zero arguments raises TypeError."""
        with pytest.raises(TypeError):
            ModelLensError()  # type: ignore[call-arg]

    def test_model_lens_error_extra_args(self) -> None:
        """Instantiation with more than one positional argument raises TypeError."""
        with pytest.raises(TypeError):
            ModelLensError("a", "b")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Catch Behaviour
# ---------------------------------------------------------------------------


class TestCatchBehaviour:
    """Verify that subclass exceptions are caught by their parent handlers."""

    def test_validation_error_caught_by_data_error(self) -> None:
        """ValidationError can be caught by except DataError."""
        with pytest.raises(DataError):
            raise ValidationError("x")

    def test_device_not_found_caught_by_hardware_error(self) -> None:
        """DeviceNotFoundError can be caught by except HardwareError."""
        with pytest.raises(HardwareError):
            raise DeviceNotFoundError("x")

    def test_all_subclasses_caught_by_model_lens_error(self) -> None:
        """All exception subclasses can be caught by except ModelLensError."""
        subclasses = [
            ConfigurationError,
            HardwareError,
            DeviceNotFoundError,
            DataError,
            ValidationError,
            ParseError,
            OperationError,
        ]
        for cls in subclasses:
            with pytest.raises(ModelLensError):
                raise cls("test message")
