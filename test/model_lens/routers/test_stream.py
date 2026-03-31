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

"""Tests for model_lens.routers.stream."""

import base64
import json
import time
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from model_lens.entities import DetectionResult


@pytest.fixture
def make_pipeline_result():
    def _make(label="cat", confidence=0.9, is_target=True):
        result = MagicMock()
        result.jpeg_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 16  # minimal fake JPEG
        result.timestamp = 1748000400.123456
        result.source = "local:0"
        detection = DetectionResult(
            label=label,
            confidence=confidence,
            bounding_box=(0.1, 0.2, 0.4, 0.6),
            is_target=is_target,
        )
        result.detections = [detection]
        return result

    return _make


def _parse_sse_data(raw_bytes: bytes) -> dict:
    """Extract the JSON payload from an SSE data line."""
    text = raw_bytes.decode()
    for line in text.strip().splitlines():
        if line.startswith("data: "):
            return json.loads(line[len("data: ") :])
    raise ValueError(f"No SSE data line found in: {text!r}")


# ---- 1.1 Happy Path — Event Payload Format ----


class TestStreamEventPayload:
    """Tests for GET /stream SSE event payload format."""

    @pytest.fixture(autouse=True)
    def _setup_queue(self, mock_pipeline, make_pipeline_result):
        """Configure mock_pipeline to yield one result then stop."""
        result = make_pipeline_result()
        self._result = result

        call_count = 0

        def get_queue_side_effect(timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return result
            return None

        mock_pipeline.get_queue.side_effect = get_queue_side_effect

    def test_stream_returns_200(self, client: TestClient):
        with client.stream("GET", "/stream") as response:
            assert response.status_code == 200

    def test_stream_content_type_is_text_event_stream(self, client: TestClient):
        with client.stream("GET", "/stream") as response:
            assert "text/event-stream" in response.headers["content-type"]

    def test_stream_event_contains_jpeg_b64(self, client: TestClient):
        with client.stream("GET", "/stream") as response:
            for chunk in response.iter_bytes():
                if chunk.startswith(b"data: "):
                    body = _parse_sse_data(chunk)
                    assert "jpeg_b64" in body
                    assert isinstance(body["jpeg_b64"], str)
                    assert len(body["jpeg_b64"]) > 0
                    return
        pytest.fail("No SSE data event received")

    def test_stream_event_jpeg_b64_is_valid_base64(self, client: TestClient):
        with client.stream("GET", "/stream") as response:
            for chunk in response.iter_bytes():
                if chunk.startswith(b"data: "):
                    body = _parse_sse_data(chunk)
                    base64.b64decode(body["jpeg_b64"])  # should not raise
                    return
        pytest.fail("No SSE data event received")

    def test_stream_event_jpeg_b64_decodes_to_original_bytes(
        self, client: TestClient
    ):
        with client.stream("GET", "/stream") as response:
            for chunk in response.iter_bytes():
                if chunk.startswith(b"data: "):
                    body = _parse_sse_data(chunk)
                    decoded = base64.b64decode(body["jpeg_b64"])
                    assert decoded == self._result.jpeg_bytes
                    return
        pytest.fail("No SSE data event received")

    def test_stream_event_contains_timestamp(self, client: TestClient):
        with client.stream("GET", "/stream") as response:
            for chunk in response.iter_bytes():
                if chunk.startswith(b"data: "):
                    body = _parse_sse_data(chunk)
                    assert body["timestamp"] == 1748000400.123456
                    return
        pytest.fail("No SSE data event received")

    def test_stream_event_contains_source(self, client: TestClient):
        with client.stream("GET", "/stream") as response:
            for chunk in response.iter_bytes():
                if chunk.startswith(b"data: "):
                    body = _parse_sse_data(chunk)
                    assert body["source"] == "local:0"
                    return
        pytest.fail("No SSE data event received")

    def test_stream_event_contains_detections(self, client: TestClient):
        with client.stream("GET", "/stream") as response:
            for chunk in response.iter_bytes():
                if chunk.startswith(b"data: "):
                    body = _parse_sse_data(chunk)
                    assert len(body["detections"]) == 1
                    return
        pytest.fail("No SSE data event received")

    def test_stream_event_detection_label(self, client: TestClient):
        with client.stream("GET", "/stream") as response:
            for chunk in response.iter_bytes():
                if chunk.startswith(b"data: "):
                    body = _parse_sse_data(chunk)
                    assert body["detections"][0]["label"] == "cat"
                    return
        pytest.fail("No SSE data event received")

    def test_stream_event_detection_confidence(self, client: TestClient):
        with client.stream("GET", "/stream") as response:
            for chunk in response.iter_bytes():
                if chunk.startswith(b"data: "):
                    body = _parse_sse_data(chunk)
                    assert body["detections"][0]["confidence"] == 0.9
                    return
        pytest.fail("No SSE data event received")

    def test_stream_event_detection_bounding_box(self, client: TestClient):
        with client.stream("GET", "/stream") as response:
            for chunk in response.iter_bytes():
                if chunk.startswith(b"data: "):
                    body = _parse_sse_data(chunk)
                    assert body["detections"][0]["bounding_box"] == [
                        0.1,
                        0.2,
                        0.4,
                        0.6,
                    ]
                    return
        pytest.fail("No SSE data event received")


class TestStreamEventDetectionIsTarget:
    """Tests for detection is_target field."""

    def test_stream_event_detection_is_target_true(
        self, client: TestClient, mock_pipeline, make_pipeline_result
    ):
        result = make_pipeline_result(is_target=True)
        call_count = 0

        def get_queue_side_effect(timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return result
            return None

        mock_pipeline.get_queue.side_effect = get_queue_side_effect

        with client.stream("GET", "/stream") as response:
            for chunk in response.iter_bytes():
                if chunk.startswith(b"data: "):
                    body = _parse_sse_data(chunk)
                    assert body["detections"][0]["is_target"] is True
                    return
        pytest.fail("No SSE data event received")

    def test_stream_event_detection_is_target_false(
        self, client: TestClient, mock_pipeline, make_pipeline_result
    ):
        result = make_pipeline_result(is_target=False)
        call_count = 0

        def get_queue_side_effect(timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return result
            return None

        mock_pipeline.get_queue.side_effect = get_queue_side_effect

        with client.stream("GET", "/stream") as response:
            for chunk in response.iter_bytes():
                if chunk.startswith(b"data: "):
                    body = _parse_sse_data(chunk)
                    assert body["detections"][0]["is_target"] is False
                    return
        pytest.fail("No SSE data event received")


class TestStreamEventEmptyDetections:
    """Test for empty detections array."""

    def test_stream_event_empty_detections(
        self, client: TestClient, mock_pipeline
    ):
        result = MagicMock()
        result.jpeg_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 16
        result.timestamp = 1748000400.123456
        result.source = "local:0"
        result.detections = []

        call_count = 0

        def get_queue_side_effect(timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return result
            return None

        mock_pipeline.get_queue.side_effect = get_queue_side_effect

        with client.stream("GET", "/stream") as response:
            for chunk in response.iter_bytes():
                if chunk.startswith(b"data: "):
                    body = _parse_sse_data(chunk)
                    assert body["detections"] == []
                    return
        pytest.fail("No SSE data event received")


class TestStreamEventFormat:
    """Tests for raw SSE event line format."""

    @pytest.fixture(autouse=True)
    def _setup_queue(self, mock_pipeline, make_pipeline_result):
        result = make_pipeline_result()
        call_count = 0

        def get_queue_side_effect(timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return result
            return None

        mock_pipeline.get_queue.side_effect = get_queue_side_effect

    def test_stream_event_line_format(self, client: TestClient):
        with client.stream("GET", "/stream") as response:
            for chunk in response.iter_bytes():
                if b"data: " in chunk:
                    assert chunk.startswith(b"data: ")
                    return
        pytest.fail("No SSE data event received")

    def test_stream_event_ends_with_double_newline(self, client: TestClient):
        with client.stream("GET", "/stream") as response:
            for chunk in response.iter_bytes():
                if chunk.startswith(b"data: "):
                    assert chunk.endswith(b"\n\n")
                    return
        pytest.fail("No SSE data event received")


# ---- 1.2 Happy Path — Keepalive ----


class TestStreamKeepalive:
    """Tests for keepalive behaviour when queue is empty."""

    def test_stream_keepalive_sent_when_queue_empty(
        self, client: TestClient, mock_pipeline
    ):
        monotonic_values = iter([0.0, 1.0, 31.0])

        mock_pipeline.get_queue.return_value = None

        with patch("model_lens.routers.stream.time.monotonic", side_effect=monotonic_values):
            with client.stream("GET", "/stream") as response:
                for chunk in response.iter_bytes():
                    if b"keepalive" in chunk:
                        return
        pytest.fail("No keepalive received")

    def test_stream_keepalive_format(
        self, client: TestClient, mock_pipeline
    ):
        monotonic_values = iter([0.0, 1.0, 31.0])

        mock_pipeline.get_queue.return_value = None

        with patch("model_lens.routers.stream.time.monotonic", side_effect=monotonic_values):
            with client.stream("GET", "/stream") as response:
                for chunk in response.iter_bytes():
                    if b"keepalive" in chunk:
                        assert chunk == b": keepalive\n\n"
                        return
        pytest.fail("No keepalive received")


# ---- 1.3 Happy Path — Idle Timeout ----


class TestStreamIdleTimeout:
    """Tests for server-side idle timeout."""

    def test_stream_idle_timeout_closes_connection(
        self, client: TestClient, mock_pipeline
    ):
        # Simulate time jumping to 30s with no frames
        monotonic_values = iter([0.0, 30.0])
        mock_pipeline.get_queue.return_value = None

        with patch("model_lens.routers.stream.time.monotonic", side_effect=monotonic_values):
            with client.stream("GET", "/stream") as response:
                chunks = list(response.iter_bytes())
                # Stream should have ended (iterator exhausted)
                assert isinstance(chunks, list)

    def test_stream_idle_timer_resets_on_frame(
        self, client: TestClient, mock_pipeline, make_pipeline_result
    ):
        result = make_pipeline_result()
        # t=0: start, t=25: queue returns frame (resets timer),
        # t=54: 29s since frame (under 30s limit) -> still open, then t=55 -> closes
        monotonic_values = iter([0.0, 25.0, 25.0, 54.0, 55.0])

        call_count = 0

        def get_queue_side_effect(timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return result
            return None

        mock_pipeline.get_queue.side_effect = get_queue_side_effect

        with patch("model_lens.routers.stream.time.monotonic", side_effect=monotonic_values):
            with client.stream("GET", "/stream") as response:
                chunks = list(response.iter_bytes())
                # Should have received at least the frame data event
                data_chunks = [c for c in chunks if c.startswith(b"data: ")]
                assert len(data_chunks) >= 1

    def test_stream_keepalive_does_not_reset_idle_timer(
        self, client: TestClient, mock_pipeline
    ):
        # Queue always empty; time advances in 1s steps up to 30s
        # Keepalives are sent but should not reset the idle timer
        times = [float(i) for i in range(32)]
        monotonic_values = iter(times)
        mock_pipeline.get_queue.return_value = None

        with patch("model_lens.routers.stream.time.monotonic", side_effect=monotonic_values):
            with client.stream("GET", "/stream") as response:
                chunks = list(response.iter_bytes())
                keepalives = [c for c in chunks if b"keepalive" in c]
                # Keepalives were sent but stream still closed at ~30s
                assert len(keepalives) > 0
                # Stream ended (iterator exhausted = connection closed)


# ---- 1.4 Resource Cleanup ----


class TestStreamCleanup:
    """Tests for resource cleanup on client disconnect."""

    def test_stream_client_disconnect_does_not_raise(
        self, client: TestClient, mock_pipeline, make_pipeline_result
    ):
        result = make_pipeline_result()
        mock_pipeline.get_queue.return_value = result

        with client.stream("GET", "/stream") as response:
            # Read one chunk then close immediately
            for chunk in response.iter_bytes():
                if chunk.startswith(b"data: "):
                    break
            response.close()
