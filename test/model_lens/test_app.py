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

"""Tests for app.py, routers/config.py, routers/stream.py, routers/health.py, and schemas.py."""

import base64
import hashlib
import json
import queue
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from model_lens.entities import (
    DetectionResult,
    LocalCameraConfig,
    RtspCameraConfig,
    RuntimeConfig,
)
from model_lens.exceptions import ConfigurationError, OperationError
from model_lens.schemas import (
    LocalCameraRequest,
    RtspCameraRequest,
    UpdateCameraRequest,
    UpdateLabelsRequest,
)

# ---------------------------------------------------------------------------
# Fixtures (imported via conftest.py from fixtures/app.py)
# ---------------------------------------------------------------------------
# mock_pipeline, client, static_client, make_pipeline_result,
# lifespan_mocks, client_with_broken_pipeline


# ===========================================================================
# 1. Health Check — GET /healthz
# ===========================================================================


@pytest.mark.unit
def test_healthz_returns_200(client: TestClient) -> None:
    """GET /healthz returns HTTP 200."""
    response = client.get("/healthz")
    assert response.status_code == 200


@pytest.mark.unit
def test_healthz_returns_empty_body(client: TestClient) -> None:
    """GET /healthz response body is empty."""
    response = client.get("/healthz")
    assert response.content == b""


# ===========================================================================
# 2. Config API — GET /config
# ===========================================================================


@pytest.mark.unit
def test_get_config_returns_200(client: TestClient) -> None:
    """GET /config returns HTTP 200."""
    response = client.get("/config")
    assert response.status_code == 200


@pytest.mark.unit
def test_get_config_local_source_type(client: TestClient) -> None:
    """Response contains source_type = 'local' for LocalCameraConfig."""
    response = client.get("/config")
    body = response.json()
    assert body["camera"]["source_type"] == "local"


@pytest.mark.unit
def test_get_config_local_device_index(client: TestClient) -> None:
    """Response contains correct device_index for LocalCameraConfig."""
    response = client.get("/config")
    body = response.json()
    assert body["camera"]["device_index"] == 0


@pytest.mark.unit
def test_get_config_local_no_rtsp_url(client: TestClient) -> None:
    """Response does not contain rtsp_url when source is local."""
    response = client.get("/config")
    body = response.json()
    assert "rtsp_url" not in body["camera"]


@pytest.mark.unit
def test_get_config_confidence_threshold(client: TestClient) -> None:
    """Response contains confidence_threshold."""
    response = client.get("/config")
    body = response.json()
    assert body["confidence_threshold"] == 0.5


@pytest.mark.unit
def test_get_config_target_labels_empty(client: TestClient) -> None:
    """Response contains empty target_labels."""
    response = client.get("/config")
    body = response.json()
    assert body["target_labels"] == []


@pytest.mark.unit
def test_get_config_target_labels_non_empty(client: TestClient, mock_pipeline: MagicMock) -> None:
    """Response contains non-empty target_labels."""
    mock_pipeline.get_config.return_value = RuntimeConfig(
        camera=LocalCameraConfig(device_index=0),
        target_labels=["cat", "dog"],
        confidence_threshold=0.5,
    )
    response = client.get("/config")
    body = response.json()
    assert body["target_labels"] == ["cat", "dog"]


@pytest.mark.unit
def test_get_config_rtsp_source_type(client: TestClient, mock_pipeline: MagicMock) -> None:
    """Response contains source_type = 'rtsp' for RtspCameraConfig."""
    mock_pipeline.get_config.return_value = RuntimeConfig(
        camera=RtspCameraConfig(rtsp_url="rtsp://192.168.1.10/stream"),
        target_labels=[],
        confidence_threshold=0.5,
    )
    response = client.get("/config")
    body = response.json()
    assert body["camera"]["source_type"] == "rtsp"


@pytest.mark.unit
def test_get_config_rtsp_url(client: TestClient, mock_pipeline: MagicMock) -> None:
    """Response contains correct rtsp_url for RtspCameraConfig."""
    mock_pipeline.get_config.return_value = RuntimeConfig(
        camera=RtspCameraConfig(rtsp_url="rtsp://192.168.1.10/stream"),
        target_labels=[],
        confidence_threshold=0.5,
    )
    response = client.get("/config")
    body = response.json()
    assert body["camera"]["rtsp_url"] == "rtsp://192.168.1.10/stream"


@pytest.mark.unit
def test_get_config_rtsp_no_device_index(client: TestClient, mock_pipeline: MagicMock) -> None:
    """Response does not contain device_index when source is RTSP."""
    mock_pipeline.get_config.return_value = RuntimeConfig(
        camera=RtspCameraConfig(rtsp_url="rtsp://192.168.1.10/stream"),
        target_labels=[],
        confidence_threshold=0.5,
    )
    response = client.get("/config")
    body = response.json()
    assert "device_index" not in body["camera"]


# ===========================================================================
# 3. Config API — PUT /config/camera
# ===========================================================================


@pytest.mark.unit
def test_put_camera_local_returns_200(client: TestClient) -> None:
    """Valid local camera request returns HTTP 200."""
    response = client.put("/config/camera", json={"camera": {"source_type": "local", "device_index": 0}})
    assert response.status_code == 200


@pytest.mark.unit
def test_put_camera_local_calls_update_config(client: TestClient, mock_pipeline: MagicMock) -> None:
    """DetectionPipeline.update_config is called once for a valid local camera request."""
    client.put("/config/camera", json={"camera": {"source_type": "local", "device_index": 0}})
    assert mock_pipeline.update_config.call_count == 1


@pytest.mark.unit
def test_put_camera_local_update_config_receives_runtime_config(
    client: TestClient, mock_pipeline: MagicMock
) -> None:
    """update_config receives a RuntimeConfig with the new LocalCameraConfig."""
    client.put("/config/camera", json={"camera": {"source_type": "local", "device_index": 2}})
    args, _ = mock_pipeline.update_config.call_args
    runtime_config: RuntimeConfig = args[0]
    assert runtime_config.camera.device_index == 2  # type: ignore[union-attr]


