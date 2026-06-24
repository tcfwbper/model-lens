# Test Specification: `inference_engine`

## Source File Under Test
`src/model_lens/inference_engine.py`

## Test File
`tests/model_lens/test_inference_engine.py`

---

## `InferenceEngine`

### Type Hierarchy

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_inference_engine_is_abstract` | `unit` | InferenceEngine cannot be instantiated directly. | | `InferenceEngine()` | Raises `TypeError` |
| `test_yolo_inference_engine_is_subclass` | `unit` | YOLOInferenceEngine inherits from InferenceEngine. | | | `issubclass(YOLOInferenceEngine, InferenceEngine)` is `True` |

---

## `YOLOInferenceEngine`

### Happy Path — Construction

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_yolo_engine_construction_loads_model` | `unit` | Construction calls YOLO(model) and stores the loaded model. | Mock `ultralytics.YOLO` to return a fake model object with `.names` attribute (`{0: "person", 1: "car"}`). | `YOLOInferenceEngine(model="yolov8n.pt", confidence_threshold=0.5)` | `YOLO("yolov8n.pt")` called; instance created without error |
| `test_yolo_engine_populates_label_map` | `unit` | Construction populates _label_map from model.names. | Mock `ultralytics.YOLO` to return model with `.names = {0: "cat", 1: "dog"}`. | `YOLOInferenceEngine(model="yolov8n.pt", confidence_threshold=0.5)` | `engine.get_label_map()` returns `{0: "cat", 1: "dog"}` |

### Validation Failures — confidence_threshold

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_yolo_engine_threshold_zero_raises` | `unit` | confidence_threshold of 0.0 raises ConfigurationError. | | `YOLOInferenceEngine(model="m.pt", confidence_threshold=0.0)` | Raises `ConfigurationError` |
| `test_yolo_engine_threshold_negative_raises` | `unit` | Negative confidence_threshold raises ConfigurationError. | | `YOLOInferenceEngine(model="m.pt", confidence_threshold=-0.1)` | Raises `ConfigurationError` |
| `test_yolo_engine_threshold_above_one_raises` | `unit` | confidence_threshold greater than 1.0 raises ConfigurationError. | | `YOLOInferenceEngine(model="m.pt", confidence_threshold=1.5)` | Raises `ConfigurationError` |

### Boundary Values — confidence_threshold

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_yolo_engine_threshold_one_valid` | `unit` | confidence_threshold of 1.0 is accepted (inclusive upper bound). | Mock `ultralytics.YOLO` to return a valid model. | `YOLOInferenceEngine(model="m.pt", confidence_threshold=1.0)` | Instance created without error |
| `test_yolo_engine_threshold_just_above_zero_valid` | `unit` | confidence_threshold of 0.01 is accepted. | Mock `ultralytics.YOLO` to return a valid model. | `YOLOInferenceEngine(model="m.pt", confidence_threshold=0.01)` | Instance created without error |

### Error Propagation

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_yolo_engine_model_load_failure_raises_operation_error` | `unit` | OperationError raised when YOLO() fails to load model. | Mock `ultralytics.YOLO` to raise an exception. | `YOLOInferenceEngine(model="bad.pt", confidence_threshold=0.5)` | Raises `OperationError` |

### Happy Path — detect

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_detect_returns_filtered_results` | `unit` | detect() returns only detections at or above confidence_threshold. | Mock YOLO model. Construct engine with `confidence_threshold=0.5`. Mock `model(frame)` to return results with boxes: one at confidence 0.8 ("person"), one at 0.3 ("car"). Create fake frame as numpy array `(480, 640, 3)` dtype `uint8`. | `engine.detect(frame, target_labels=["person"])` | Returns list with one `DetectionResult` (label="person", confidence=0.8, is_target=True); car (0.3) is filtered out |
| `test_detect_sets_is_target_correctly` | `unit` | is_target is True only when label is in target_labels. | Mock YOLO model. Construct engine with `confidence_threshold=0.25`. Mock inference to return two detections: "person" at 0.9, "car" at 0.7. Create fake frame. | `engine.detect(frame, target_labels=["car"])` | "car" result has `is_target=True`; "person" result has `is_target=False` |
| `test_detect_normalises_bounding_box` | `unit` | Bounding box coordinates are divided by frame dimensions. | Mock YOLO model. Mock inference to return one detection with pixel bbox `[100, 50, 200, 150]` on a frame of shape `(300, 400, 3)`. Construct engine with `confidence_threshold=0.1`. | `engine.detect(frame, target_labels=[])` | Result bounding box values are `[100/400, 50/300, 200/400, 150/300]` i.e. `[0.25, 0.1667, 0.5, 0.5]` |
| `test_detect_empty_when_no_detections` | `unit` | Returns empty list when model produces no boxes. | Mock YOLO model. Mock inference to return results with no boxes (empty/falsy). Create fake frame. | `engine.detect(frame, target_labels=["person"])` | Returns `[]` |
| `test_detect_empty_when_all_below_threshold` | `unit` | Returns empty list when all detections are below threshold. | Mock YOLO model with `confidence_threshold=0.9`. Mock inference to return detections all at confidence 0.5. Create fake frame. | `engine.detect(frame, target_labels=[])` | Returns `[]` |
| `test_detect_includes_detection_at_exact_threshold` | `unit` | Detection with confidence exactly equal to threshold is kept. | Mock YOLO model with `confidence_threshold=0.5`. Mock inference to return one detection at confidence exactly 0.5. Create fake frame. | `engine.detect(frame, target_labels=[])` | Returns list with one `DetectionResult` |

