# Test Specification: `test/model_lens/test_exceptions.md`

## Source File Under Test

`src/model_lens/exceptions.py`

## Test File

`test/model_lens/test_exceptions.py`

## Imports Required

```python
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
```

---

## 1. `ModelLensError`

### 1.1 Happy Path — Construction

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_model_lens_error_stores_message` | `unit` | Message string is stored and accessible via `str()` | `ModelLensError("something went wrong")` | `str(exc) == "something went wrong"` |
| `test_model_lens_error_args` | `unit` | Message string is accessible via `exc.args[0]` | `ModelLensError("something went wrong")` | `exc.args[0] == "something went wrong"` |

### 1.2 Validation Failures

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_model_lens_error_zero_args` | `unit` | Passing no arguments raises `TypeError` | `ModelLensError()` | raises `TypeError` |
| `test_model_lens_error_two_args` | `unit` | Passing two arguments raises `TypeError` | `ModelLensError("a", "b")` | raises `TypeError` |

### 1.3 Type Hierarchy

| Test ID | Category | Description | Expected |
|---|---|---|---|
| `test_model_lens_error_is_exception` | `unit` | `ModelLensError` inherits from `Exception` | `isinstance(ModelLensError("x"), Exception) is True` |

### 1.4 Catch Behaviour

| Test ID | Category | Description | Expected |
|---|---|---|---|
| `test_model_lens_error_caught_as_exception` | `unit` | `ModelLensError` can be caught as `Exception` | `raise ModelLensError("x")` is caught by `except Exception` |

---

## 2. `ConfigurationError`

### 2.1 Happy Path — Construction

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_configuration_error_stores_message` | `unit` | Message string is stored and accessible via `str()` | `ConfigurationError("bad config")` | `str(exc) == "bad config"` |
| `test_configuration_error_args` | `unit` | Message string is accessible via `exc.args[0]` | `ConfigurationError("bad config")` | `exc.args[0] == "bad config"` |

### 2.2 Validation Failures

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_configuration_error_zero_args` | `unit` | Passing no arguments raises `TypeError` | `ConfigurationError()` | raises `TypeError` |
| `test_configuration_error_two_args` | `unit` | Passing two arguments raises `TypeError` | `ConfigurationError("a", "b")` | raises `TypeError` |

### 2.3 Type Hierarchy

| Test ID | Category | Description | Expected |
|---|---|---|---|
| `test_configuration_error_is_model_lens_error` | `unit` | `ConfigurationError` inherits from `ModelLensError` | `isinstance(ConfigurationError("x"), ModelLensError) is True` |
| `test_configuration_error_is_exception` | `unit` | `ConfigurationError` inherits from `Exception` | `isinstance(ConfigurationError("x"), Exception) is True` |

### 2.4 Catch Behaviour

| Test ID | Category | Description | Expected |
|---|---|---|---|
| `test_configuration_error_caught_as_model_lens_error` | `unit` | `ConfigurationError` can be caught as `ModelLensError` | `raise ConfigurationError("x")` is caught by `except ModelLensError` |

---

## 3. `HardwareError`

### 3.1 Happy Path — Construction

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_hardware_error_stores_message` | `unit` | Message string is stored and accessible via `str()` | `HardwareError("camera failed")` | `str(exc) == "camera failed"` |
| `test_hardware_error_args` | `unit` | Message string is accessible via `exc.args[0]` | `HardwareError("camera failed")` | `exc.args[0] == "camera failed"` |

### 3.2 Validation Failures

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_hardware_error_zero_args` | `unit` | Passing no arguments raises `TypeError` | `HardwareError()` | raises `TypeError` |
| `test_hardware_error_two_args` | `unit` | Passing two arguments raises `TypeError` | `HardwareError("a", "b")` | raises `TypeError` |

### 3.3 Type Hierarchy

| Test ID | Category | Description | Expected |
|---|---|---|---|
| `test_hardware_error_is_model_lens_error` | `unit` | `HardwareError` inherits from `ModelLensError` | `isinstance(HardwareError("x"), ModelLensError) is True` |
| `test_hardware_error_is_exception` | `unit` | `HardwareError` inherits from `Exception` | `isinstance(HardwareError("x"), Exception) is True` |

### 3.4 Catch Behaviour

| Test ID | Category | Description | Expected |
|---|---|---|---|
| `test_hardware_error_caught_as_model_lens_error` | `unit` | `HardwareError` can be caught as `ModelLensError` | `raise HardwareError("x")` is caught by `except ModelLensError` |

---

## 4. `DeviceNotFoundError`

