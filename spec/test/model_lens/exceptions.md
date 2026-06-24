# Test Specification: `exceptions`

## Source File Under Test
`src/model_lens/exceptions.py`

## Test File
`tests/model_lens/test_exceptions.py`

---

## `ModelLensError`

### Type Hierarchy

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_model_lens_error_inherits_exception` | `unit` | ModelLensError is a subclass of Exception. | | | `issubclass(ModelLensError, Exception)` is `True` |
| `test_configuration_error_inherits_model_lens_error` | `unit` | ConfigurationError is a subclass of ModelLensError. | | | `issubclass(ConfigurationError, ModelLensError)` is `True` |
| `test_hardware_error_inherits_model_lens_error` | `unit` | HardwareError is a subclass of ModelLensError. | | | `issubclass(HardwareError, ModelLensError)` is `True` |
| `test_device_not_found_error_inherits_hardware_error` | `unit` | DeviceNotFoundError is a subclass of HardwareError. | | | `issubclass(DeviceNotFoundError, HardwareError)` is `True` |
| `test_data_error_inherits_model_lens_error` | `unit` | DataError is a subclass of ModelLensError. | | | `issubclass(DataError, ModelLensError)` is `True` |
| `test_validation_error_inherits_data_error` | `unit` | ValidationError is a subclass of DataError. | | | `issubclass(ValidationError, DataError)` is `True` |
| `test_parse_error_inherits_data_error` | `unit` | ParseError is a subclass of DataError. | | | `issubclass(ParseError, DataError)` is `True` |
| `test_operation_error_inherits_model_lens_error` | `unit` | OperationError is a subclass of ModelLensError. | | | `issubclass(OperationError, ModelLensError)` is `True` |

### Happy Path — Construction

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_model_lens_error_stores_message` | `unit` | Message is accessible via args[0] and str(). | | `ModelLensError("something failed")` | `exc.args[0] == "something failed"` and `str(exc) == "something failed"` |
| `test_subclass_stores_message` | `unit` | Subclasses inherit the single-message constructor. | | `ValidationError("field is invalid")` | `exc.args[0] == "field is invalid"` and `str(exc) == "field is invalid"` |

### Validation Failures

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_model_lens_error_no_args` | `unit` | Instantiation with zero arguments raises TypeError. | | `ModelLensError()` | Raises `TypeError` |
| `test_model_lens_error_extra_args` | `unit` | Instantiation with more than one positional argument raises TypeError. | | `ModelLensError("a", "b")` | Raises `TypeError` |

### Catch Behaviour

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_validation_error_caught_by_data_error` | `unit` | ValidationError can be caught by except DataError. | | Raise `ValidationError("x")` | Caught by `except DataError` |
| `test_device_not_found_caught_by_hardware_error` | `unit` | DeviceNotFoundError can be caught by except HardwareError. | | Raise `DeviceNotFoundError("x")` | Caught by `except HardwareError` |
| `test_all_subclasses_caught_by_model_lens_error` | `unit` | All exception subclasses can be caught by except ModelLensError. | | Raise each subclass | All caught by `except ModelLensError` |