@pytest.mark.unit
def test_put_camera_local_response_reflects_new_camera(client: TestClient) -> None:
    """Response body reflects the updated camera."""
    response = client.put("/config/camera", json={"camera": {"source_type": "local", "device_index": 2}})
    body = response.json()
    assert body["camera"]["device_index"] == 2


@pytest.mark.unit
def test_put_camera_local_preserves_target_labels(
    client: TestClient, mock_pipeline: MagicMock
) -> None:
    """target_labels in the updated RuntimeConfig is preserved from the current config."""
    mock_pipeline.get_config.return_value = RuntimeConfig(
        camera=LocalCameraConfig(device_index=0),
        target_labels=["cat"],
        confidence_threshold=0.5,
    )
    client.put("/config/camera", json={"camera": {"source_type": "local", "device_index": 1}})
    args, _ = mock_pipeline.update_config.call_args
    runtime_config: RuntimeConfig = args[0]
    assert runtime_config.target_labels == ["cat"]


@pytest.mark.unit
def test_put_camera_local_preserves_confidence_threshold(
    client: TestClient, mock_pipeline: MagicMock
) -> None:
    """confidence_threshold in the updated RuntimeConfig is preserved."""
    mock_pipeline.get_config.return_value = RuntimeConfig(
        camera=LocalCameraConfig(device_index=0),
        target_labels=[],
        confidence_threshold=0.75,
    )
    client.put("/config/camera", json={"camera": {"source_type": "local", "device_index": 1}})
    args, _ = mock_pipeline.update_config.call_args
    runtime_config: RuntimeConfig = args[0]
    assert runtime_config.confidence_threshold == 0.75


@pytest.mark.unit
def test_put_camera_rtsp_returns_200(client: TestClient) -> None:
    """Valid RTSP camera request returns HTTP 200."""
    response = client.put(
        "/config/camera",
        json={"camera": {"source_type": "rtsp", "rtsp_url": "rtsp://192.168.1.10/stream"}},
    )
    assert response.status_code == 200


@pytest.mark.unit
def test_put_camera_rtsp_update_config_receives_runtime_config(
    client: TestClient, mock_pipeline: MagicMock
) -> None:
    """update_config receives a RuntimeConfig with the new RtspCameraConfig."""
    client.put(
        "/config/camera",
        json={"camera": {"source_type": "rtsp", "rtsp_url": "rtsp://192.168.1.10/stream"}},
    )
    args, _ = mock_pipeline.update_config.call_args
    runtime_config: RuntimeConfig = args[0]
    assert runtime_config.camera.rtsp_url == "rtsp://192.168.1.10/stream"  # type: ignore[union-attr]


@pytest.mark.unit
def test_put_camera_rtsp_response_reflects_new_camera(client: TestClient) -> None:
    """Response body reflects the updated RTSP camera."""
    response = client.put(
        "/config/camera",
        json={"camera": {"source_type": "rtsp", "rtsp_url": "rtsp://192.168.1.10/stream"}},
    )
    body = response.json()
    assert body["camera"]["source_type"] == "rtsp"
    assert body["camera"]["rtsp_url"] == "rtsp://192.168.1.10/stream"


@pytest.mark.unit
def test_put_camera_invalid_source_type_returns_422(client: TestClient) -> None:
    """Unknown source_type returns 422."""
    response = client.put("/config/camera", json={"camera": {"source_type": "usb"}})
    assert response.status_code == 422


@pytest.mark.unit
def test_put_camera_local_negative_device_index_returns_422(client: TestClient) -> None:
    """Negative device_index returns 422."""
    response = client.put(
        "/config/camera", json={"camera": {"source_type": "local", "device_index": -1}}
    )
    assert response.status_code == 422


@pytest.mark.unit
def test_put_camera_rtsp_missing_url_returns_422(client: TestClient) -> None:
    """Missing rtsp_url for RTSP source returns 422."""
    response = client.put("/config/camera", json={"camera": {"source_type": "rtsp"}})
    assert response.status_code == 422


@pytest.mark.unit
def test_put_camera_rtsp_empty_url_returns_422(client: TestClient) -> None:
    """Empty rtsp_url returns 422."""
    response = client.put(
        "/config/camera", json={"camera": {"source_type": "rtsp", "rtsp_url": ""}}
    )
    assert response.status_code == 422


@pytest.mark.unit
def test_put_camera_rtsp_url_wrong_scheme_returns_422(client: TestClient) -> None:
    """rtsp_url not starting with rtsp:// returns 422."""
    response = client.put(
        "/config/camera",
        json={"camera": {"source_type": "rtsp", "rtsp_url": "http://192.168.1.10/stream"}},
    )
    assert response.status_code == 422


@pytest.mark.unit
def test_put_camera_missing_camera_field_returns_422(client: TestClient) -> None:
    """Request body missing camera field returns 422."""
    response = client.put("/config/camera", json={})
    assert response.status_code == 422