### 4.1 Happy Path — Construction

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_device_not_found_error_stores_message` | `unit` | Message string is stored and accessible via `str()` | `DeviceNotFoundError("device 2 not found")` | `str(exc) == "device 2 not found"` |
| `test_device_not_found_error_args` | `unit` | Message string is accessible via `exc.args[0]` | `DeviceNotFoundError("device 2 not found")` | `exc.args[0] == "device 2 not found"` |

### 4.2 Validation Failures

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_device_not_found_error_zero_args` | `unit` | Passing no arguments raises `TypeError` | `DeviceNotFoundError()` | raises `TypeError` |
| `test_device_not_found_error_two_args` | `unit` | Passing two arguments raises `TypeError` | `DeviceNotFoundError("a", "b")` | raises `TypeError` |

### 4.3 Type Hierarchy

| Test ID | Category | Description | Expected |
|---|---|---|---|
| `test_device_not_found_error_is_hardware_error` | `unit` | `DeviceNotFoundError` inherits from `HardwareError` | `isinstance(DeviceNotFoundError("x"), HardwareError) is True` |
| `test_device_not_found_error_is_model_lens_error` | `unit` | `DeviceNotFoundError` inherits from `ModelLensError` | `isinstance(DeviceNotFoundError("x"), ModelLensError) is True` |
| `test_device_not_found_error_is_exception` | `unit` | `DeviceNotFoundError` inherits from `Exception` | `isinstance(DeviceNotFoundError("x"), Exception) is True` |

### 4.4 Catch Behaviour

| Test ID | Category | Description | Expected |
|---|---|---|---|
| `test_device_not_found_error_caught_as_hardware_error` | `unit` | `DeviceNotFoundError` can be caught as `HardwareError` | `raise DeviceNotFoundError("x")` is caught by `except HardwareError` |
| `test_device_not_found_error_caught_as_model_lens_error` | `unit` | `DeviceNotFoundError` can be caught as `ModelLensError` | `raise DeviceNotFoundError("x")` is caught by `except ModelLensError` |

---

## 5. `DataError`

### 5.1 Happy Path — Construction

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_data_error_stores_message` | `unit` | Message string is stored and accessible via `str()` | `DataError("malformed data")` | `str(exc) == "malformed data"` |
| `test_data_error_args` | `unit` | Message string is accessible via `exc.args[0]` | `DataError("malformed data")` | `exc.args[0] == "malformed data"` |

### 5.2 Validation Failures

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_data_error_zero_args` | `unit` | Passing no arguments raises `TypeError` | `DataError()` | raises `TypeError` |
| `test_data_error_two_args` | `unit` | Passing two arguments raises `TypeError` | `DataError("a", "b")` | raises `TypeError` |

### 5.3 Type Hierarchy

| Test ID | Category | Description | Expected |
|---|---|---|---|
| `test_data_error_is_model_lens_error` | `unit` | `DataError` inherits from `ModelLensError` | `isinstance(DataError("x"), ModelLensError) is True` |
| `test_data_error_is_exception` | `unit` | `DataError` inherits from `Exception` | `isinstance(DataError("x"), Exception) is True` |

### 5.4 Catch Behaviour

| Test ID | Category | Description | Expected |
|---|---|---|---|
| `test_data_error_caught_as_model_lens_error` | `unit` | `DataError` can be caught as `ModelLensError` | `raise DataError("x")` is caught by `except ModelLensError` |

---

## 6. `ValidationError`

### 6.1 Happy Path — Construction

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_validation_error_stores_message` | `unit` | Message string is stored and accessible via `str()` | `ValidationError("value out of range")` | `str(exc) == "value out of range"` |
| `test_validation_error_args` | `unit` | Message string is accessible via `exc.args[0]` | `ValidationError("value out of range")` | `exc.args[0] == "value out of range"` |

### 6.2 Validation Failures

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_validation_error_zero_args` | `unit` | Passing no arguments raises `TypeError` | `ValidationError()` | raises `TypeError` |
| `test_validation_error_two_args` | `unit` | Passing two arguments raises `TypeError` | `ValidationError("a", "b")` | raises `TypeError` |

### 6.3 Type Hierarchy

| Test ID | Category | Description | Expected |
|---|---|---|---|
| `test_validation_error_is_data_error` | `unit` | `ValidationError` inherits from `DataError` | `isinstance(ValidationError("x"), DataError) is True` |
| `test_validation_error_is_model_lens_error` | `unit` | `ValidationError` inherits from `ModelLensError` | `isinstance(ValidationError("x"), ModelLensError) is True` |
| `test_validation_error_is_exception` | `unit` | `ValidationError` inherits from `Exception` | `isinstance(ValidationError("x"), Exception) is True` |

### 6.4 Catch Behaviour

