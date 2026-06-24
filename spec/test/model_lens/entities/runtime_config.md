# Test Specification: `runtime_config`

## Source File Under Test
`src/model_lens/entities/runtime_config.py`

## Test File
`tests/model_lens/entities/test_runtime_config.py`

---

## `RuntimeConfig`

### Happy Path — Default Construction

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_runtime_config_defaults` | `unit` | Default construction produces expected defaults. | | `RuntimeConfig()` | `camera` is `LocalCameraConfig(device_index=0)`, `target_labels` is `[]`, `confidence_threshold` is `0.5` |

### Happy Path — Explicit Construction

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_runtime_config_explicit_fields` | `unit` | Explicit construction stores all provided values. | | `RuntimeConfig(camera=RtspCameraConfig(rtsp_url="rtsp://x"), target_labels=["person", "car"], confidence_threshold=0.8)` | All fields match provided values |

### Immutability

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_runtime_config_frozen` | `unit` | Assigning to any field on an existing instance raises. | | `instance.confidence_threshold = 0.9` on a valid instance | Raises `FrozenInstanceError` or `dataclasses.FrozenInstanceError` |

### Atomic Replacement

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_runtime_config_new_instance_does_not_mutate_original` | `unit` | Creating a new RuntimeConfig does not alter an existing instance. | Create `original = RuntimeConfig()` | Create `new = RuntimeConfig(target_labels=["dog"])` | `original.target_labels` remains `[]` |

### Null / Empty Input

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_runtime_config_empty_target_labels` | `unit` | Empty target_labels list is valid. | | `RuntimeConfig(target_labels=[])` | Instance created; `target_labels` is `[]` |