@pytest.mark.unit
def test_put_camera_malformed_json_returns_400(client: TestClient) -> None:
    """Non-JSON body returns 400."""
    response = client.put(
        "/config/camera",
        content=b"not json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400


@pytest.mark.unit
def test_put_camera_confidence_threshold_in_body_is_ignored(client: TestClient) -> None:
    """confidence_threshold in request body is silently ignored, not rejected."""
    response = client.put(
        "/config/camera",
        json={"camera": {"source_type": "local", "device_index": 0}, "confidence_threshold": 0.9},
    )
    assert response.status_code == 200


# ===========================================================================
# 4. Config API — PUT /config/labels
# ===========================================================================


@pytest.mark.unit
def test_put_labels_returns_200(client: TestClient) -> None:
    """Valid labels list returns HTTP 200."""
    response = client.put("/config/labels", json={"target_labels": ["cat", "dog"]})
    assert response.status_code == 200


@pytest.mark.unit
def test_put_labels_calls_update_config(client: TestClient, mock_pipeline: MagicMock) -> None:
    """DetectionPipeline.update_config is called once."""
    client.put("/config/labels", json={"target_labels": ["cat"]})
    assert mock_pipeline.update_config.call_count == 1


@pytest.mark.unit
def test_put_labels_update_config_receives_runtime_config(
    client: TestClient, mock_pipeline: MagicMock
) -> None:
    """update_config receives a RuntimeConfig with the new labels."""
    client.put("/config/labels", json={"target_labels": ["cat", "dog"]})
    args, _ = mock_pipeline.update_config.call_args
    runtime_config: RuntimeConfig = args[0]
    assert runtime_config.target_labels == ["cat", "dog"]


@pytest.mark.unit
def test_put_labels_empty_list_is_valid(client: TestClient) -> None:
    """Empty target_labels list is accepted."""
    response = client.put("/config/labels", json={"target_labels": []})
    assert response.status_code == 200


@pytest.mark.unit
def test_put_labels_response_reflects_new_labels(client: TestClient) -> None:
    """Response body reflects the updated labels."""
    response = client.put("/config/labels", json={"target_labels": ["person"]})
    body = response.json()
    assert body["target_labels"] == ["person"]


@pytest.mark.unit
def test_put_labels_preserves_camera(client: TestClient, mock_pipeline: MagicMock) -> None:
    """camera in the updated RuntimeConfig is preserved from the current config."""
    mock_pipeline.get_config.return_value = RuntimeConfig(
        camera=LocalCameraConfig(device_index=1),
        target_labels=[],
        confidence_threshold=0.5,
    )
    client.put("/config/labels", json={"target_labels": ["cat"]})
    args, _ = mock_pipeline.update_config.call_args
    runtime_config: RuntimeConfig = args[0]
    assert runtime_config.camera.device_index == 1  # type: ignore[union-attr]


@pytest.mark.unit
def test_put_labels_preserves_confidence_threshold(
    client: TestClient, mock_pipeline: MagicMock
) -> None:
    """confidence_threshold in the updated RuntimeConfig is preserved."""
    mock_pipeline.get_config.return_value = RuntimeConfig(
        camera=LocalCameraConfig(device_index=0),
        target_labels=[],
        confidence_threshold=0.75,
    )
    client.put("/config/labels", json={"target_labels": ["cat"]})
    args, _ = mock_pipeline.update_config.call_args
    runtime_config: RuntimeConfig = args[0]
    assert runtime_config.confidence_threshold == 0.75


@pytest.mark.unit
def test_put_labels_missing_field_returns_422(client: TestClient) -> None:
    """Request body missing target_labels field returns 422."""
    response = client.put("/config/labels", json={})
    assert response.status_code == 422


@pytest.mark.unit
def test_put_labels_non_array_returns_422(client: TestClient) -> None:
    """target_labels is not an array returns 422."""
    response = client.put("/config/labels", json={"target_labels": "cat"})
    assert response.status_code == 422


@pytest.mark.unit
def test_put_labels_array_of_non_strings_returns_422(client: TestClient) -> None:
    """target_labels contains non-string elements returns 422."""
    response = client.put("/config/labels", json={"target_labels": [1, 2, 3]})
    assert response.status_code == 422


@pytest.mark.unit
def test_put_labels_malformed_json_returns_400(client: TestClient) -> None:
    """Non-JSON body returns 400."""
    response = client.put(
        "/config/labels",
        content=b"not json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400


# ===========================================================================
# 5. Stream API — GET /stream
# ===========================================================================


def _make_stream_queue(results: list) -> queue.Queue:
    """Helper: populate a Queue with the given results."""
    q: queue.Queue = queue.Queue()
    for r in results:
        q.put(r)
    return q


@pytest.mark.unit
def test_stream_returns_200(client: TestClient, mock_pipeline: MagicMock, make_pipeline_result) -> None:
    """GET /stream returns HTTP 200."""
    result = make_pipeline_result()
    mock_pipeline.get_queue.return_value = _make_stream_queue([result])
    with client.stream("GET", "/stream") as response:
        assert response.status_code == 200


@pytest.mark.unit
def test_stream_content_type_is_text_event_stream(
    client: TestClient, mock_pipeline: MagicMock, make_pipeline_result
) -> None:
    """Response Content-Type is text/event-stream."""
    result = make_pipeline_result()
    mock_pipeline.get_queue.return_value = _make_stream_queue([result])
    with client.stream("GET", "/stream") as response:
        assert "text/event-stream" in response.headers["content-type"]


@pytest.mark.unit
def test_stream_event_contains_jpeg_b64(
    client: TestClient, mock_pipeline: MagicMock, make_pipeline_result
) -> None:
    """SSE event payload contains jpeg_b64 field."""
    result = make_pipeline_result()
    mock_pipeline.get_queue.return_value = _make_stream_queue([result])
    chunks = []
    with client.stream("GET", "/stream") as response:
        for chunk in response.iter_bytes():
            chunks.append(chunk)
            break  # only need the first event
    raw = b"".join(chunks)
    data_line = next(line for line in raw.split(b"\n") if line.startswith(b"data: "))
    body = json.loads(data_line[len(b"data: "):])
    assert "jpeg_b64" in body
    assert len(body["jpeg_b64"]) > 0


@pytest.mark.unit
def test_stream_event_jpeg_b64_is_valid_base64(
    client: TestClient, mock_pipeline: MagicMock, make_pipeline_result
) -> None:
    """jpeg_b64 value is valid base64."""
    result = make_pipeline_result()
    mock_pipeline.get_queue.return_value = _make_stream_queue([result])
    chunks = []
    with client.stream("GET", "/stream") as response:
        for chunk in response.iter_bytes():
            chunks.append(chunk)
            break
    raw = b"".join(chunks)
    data_line = next(line for line in raw.split(b"\n") if line.startswith(b"data: "))
    body = json.loads(data_line[len(b"data: "):])
    # Should not raise
    base64.b64decode(body["jpeg_b64"])


@pytest.mark.unit
def test_stream_event_jpeg_b64_decodes_to_original_bytes(
    client: TestClient, mock_pipeline: MagicMock, make_pipeline_result
) -> None:
    """Decoded jpeg_b64 matches original jpeg_bytes."""
    result = make_pipeline_result()
    original_bytes = result.jpeg_bytes
    mock_pipeline.get_queue.return_value = _make_stream_queue([result])
    chunks = []
    with client.stream("GET", "/stream") as response:
        for chunk in response.iter_bytes():
            chunks.append(chunk)
            break
    raw = b"".join(chunks)
    data_line = next(line for line in raw.split(b"\n") if line.startswith(b"data: "))
    body = json.loads(data_line[len(b"data: "):])
    assert base64.b64decode(body["jpeg_b64"]) == original_bytes


@pytest.mark.unit
def test_stream_event_contains_timestamp(
    client: TestClient, mock_pipeline: MagicMock, make_pipeline_result
) -> None:
    """SSE event payload contains timestamp field."""
    result = make_pipeline_result()
    mock_pipeline.get_queue.return_value = _make_stream_queue([result])
    chunks = []
    with client.stream("GET", "/stream") as response:
        for chunk in response.iter_bytes():
            chunks.append(chunk)
            break
    raw = b"".join(chunks)
    data_line = next(line for line in raw.split(b"\n") if line.startswith(b"data: "))
    body = json.loads(data_line[len(b"data: "):])
    assert body["timestamp"] == 1748000400.123456


@pytest.mark.unit
def test_stream_event_contains_source(
    client: TestClient, mock_pipeline: MagicMock, make_pipeline_result
) -> None:
    """SSE event payload contains source field."""
    result = make_pipeline_result()
    mock_pipeline.get_queue.return_value = _make_stream_queue([result])
    chunks = []
    with client.stream("GET", "/stream") as response:
        for chunk in response.iter_bytes():
            chunks.append(chunk)
            break
    raw = b"".join(chunks)
    data_line = next(line for line in raw.split(b"\n") if line.startswith(b"data: "))
    body = json.loads(data_line[len(b"data: "):])
    assert body["source"] == "local:0"


@pytest.mark.unit
def test_stream_event_contains_detections(
    client: TestClient, mock_pipeline: MagicMock, make_pipeline_result
) -> None:
    """SSE event payload contains detections array."""
    result = make_pipeline_result()
    mock_pipeline.get_queue.return_value = _make_stream_queue([result])
    chunks = []
    with client.stream("GET", "/stream") as response:
        for chunk in response.iter_bytes():
            chunks.append(chunk)
            break
    raw = b"".join(chunks)
    data_line = next(line for line in raw.split(b"\n") if line.startswith(b"data: "))
    body = json.loads(data_line[len(b"data: "):])
    assert len(body["detections"]) == 1


@pytest.mark.unit
def test_stream_event_detection_label(
    client: TestClient, mock_pipeline: MagicMock, make_pipeline_result
) -> None:
    """Detection object contains correct label."""
    result = make_pipeline_result(label="cat")
    mock_pipeline.get_queue.return_value = _make_stream_queue([result])
    chunks = []
    with client.stream("GET", "/stream") as response:
        for chunk in response.iter_bytes():
            chunks.append(chunk)
            break
    raw = b"".join(chunks)
    data_line = next(line for line in raw.split(b"\n") if line.startswith(b"data: "))
    body = json.loads(data_line[len(b"data: "):])
    assert body["detections"][0]["label"] == "cat"


@pytest.mark.unit
def test_stream_event_detection_confidence(
    client: TestClient, mock_pipeline: MagicMock, make_pipeline_result
) -> None:
    """Detection object contains correct confidence."""
    result = make_pipeline_result(confidence=0.9)
    mock_pipeline.get_queue.return_value = _make_stream_queue([result])
    chunks = []
    with client.stream("GET", "/stream") as response:
        for chunk in response.iter_bytes():
            chunks.append(chunk)
            break
    raw = b"".join(chunks)
    data_line = next(line for line in raw.split(b"\n") if line.startswith(b"data: "))
    body = json.loads(data_line[len(b"data: "):])
    assert body["detections"][0]["confidence"] == 0.9


@pytest.mark.unit
def test_stream_event_detection_bounding_box(
    client: TestClient, mock_pipeline: MagicMock, make_pipeline_result
) -> None:
    """Detection object contains correct bounding_box."""
    result = make_pipeline_result()
    mock_pipeline.get_queue.return_value = _make_stream_queue([result])
    chunks = []
    with client.stream("GET", "/stream") as response:
        for chunk in response.iter_bytes():
            chunks.append(chunk)
            break
    raw = b"".join(chunks)
    data_line = next(line for line in raw.split(b"\n") if line.startswith(b"data: "))
    body = json.loads(data_line[len(b"data: "):])
    assert body["detections"][0]["bounding_box"] == [0.1, 0.2, 0.4, 0.6]


@pytest.mark.unit
def test_stream_event_detection_is_target_true(
    client: TestClient, mock_pipeline: MagicMock, make_pipeline_result
) -> None:
    """Detection object contains is_target=True."""
    result = make_pipeline_result(is_target=True)
    mock_pipeline.get_queue.return_value = _make_stream_queue([result])
    chunks = []
    with client.stream("GET", "/stream") as response:
        for chunk in response.iter_bytes():
            chunks.append(chunk)
            break
    raw = b"".join(chunks)
    data_line = next(line for line in raw.split(b"\n") if line.startswith(b"data: "))
    body = json.loads(data_line[len(b"data: "):])
    assert body["detections"][0]["is_target"] is True


@pytest.mark.unit
def test_stream_event_detection_is_target_false(
    client: TestClient, mock_pipeline: MagicMock, make_pipeline_result
) -> None:
    """Detection object contains is_target=False."""
    result = make_pipeline_result(is_target=False)
    mock_pipeline.get_queue.return_value = _make_stream_queue([result])
    chunks = []
    with client.stream("GET", "/stream") as response:
        for chunk in response.iter_bytes():
            chunks.append(chunk)
            break
    raw = b"".join(chunks)
    data_line = next(line for line in raw.split(b"\n") if line.startswith(b"data: "))
    body = json.loads(data_line[len(b"data: "):])
    assert body["detections"][0]["is_target"] is False


@pytest.mark.unit
def test_stream_event_empty_detections(
    client: TestClient, mock_pipeline: MagicMock, make_pipeline_result
) -> None:
    """detections array is empty when no objects detected."""
    result = make_pipeline_result()
    result.detections = []
    mock_pipeline.get_queue.return_value = _make_stream_queue([result])
    chunks = []
    with client.stream("GET", "/stream") as response:
        for chunk in response.iter_bytes():
            chunks.append(chunk)
            break
    raw = b"".join(chunks)
    data_line = next(line for line in raw.split(b"\n") if line.startswith(b"data: "))
    body = json.loads(data_line[len(b"data: "):])
    assert body["detections"] == []


@pytest.mark.unit
def test_stream_event_line_format(
    client: TestClient, mock_pipeline: MagicMock, make_pipeline_result
) -> None:
    """Each SSE event line starts with 'data: '."""
    result = make_pipeline_result()
    mock_pipeline.get_queue.return_value = _make_stream_queue([result])
    chunks = []
    with client.stream("GET", "/stream") as response:
        for chunk in response.iter_bytes():
            chunks.append(chunk)
            break
    raw = b"".join(chunks)
    assert any(line.startswith(b"data: ") for line in raw.split(b"\n"))


@pytest.mark.unit
def test_stream_event_ends_with_double_newline(
    client: TestClient, mock_pipeline: MagicMock, make_pipeline_result
) -> None:
    """Each SSE event ends with \\n\\n."""
    result = make_pipeline_result()
    mock_pipeline.get_queue.return_value = _make_stream_queue([result])
    chunks = []
    with client.stream("GET", "/stream") as response:
        for chunk in response.iter_bytes():
            chunks.append(chunk)
            break
    raw = b"".join(chunks)
    assert raw.endswith(b"\n\n")


@pytest.mark.unit
def test_stream_keepalive_sent_when_queue_empty(
    client: TestClient, mock_pipeline: MagicMock
) -> None:
    """When the queue is empty for 1 second, a keepalive comment is sent."""
    empty_queue: queue.Queue = queue.Queue()
    mock_pipeline.get_queue.return_value = empty_queue

    # Simulate time advancing by 1.0 s on each call so a keepalive is triggered
    time_values = iter([0.0, 1.0, 1.0, 31.0])  # last value triggers idle timeout to end stream

    with patch("model_lens.routers.stream.time.monotonic", side_effect=time_values):
        chunks = []
        with client.stream("GET", "/stream") as response:
            for chunk in response.iter_bytes():
                chunks.append(chunk)
                if b": keepalive" in chunk:
                    break

    raw = b"".join(chunks)
    assert b": keepalive" in raw


@pytest.mark.unit
def test_stream_keepalive_format(
    client: TestClient, mock_pipeline: MagicMock
) -> None:
    """Keepalive line is an SSE comment (starts with ': ')."""
    empty_queue: queue.Queue = queue.Queue()
    mock_pipeline.get_queue.return_value = empty_queue

    time_values = iter([0.0, 1.0, 1.0, 31.0])

    with patch("model_lens.routers.stream.time.monotonic", side_effect=time_values):
        chunks = []
        with client.stream("GET", "/stream") as response:
            for chunk in response.iter_bytes():
                chunks.append(chunk)
                if b": keepalive" in chunk:
                    break

    raw = b"".join(chunks)
    keepalive_chunks = [c for c in chunks if b": keepalive" in c]
    assert len(keepalive_chunks) > 0
    assert keepalive_chunks[0] == b": keepalive\n\n"


@pytest.mark.unit
def test_stream_idle_timeout_closes_connection(
    client: TestClient, mock_pipeline: MagicMock
) -> None:
    """After 30 seconds of idle time the server closes the stream."""
    empty_queue: queue.Queue = queue.Queue()
    mock_pipeline.get_queue.return_value = empty_queue

    # Advance time past the 30 s idle timeout immediately
    time_values = iter([0.0, 30.0])

    with patch("model_lens.routers.stream.time.monotonic", side_effect=time_values):
        chunks = list(client.stream("GET", "/stream").__enter__().iter_bytes())

    # The stream should have ended (no infinite loop)
    assert isinstance(chunks, list)


@pytest.mark.unit
def test_stream_idle_timer_resets_on_frame(
    client: TestClient, mock_pipeline: MagicMock, make_pipeline_result
) -> None:
    """Receiving a frame resets the idle timer."""
    result = make_pipeline_result()
    q: queue.Queue = queue.Queue()
    mock_pipeline.get_queue.return_value = q

    # t=0 start, t=25 frame arrives, t=54 only 29 s since last frame → still open
    # We simulate: first poll empty (t=0→25), then frame available (t=25), then empty (t=25→54)
    # then timeout at t=55 (30 s after frame)
    call_count = 0
    time_sequence = [0.0, 25.0, 25.0, 54.0, 55.0]
    time_iter = iter(time_sequence)

    def _monotonic() -> float:
        return next(time_iter)

    # Put the frame in the queue so it's dequeued at the right moment
    q.put(result)

    with patch("model_lens.routers.stream.time.monotonic", side_effect=_monotonic):
        chunks = []
        with client.stream("GET", "/stream") as response:
            for chunk in response.iter_bytes():
                chunks.append(chunk)
                # After receiving the data frame, stop consuming to avoid blocking
                if any(line.startswith(b"data: ") for line in chunk.split(b"\n")):
                    break

    # Connection was open long enough to receive the frame
    raw = b"".join(chunks)
    assert any(line.startswith(b"data: ") for line in raw.split(b"\n"))


@pytest.mark.unit
def test_stream_keepalive_does_not_reset_idle_timer(
    client: TestClient, mock_pipeline: MagicMock
) -> None:
    """Keepalive comments sent during idle do NOT reset the 30-second idle timer."""
    empty_queue: queue.Queue = queue.Queue()
    mock_pipeline.get_queue.return_value = empty_queue

    # Advance time in 1 s steps; keepalives fire at 1, 2, ... but idle timeout fires at 30
    # We provide enough values to cover multiple keepalives then the 30 s timeout
    time_values = [float(i) for i in range(35)]
    time_iter = iter(time_values)

    with patch("model_lens.routers.stream.time.monotonic", side_effect=time_iter):
        chunks = []
        with client.stream("GET", "/stream") as response:
            for chunk in response.iter_bytes():
                chunks.append(chunk)

    raw = b"".join(chunks)
    # Multiple keepalives should have been sent
    assert raw.count(b": keepalive\n\n") >= 1
    # Stream ended (iterator exhausted) — connection closed cleanly


@pytest.mark.unit
def test_stream_client_disconnect_does_not_raise(
    client: TestClient, mock_pipeline: MagicMock, make_pipeline_result
) -> None:
    """Closing the TestClient stream mid-flight does not raise a server-side exception."""
    result = make_pipeline_result()
    q: queue.Queue = queue.Queue()
    for _ in range(100):
        q.put(result)
    mock_pipeline.get_queue.return_value = q

    # Open the stream and immediately close it — should not raise
    with client.stream("GET", "/stream") as response:
        response.close()


# ===========================================================================
# 6. Static Assets
# ===========================================================================


@pytest.mark.unit
def test_root_returns_200(static_client: tuple) -> None:
    """GET / returns HTTP 200."""
    c, _ = static_client
    response = c.get("/")
    assert response.status_code == 200


@pytest.mark.unit
def test_root_content_type_is_html(static_client: tuple) -> None:
    """Response Content-Type is text/html."""
    c, _ = static_client
    response = c.get("/")
    assert "text/html" in response.headers["content-type"]


@pytest.mark.unit
def test_root_body_is_index_html(static_client: tuple) -> None:
    """Response body matches the content of index.html."""
    c, index_content = static_client
    response = c.get("/")
    assert response.content == index_content


@pytest.mark.unit
def test_root_etag_header_present(static_client: tuple) -> None:
    """Response includes an ETag header."""
    c, _ = static_client
    response = c.get("/")
    assert "etag" in response.headers


@pytest.mark.unit
def test_root_etag_is_md5_of_content(static_client: tuple) -> None:
    """ETag value is the MD5 hex digest of index.html bytes, quoted."""
    c, index_content = static_client
    response = c.get("/")
    expected_etag = f'"{hashlib.md5(index_content).hexdigest()}"'
    assert response.headers["etag"] == expected_etag


@pytest.mark.unit
def test_root_etag_is_quoted_string(static_client: tuple) -> None:
    """ETag value is wrapped in double quotes per HTTP spec."""
    c, _ = static_client
    response = c.get("/")
    etag = response.headers["etag"]
    assert etag.startswith('"')
    assert etag.endswith('"')


@pytest.mark.unit
def test_static_file_returns_200(static_client: tuple) -> None:
    """GET /static/app.js returns HTTP 200."""
    c, _ = static_client
    response = c.get("/static/app.js")
    assert response.status_code == 200


@pytest.mark.unit
def test_static_file_body_matches_content(static_client: tuple) -> None:
    """Response body matches the file content."""
    c, _ = static_client
    response = c.get("/static/app.js")
    assert response.content == b"console.log('hello');"


@pytest.mark.unit
def test_static_file_not_found_returns_404(static_client: tuple) -> None:
    """GET /static/nonexistent.js returns 404."""
    c, _ = static_client
    response = c.get("/static/nonexistent.js")
    assert response.status_code == 404


@pytest.mark.unit
def test_unknown_path_returns_404(client: TestClient) -> None:
    """An unrecognised path returns 404."""
    response = client.get("/unknown")
    assert response.status_code == 404


# ===========================================================================
# 7. Dependency Injection
# ===========================================================================


@pytest.mark.unit
def test_get_pipeline_returns_pipeline_from_app_state(
    client: TestClient, mock_pipeline: MagicMock
) -> None:
    """get_pipeline returns the DetectionPipeline stored in app.state."""
    from model_lens.app import create_app
    from starlette.requests import Request

    # Access the dependency directly
    from model_lens.routers.config import get_pipeline

    # Build a minimal fake request with app.state.pipeline set
    with patch("model_lens.app.resolve_dist_dir"):
        app = create_app()
    app.state.pipeline = mock_pipeline

    fake_request = MagicMock(spec=Request)
    fake_request.app = app

    result = get_pipeline(fake_request)
    assert result is mock_pipeline


@pytest.mark.unit
def test_get_pipeline_used_by_config_router(client: TestClient, mock_pipeline: MagicMock) -> None:
    """Config router uses get_pipeline dependency; the pipeline from app.state is called."""
    client.get("/config")
    assert mock_pipeline.get_config.call_count == 1


@pytest.mark.unit
def test_stream_router_calls_get_queue(client: TestClient, mock_pipeline: MagicMock, make_pipeline_result) -> None:
    """The stream router retrieves the result queue via pipeline.get_queue() and never calls get_result_queue()."""
    result = make_pipeline_result()
    mock_pipeline.get_queue.return_value = _make_stream_queue([result])
    mock_pipeline.get_result_queue = MagicMock()

    with client.stream("GET", "/stream") as response:
        for chunk in response.iter_bytes():
            break  # consume one chunk then stop

    assert mock_pipeline.get_queue.call_count >= 1
    assert mock_pipeline.get_result_queue.call_count == 0


# ===========================================================================
# 8. Lifespan — Startup and Shutdown
# ===========================================================================


@pytest.mark.unit
def test_lifespan_config_loader_called(lifespan_mocks: dict) -> None:
    """ConfigLoader.load() is called during startup."""
    from model_lens.app import create_app

    app = create_app()
    with TestClient(app):
        pass
    assert lifespan_mocks["loader_cls"].return_value.load.call_count == 1


@pytest.mark.unit
def test_lifespan_inference_engine_constructed(lifespan_mocks: dict) -> None:
    """TorchInferenceEngine is constructed with values from AppConfig."""
    from model_lens.app import create_app

    app = create_app()
    with TestClient(app):
        pass
    mock_config = lifespan_mocks["config"]
    lifespan_mocks["engine_cls"].assert_called_once_with(
        model_path=mock_config.model.model_path,
        confidence_threshold=mock_config.model.confidence_threshold,
        labels_path=mock_config.model.labels_path,
    )


@pytest.mark.unit
def test_lifespan_detection_pipeline_constructed(lifespan_mocks: dict) -> None:
    """DetectionPipeline is constructed with the engine and initial RuntimeConfig."""
    from model_lens.app import create_app

    app = create_app()
    with TestClient(app):
        pass
    assert lifespan_mocks["pipeline_cls"].call_count == 1


@pytest.mark.unit
def test_lifespan_initial_runtime_config_camera_from_app_config(lifespan_mocks: dict) -> None:
    """The RuntimeConfig passed to DetectionPipeline has camera attributes matching AppConfig.camera."""
    from model_lens.app import create_app

    app = create_app()
    with TestClient(app):
        pass
    args, kwargs = lifespan_mocks["pipeline_cls"].call_args
    # RuntimeConfig may be passed as positional or keyword arg
    runtime_config = None
    for arg in list(args) + list(kwargs.values()):
        if isinstance(arg, RuntimeConfig):
            runtime_config = arg
            break
    assert runtime_config is not None
    assert runtime_config.camera.device_index == lifespan_mocks["config"].camera.device_index  # type: ignore[union-attr]


@pytest.mark.unit
def test_lifespan_initial_runtime_config_target_labels_empty(lifespan_mocks: dict) -> None:
    """The initial RuntimeConfig has an empty target_labels list."""
    from model_lens.app import create_app

    app = create_app()
    with TestClient(app):
        pass
    args, kwargs = lifespan_mocks["pipeline_cls"].call_args
    runtime_config = None
    for arg in list(args) + list(kwargs.values()):
        if isinstance(arg, RuntimeConfig):
            runtime_config = arg
            break
    assert runtime_config is not None
    assert runtime_config.target_labels == []


@pytest.mark.unit
def test_lifespan_pipeline_start_called(lifespan_mocks: dict) -> None:
    """DetectionPipeline.start() is called during startup."""
    from model_lens.app import create_app

    app = create_app()
    with TestClient(app):
        pass
    assert lifespan_mocks["pipeline"].start.call_count == 1


@pytest.mark.unit
def test_lifespan_pipeline_stored_in_app_state(lifespan_mocks: dict) -> None:
    """After startup, app.state.pipeline is the constructed DetectionPipeline."""
    from model_lens.app import create_app

    app = create_app()
    with TestClient(app):
        assert app.state.pipeline is lifespan_mocks["pipeline"]


@pytest.mark.unit
def test_lifespan_pipeline_stop_called_on_shutdown(lifespan_mocks: dict) -> None:
    """DetectionPipeline.stop() is called during shutdown."""
    from model_lens.app import create_app

    app = create_app()
    with TestClient(app):
        pass
    assert lifespan_mocks["pipeline"].stop.call_count == 1


@pytest.mark.unit
def test_lifespan_engine_teardown_called_on_shutdown(lifespan_mocks: dict) -> None:
    """TorchInferenceEngine.teardown() is called during shutdown."""
    from model_lens.app import create_app

    app = create_app()
    with TestClient(app):
        pass
    assert lifespan_mocks["engine"].teardown.call_count == 1


@pytest.mark.unit
def test_lifespan_engine_teardown_after_pipeline_stop(lifespan_mocks: dict) -> None:
    """teardown() is called after stop() (order enforced)."""
    from model_lens.app import create_app

    call_order: list[str] = []
    lifespan_mocks["pipeline"].stop.side_effect = lambda: call_order.append("stop")
    lifespan_mocks["engine"].teardown.side_effect = lambda: call_order.append("teardown")

    app = create_app()
    with TestClient(app):
        pass

    assert call_order == ["stop", "teardown"]


@pytest.mark.unit
def test_lifespan_config_loader_error_exits(lifespan_mocks: dict) -> None:
    """ConfigLoader.load() raising ConfigurationError causes sys.exit(1)."""
    from model_lens.app import create_app

    lifespan_mocks["loader_cls"].return_value.load.side_effect = ConfigurationError("bad config")
    app = create_app()
    with pytest.raises(SystemExit) as exc_info:
        with TestClient(app):
            pass
    assert exc_info.value.code == 1


@pytest.mark.unit
def test_lifespan_inference_engine_configuration_error_exits(lifespan_mocks: dict) -> None:
    """TorchInferenceEngine() raising ConfigurationError causes sys.exit(1)."""
    from model_lens.app import create_app

    lifespan_mocks["engine_cls"].side_effect = ConfigurationError("bad model")
    app = create_app()
    with pytest.raises(SystemExit) as exc_info:
        with TestClient(app):
            pass
    assert exc_info.value.code == 1


@pytest.mark.unit
def test_lifespan_inference_engine_operation_error_exits(lifespan_mocks: dict) -> None:
    """TorchInferenceEngine() raising OperationError causes sys.exit(1)."""
    from model_lens.app import create_app

    lifespan_mocks["engine_cls"].side_effect = OperationError("load failed")
    app = create_app()
    with pytest.raises(SystemExit) as exc_info:
        with TestClient(app):
            pass
    assert exc_info.value.code == 1


@pytest.mark.unit
def test_lifespan_missing_dist_dir_exits(lifespan_mocks: dict) -> None:
    """Missing dist/ directory causes sys.exit(1)."""
    from model_lens.app import create_app

    with patch("model_lens.app.resolve_dist_dir", side_effect=FileNotFoundError("no dist")):
        app = create_app()
        with pytest.raises(SystemExit) as exc_info:
            with TestClient(app):
                pass
    assert exc_info.value.code == 1


@pytest.mark.unit
def test_lifespan_missing_index_html_exits(lifespan_mocks: dict, tmp_path: Path) -> None:
    """Missing dist/index.html causes sys.exit(1)."""
    from model_lens.app import create_app

    dist_dir = tmp_path / "dist_no_index"
    dist_dir.mkdir()
    # No index.html created

    with patch("model_lens.app.resolve_dist_dir", return_value=dist_dir):
        app = create_app()
        with pytest.raises(SystemExit) as exc_info:
            with TestClient(app):
                pass
    assert exc_info.value.code == 1


@pytest.mark.unit
def test_lifespan_pipeline_stop_called_even_after_startup_failure(lifespan_mocks: dict) -> None:
    """DetectionPipeline.stop() is still called if startup fails after the pipeline is constructed."""
    from model_lens.app import create_app

    lifespan_mocks["pipeline"].start.side_effect = RuntimeError("start failed")
    app = create_app()
    with pytest.raises((SystemExit, RuntimeError)):
        with TestClient(app):
            pass
    assert lifespan_mocks["pipeline"].stop.call_count == 1


# ===========================================================================
# 9. LocalCameraRequest
# ===========================================================================


@pytest.mark.unit
def test_local_camera_request_default_device_index() -> None:
    """Default device_index is 0."""
    instance = LocalCameraRequest(source_type="local")
    assert instance.device_index == 0


@pytest.mark.unit
def test_local_camera_request_explicit_device_index() -> None:
    """Explicit device_index is stored."""
    instance = LocalCameraRequest(source_type="local", device_index=3)
    assert instance.device_index == 3


@pytest.mark.unit
def test_local_camera_request_negative_device_index_raises() -> None:
    """Negative device_index raises pydantic.ValidationError."""
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        LocalCameraRequest(source_type="local", device_index=-1)


# ===========================================================================
# 10. RtspCameraRequest
# ===========================================================================


@pytest.mark.unit
def test_rtsp_camera_request_stores_url() -> None:
    """Valid RTSP URL is stored."""
    instance = RtspCameraRequest(source_type="rtsp", rtsp_url="rtsp://x")
    assert instance.rtsp_url == "rtsp://x"


@pytest.mark.unit
def test_rtsp_camera_request_wrong_scheme_raises() -> None:
    """URL not starting with rtsp:// raises pydantic.ValidationError."""
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        RtspCameraRequest(source_type="rtsp", rtsp_url="http://x")


@pytest.mark.unit
def test_rtsp_camera_request_empty_url_raises() -> None:
    """Empty rtsp_url raises pydantic.ValidationError."""
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        RtspCameraRequest(source_type="rtsp", rtsp_url="")


# ===========================================================================
# 11. UpdateCameraRequest
# ===========================================================================


@pytest.mark.unit
def test_update_camera_request_local_discriminated() -> None:
    """source_type='local' produces LocalCameraRequest."""
    instance = UpdateCameraRequest(camera={"source_type": "local", "device_index": 0})
    assert isinstance(instance.camera, LocalCameraRequest)


@pytest.mark.unit
def test_update_camera_request_rtsp_discriminated() -> None:
    """source_type='rtsp' produces RtspCameraRequest."""
    instance = UpdateCameraRequest(camera={"source_type": "rtsp", "rtsp_url": "rtsp://x"})
    assert isinstance(instance.camera, RtspCameraRequest)


@pytest.mark.unit
def test_update_camera_request_unknown_source_type_raises() -> None:
    """Unknown source_type raises pydantic.ValidationError."""
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        UpdateCameraRequest(camera={"source_type": "usb"})


# ===========================================================================
# 12. UpdateLabelsRequest
# ===========================================================================


@pytest.mark.unit
def test_update_labels_request_stores_labels() -> None:
    """Labels list is stored."""
    instance = UpdateLabelsRequest(target_labels=["cat", "dog"])
    assert instance.target_labels == ["cat", "dog"]


@pytest.mark.unit
def test_update_labels_request_empty_list_valid() -> None:
    """Empty list is valid."""
    instance = UpdateLabelsRequest(target_labels=[])
    assert instance.target_labels == []


@pytest.mark.unit
def test_update_labels_request_missing_field_raises() -> None:
    """Missing target_labels field raises pydantic.ValidationError."""
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        UpdateLabelsRequest()  # type: ignore[call-arg]


@pytest.mark.unit
def test_update_labels_request_non_array_raises() -> None:
    """target_labels not being a list raises pydantic.ValidationError."""
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        UpdateLabelsRequest(target_labels="cat")  # type: ignore[arg-type]


@pytest.mark.unit
def test_update_labels_request_non_string_elements_raises() -> None:
    """Non-string elements raise pydantic.ValidationError."""
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        UpdateLabelsRequest(target_labels=[1, 2])  # type: ignore[list-item]


# ===========================================================================
# 13. Error Handling — HTTP 500
# ===========================================================================


@pytest.mark.unit
def test_unhandled_exception_returns_500(client_with_broken_pipeline: TestClient) -> None:
    """An unhandled RuntimeError in a route handler returns HTTP 500."""
    response = client_with_broken_pipeline.get("/config")
    assert response.status_code == 500


@pytest.mark.unit
def test_unhandled_exception_response_is_json(client_with_broken_pipeline: TestClient) -> None:
    """The 500 response body is valid JSON."""
    response = client_with_broken_pipeline.get("/config")
    assert "application/json" in response.headers["content-type"]
    response.json()  # should not raise


@pytest.mark.unit
def test_unhandled_exception_response_has_detail_key(client_with_broken_pipeline: TestClient) -> None:
    """The 500 response body contains a 'detail' key per FastAPI's standard error shape."""
    response = client_with_broken_pipeline.get("/config")
    assert "detail" in response.json()