| Test ID | Category | Description | Expected |
|---|---|---|---|
| `test_validation_error_caught_as_data_error` | `unit` | `ValidationError` can be caught as `DataError` | `raise ValidationError("x")` is caught by `except DataError` |
| `test_validation_error_caught_as_model_lens_error` | `unit` | `ValidationError` can be caught as `ModelLensError` | `raise ValidationError("x")` is caught by `except ModelLensError` |

---

## 7. `ParseError`

### 7.1 Happy Path — Construction

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_parse_error_stores_message` | `unit` | Message string is stored and accessible via `str()` | `ParseError("cannot decode line 3")` | `str(exc) == "cannot decode line 3"` |
| `test_parse_error_args` | `unit` | Message string is accessible via `exc.args[0]` | `ParseError("cannot decode line 3")` | `exc.args[0] == "cannot decode line 3"` |

### 7.2 Validation Failures

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_parse_error_zero_args` | `unit` | Passing no arguments raises `TypeError` | `ParseError()` | raises `TypeError` |
| `test_parse_error_two_args` | `unit` | Passing two arguments raises `TypeError` | `ParseError("a", "b")` | raises `TypeError` |

### 7.3 Type Hierarchy

| Test ID | Category | Description | Expected |
|---|---|---|---|
| `test_parse_error_is_data_error` | `unit` | `ParseError` inherits from `DataError` | `isinstance(ParseError("x"), DataError) is True` |
| `test_parse_error_is_model_lens_error` | `unit` | `ParseError` inherits from `ModelLensError` | `isinstance(ParseError("x"), ModelLensError) is True` |
| `test_parse_error_is_exception` | `unit` | `ParseError` inherits from `Exception` | `isinstance(ParseError("x"), Exception) is True` |

### 7.4 Catch Behaviour

| Test ID | Category | Description | Expected |
|---|---|---|---|
| `test_parse_error_caught_as_data_error` | `unit` | `ParseError` can be caught as `DataError` | `raise ParseError("x")` is caught by `except DataError` |
| `test_parse_error_caught_as_model_lens_error` | `unit` | `ParseError` can be caught as `ModelLensError` | `raise ParseError("x")` is caught by `except ModelLensError` |

---

## 8. `OperationError`

### 8.1 Happy Path — Construction

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_operation_error_stores_message` | `unit` | Message string is stored and accessible via `str()` | `OperationError("inference call failed")` | `str(exc) == "inference call failed"` |
| `test_operation_error_args` | `unit` | Message string is accessible via `exc.args[0]` | `OperationError("inference call failed")` | `exc.args[0] == "inference call failed"` |

### 8.2 Validation Failures

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_operation_error_zero_args` | `unit` | Passing no arguments raises `TypeError` | `OperationError()` | raises `TypeError` |
| `test_operation_error_two_args` | `unit` | Passing two arguments raises `TypeError` | `OperationError("a", "b")` | raises `TypeError` |

### 8.3 Type Hierarchy

| Test ID | Category | Description | Expected |
|---|---|---|---|
| `test_operation_error_is_model_lens_error` | `unit` | `OperationError` inherits from `ModelLensError` | `isinstance(OperationError("x"), ModelLensError) is True` |
| `test_operation_error_is_exception` | `unit` | `OperationError` inherits from `Exception` | `isinstance(OperationError("x"), Exception) is True` |

### 8.4 Catch Behaviour

| Test ID | Category | Description | Expected |
|---|---|---|---|
| `test_operation_error_caught_as_model_lens_error` | `unit` | `OperationError` can be caught as `ModelLensError` | `raise OperationError("x")` is caught by `except ModelLensError` |

---

## Summary Table

| Entity | Test Count (approx.) | unit | e2e | race | Key Concerns |
|---|---|---|---|---|---|
| `ModelLensError` | 6 | 6 | 0 | 0 | message stored, args, zero/two args, isinstance, catch-as-Exception |
| `ConfigurationError` | 6 | 6 | 0 | 0 | message stored, args, zero/two args, isinstance chain, catch-as-parent |
| `HardwareError` | 6 | 6 | 0 | 0 | message stored, args, zero/two args, isinstance chain, catch-as-parent |
| `DeviceNotFoundError` | 8 | 8 | 0 | 0 | message stored, args, zero/two args, isinstance chain (3 levels), catch-as-both-parents |
| `DataError` | 6 | 6 | 0 | 0 | message stored, args, zero/two args, isinstance chain, catch-as-parent |
| `ValidationError` | 8 | 8 | 0 | 0 | message stored, args, zero/two args, isinstance chain (3 levels), catch-as-both-parents |
| `ParseError` | 8 | 8 | 0 | 0 | message stored, args, zero/two args, isinstance chain (3 levels), catch-as-both-parents |
| `OperationError` | 6 | 6 | 0 | 0 | message stored, args, zero/two args, isinstance chain, catch-as-parent |
