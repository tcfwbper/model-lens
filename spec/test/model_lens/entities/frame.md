# Test Specification: `frame`

## Source File Under Test
`src/model_lens/entities/frame.py`

## Test File
`tests/model_lens/entities/test_frame.py`

---

## `Frame`

### Happy Path — Construction

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_frame_stores_fields` | `unit` | Construction stores data, timestamp, and source as provided. | Create a numpy array of shape `(480, 640, 3)` with dtype `uint8` programmatically in the test. | `Frame(data=array, timestamp=1700000000.123, source="local:0")` | Instance fields match provided values |

### Not Immutable

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_frame_allows_field_reassignment` | `unit` | Frame is not frozen; field reassignment does not raise. | Create a valid Frame instance programmatically. | `instance.source = "rtsp://new"` | No exception raised; field updated |

### Read-Only Convention

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_frame_data_not_copied` | `unit` | Frame does not internally copy the data array; it holds a reference. | Create a numpy array and construct a Frame with it. | Compare `frame.data` identity with original array via `frame.data is original_array` | `True` — same object reference |