### Ordering — confidence

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_detect_results_sorted_descending_confidence` | `unit` | Results are ordered by descending confidence. | Mock YOLO model with `confidence_threshold=0.1`. Mock inference to return detections at confidences 0.3, 0.9, 0.6. Create fake frame. | `engine.detect(frame, target_labels=[])` | Returned list has confidences in order `[0.9, 0.6, 0.3]` |

### Immutability

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_detect_does_not_mutate_frame` | `unit` | detect() does not modify the input frame array. | Mock YOLO model. Construct engine. Create numpy frame and take a copy before calling detect. | `engine.detect(frame, target_labels=[])` | `numpy.array_equal(frame, original_copy)` is `True` |
| `test_detect_does_not_mutate_target_labels` | `unit` | detect() does not modify the input target_labels list. | Mock YOLO model. Construct engine. Create `labels = ["person", "car"]` and take a copy. | `engine.detect(frame, target_labels=labels)` | `labels == original_copy` |

### Happy Path — get_label_map

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_get_label_map_returns_copy` | `unit` | get_label_map() returns a copy, not the internal reference. | Mock YOLO model with `.names = {0: "a"}`. Construct engine. | Call `engine.get_label_map()` | Returned dict equals `{0: "a"}` and `result is not engine._label_map` |

### Resource Cleanup

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_teardown_sets_model_none` | `unit` | teardown() releases the model reference. | Mock YOLO model. Construct engine. | Call `engine.teardown()` | `engine._model` is `None` |
| `test_teardown_does_not_clear_label_map` | `unit` | teardown() preserves the _label_map. | Mock YOLO model with `.names = {0: "x"}`. Construct engine. | Call `engine.teardown()` | `engine._label_map` is still `{0: "x"}` |
| `test_detect_after_teardown_raises_operation_error` | `unit` | detect() raises OperationError after teardown. | Mock YOLO model. Construct engine. Call `teardown()`. Create fake frame. | `engine.detect(frame, target_labels=[])` | Raises `OperationError` |
| `test_get_label_map_after_teardown_raises_operation_error` | `unit` | get_label_map() raises OperationError after teardown. | Mock YOLO model. Construct engine. Call `teardown()`. | `engine.get_label_map()` | Raises `OperationError` |

### Idempotency

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_teardown_idempotent` | `unit` | Calling teardown() multiple times does not raise. | Mock YOLO model. Construct engine. Call `teardown()` once. | Call `engine.teardown()` a second time | No exception raised |

### Mock / Dependency Interaction

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_detect_wraps_inference_exception_in_operation_error` | `unit` | Runtime inference failure is wrapped in OperationError. | Mock YOLO model. Construct engine. Mock `model(frame)` to raise `RuntimeError`. Create fake frame. | `engine.detect(frame, target_labels=[])` | Raises `OperationError` |

### Concurrent Behaviour

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_detect_serialised_by_lock` | `unit` | Concurrent detect() calls are serialised by the per-instance lock. | Mock YOLO model with a slow inference (use `threading.Event` to control execution order). Construct engine. Launch two threads calling `detect()`. | Two concurrent `detect()` calls | Only one inference runs at a time; both complete without error |
| `test_teardown_serialised_with_detect` | `unit` | teardown() and detect() are serialised by the same lock. | Mock YOLO model. Construct engine. Acquire lock in a thread, then call teardown() from main thread. | `teardown()` while lock held | `teardown()` blocks until lock released, then completes |

---

## `ENGINE_REGISTRY`

### Happy Path — ENGINE_REGISTRY

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_engine_registry_contains_yolo` | `unit` | ENGINE_REGISTRY maps "yolo" to YOLOInferenceEngine. | | Access `ENGINE_REGISTRY` | `ENGINE_REGISTRY["yolo"]` is `YOLOInferenceEngine` |
| `test_engine_registry_is_dict` | `unit` | ENGINE_REGISTRY is a plain dict. | | Access `ENGINE_REGISTRY` | `isinstance(ENGINE_REGISTRY, dict)` is `True` |
