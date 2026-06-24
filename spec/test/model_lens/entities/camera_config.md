# Test Specification: `camera_config`

## Source File Under Test
`src/model_lens/entities/camera_config.py`

## Test File
`tests/model_lens/entities/test_camera_config.py`

---

## `CameraConfig`

### Type Hierarchy

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_camera_config_is_abstract` | `unit` | Direct instantiation of CameraConfig raises TypeError. | | `CameraConfig()` | Raises `TypeError` |
| `test_camera_config_inherits_abc` | `unit` | CameraConfig is a subclass of abc.ABC. | | | `issubclass(CameraConfig, abc.ABC)` is `True` |
| `test_local_camera_config_is_subclass` | `unit` | LocalCameraConfig is a subclass of CameraConfig. | | | `issubclass(LocalCameraConfig, CameraConfig)` is `True` |
| `test_rtsp_camera_config_is_subclass` | `unit` | RtspCameraConfig is a subclass of CameraConfig. | | | `issubclass(RtspCameraConfig, CameraConfig)` is `True` |

---

## `LocalCameraConfig`

### Happy Path — Default Construction

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_local_camera_config_default` | `unit` | Default construction uses device_index=0. | | `LocalCameraConfig()` | Instance created with `device_index == 0` |

### Happy Path — Explicit Construction

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_local_camera_config_explicit_index` | `unit` | Construction with explicit device_index stores the value. | | `LocalCameraConfig(device_index=2)` | Instance created with `device_index == 2` |

### Boundary Values — device_index

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_local_camera_config_zero_index` | `unit` | device_index=0 is the minimum valid value. | | `LocalCameraConfig(device_index=0)` | Instance created successfully |
| `test_local_camera_config_negative_index` | `unit` | device_index=-1 raises ValidationError. | | `LocalCameraConfig(device_index=-1)` | Raises `ValidationError`; message includes the invalid value |

### Validation Failures — device_index

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_local_camera_config_negative_large` | `unit` | A large negative device_index raises ValidationError. | | `LocalCameraConfig(device_index=-100)` | Raises `ValidationError` |

### Immutability

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_local_camera_config_frozen` | `unit` | Assigning to device_index on an existing instance raises. | | `instance.device_index = 5` on a valid instance | Raises `FrozenInstanceError` or `dataclasses.FrozenInstanceError` |

---

## `RtspCameraConfig`

### Happy Path — Explicit Construction

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_rtsp_camera_config_valid_url` | `unit` | Construction with a non-empty URL succeeds. | | `RtspCameraConfig(rtsp_url="rtsp://192.168.1.1:554/stream")` | Instance created with `rtsp_url == "rtsp://192.168.1.1:554/stream"` |
| `test_rtsp_camera_config_whitespace_only_url` | `unit` | A whitespace-only URL is accepted (only empty-string check is performed). | | `RtspCameraConfig(rtsp_url="   ")` | Instance created successfully |

### Validation Failures — rtsp_url

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_rtsp_camera_config_empty_url` | `unit` | Empty string raises ValidationError. | | `RtspCameraConfig(rtsp_url="")` | Raises `ValidationError` |
| `test_rtsp_camera_config_default_url` | `unit` | Default construction (empty string default) raises ValidationError. | | `RtspCameraConfig()` | Raises `ValidationError` |

### Immutability

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_rtsp_camera_config_frozen` | `unit` | Assigning to rtsp_url on an existing instance raises. | | `instance.rtsp_url = "new"` on a valid instance | Raises `FrozenInstanceError` or `dataclasses.FrozenInstanceError` |
