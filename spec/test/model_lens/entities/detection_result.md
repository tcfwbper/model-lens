# Test Specification: `detection_result`

## Source File Under Test
`src/model_lens/entities/detection_result.py`

## Test File
`tests/model_lens/entities/test_detection_result.py`

---

## `DetectionResult`

### Happy Path — Construction

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_detection_result_valid` | `unit` | Construction with valid fields stores all values. | | `DetectionResult(label="person", confidence=0.95, bounding_box=(0.1, 0.2, 0.5, 0.8), is_target=True)` | Instance created with all fields matching input |
| `test_detection_result_confidence_one` | `unit` | confidence=1.0 is the inclusive upper bound and valid. | | `DetectionResult(label="car", confidence=1.0, bounding_box=(0.0, 0.0, 1.0, 1.0), is_target=False)` | Instance created successfully |
| `test_detection_result_is_target_false` | `unit` | is_target=False is stored correctly. | | `DetectionResult(label="cat", confidence=0.5, bounding_box=(0.0, 0.0, 0.5, 0.5), is_target=False)` | `instance.is_target` is `False` |

### Boundary Values — confidence

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_detection_result_confidence_just_above_zero` | `unit` | confidence just above zero is valid. | | `DetectionResult(label="dog", confidence=0.001, bounding_box=(0.0, 0.0, 0.5, 0.5), is_target=False)` | Instance created successfully |
| `test_detection_result_confidence_zero` | `unit` | confidence=0.0 is invalid (exclusive lower bound). | | `DetectionResult(label="dog", confidence=0.0, bounding_box=(0.0, 0.0, 0.5, 0.5), is_target=False)` | Raises `ValidationError` |
| `test_detection_result_confidence_above_one` | `unit` | confidence > 1.0 is invalid. | | `DetectionResult(label="dog", confidence=1.1, bounding_box=(0.0, 0.0, 0.5, 0.5), is_target=False)` | Raises `ValidationError` |
| `test_detection_result_confidence_negative` | `unit` | Negative confidence is invalid. | | `DetectionResult(label="dog", confidence=-0.5, bounding_box=(0.0, 0.0, 0.5, 0.5), is_target=False)` | Raises `ValidationError` |

### Validation Failures — label

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_detection_result_empty_label` | `unit` | Empty label string raises ValidationError. | | `DetectionResult(label="", confidence=0.9, bounding_box=(0.0, 0.0, 0.5, 0.5), is_target=False)` | Raises `ValidationError` |

### Immutability

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_detection_result_frozen` | `unit` | Assigning to any field on an existing instance raises. | | `instance.label = "new"` on a valid instance | Raises `FrozenInstanceError` or `dataclasses.FrozenInstanceError` |
