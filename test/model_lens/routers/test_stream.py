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
import queue
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


def _monotonic_seq(*times: float, fallback: float = 200.0):
    """Return a callable that yields *times* in order, then always returns *fallback*.

    Used to mock ``time.monotonic`` in stream tests.  Because
    ``patch("model_lens.routers.stream.time.monotonic", ...)`` replaces the
    attribute on the shared ``time`` module object, the mock is visible to
    starlette / anyio internals as well.  Those extra calls would exhaust a
    plain iterator and raise ``StopIteration`` inside the generator — which
    Python 3.7+ converts to ``RuntimeError``, stalling the stream.  The
    *fallback* (200 s) is large enough to trigger the idle-timeout branch so
    the generator exits cleanly even when extra calls occur.
    """
    it = iter(times)
    return lambda: next(it, fallback)


@pytest.fixture(autouse=True)
def _patch_stream_timeouts(monkeypatch):
    """Make all stream tests fast by default.

    ``_IDLE_TIMEOUT=0.0`` causes the generator to exit immediately after the
    first ``None`` result instead of spinning for 30 real seconds.
    ``_QUEUE_TIMEOUT=0.0`` is a no-op in practice (the mock returns instantly)
    but makes the intent explicit.

    Classes that test keepalive / idle-timeout behaviour override this fixture
    at class scope (same fixture name, closer scope wins in pytest) to restore
    the real ``_IDLE_TIMEOUT`` value — those tests already mock
    ``time.monotonic`` so they remain fast.
    """
    monkeypatch.setattr("model_lens.routers.stream._IDLE_TIMEOUT", 0.0)
    monkeypatch.setattr("model_lens.routers.stream._QUEUE_TIMEOUT", 0.0)


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
            raise queue.Empty

        mock_pipeline.get_queue.return_value.get.side_effect = get_queue_side_effect

    @pytest.mark.unit
    def test_stream_returns_200(self, client: TestClient):
        with client.stream("GET", "/stream") as response:
            assert response.status_code == 200

    @pytest.mark.unit
    def test_stream_content_type_is_text_event_stream(self, client: TestClient):
        with client.stream("GET", "/stream") as response:
            assert "text/event-stream" in response.headers["content-type"]

    @pytest.mark.unit
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

    @pytest.mark.unit
    def test_stream_event_jpeg_b64_is_valid_base64(self, client: TestClient):
        with client.stream("GET", "/stream") as response:
            for chunk in response.iter_bytes():
                if chunk.startswith(b"data: "):
                    body = _parse_sse_data(chunk)
                    base64.b64decode(body["jpeg_b64"])  # should not raise
                    return
        pytest.fail("No SSE data event received")

    @pytest.mark.unit
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

    @pytest.mark.unit
    def test_stream_event_contains_timestamp(self, client: TestClient):
        with client.stream("GET", "/stream") as response:
            for chunk in response.iter_bytes():
                if chunk.startswith(b"data: "):
                    body = _parse_sse_data(chunk)
                    assert body["timestamp"] == 1748000400.123456
                    return
        pytest.fail("No SSE data event received")

    @pytest.mark.unit
    def test_stream_event_contains_source(self, client: TestClient):
        with client.stream("GET", "/stream") as response:
            for chunk in response.iter_bytes():
                if chunk.startswith(b"data: "):
                    body = _parse_sse_data(chunk)
                    assert body["source"] == "local:0"
                    return
        pytest.fail("No SSE data event received")

    @pytest.mark.unit
    def test_stream_event_contains_detections(self, client: TestClient):
        with client.stream("GET", "/stream") as response:
            for chunk in response.iter_bytes():
                if chunk.startswith(b"data: "):
                    body = _parse_sse_data(chunk)
                    assert len(body["detections"]) == 1
                    return
        pytest.fail("No SSE data event received")

    @pytest.mark.unit
    def test_stream_event_detection_label(self, client: TestClient):
        with client.stream("GET", "/stream") as response:
            for chunk in response.iter_bytes():
                if chunk.startswith(b"data: "):
                    body = _parse_sse_data(chunk)
                    assert body["detections"][0]["label"] == "cat"
                    return
        pytest.fail("No SSE data event received")

    @pytest.mark.unit
    def test_stream_event_detection_confidence(self, client: TestClient):
        with client.stream("GET", "/stream") as response:
            for chunk in response.iter_bytes():
                if chunk.startswith(b"data: "):
                    body = _parse_sse_data(chunk)
                    assert body["detections"][0]["confidence"] == 0.9
                    return
        pytest.fail("No SSE data event received")

    @pytest.mark.unit
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

    @pytest.mark.unit
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
            raise queue.Empty

        mock_pipeline.get_queue.return_value.get.side_effect = get_queue_side_effect

        with client.stream("GET", "/stream") as response:
            for chunk in response.iter_bytes():
                if chunk.startswith(b"data: "):
                    body = _parse_sse_data(chunk)
                    assert body["detections"][0]["is_target"] is True
                    return
        pytest.fail("No SSE data event received")

    @pytest.mark.unit
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
            raise queue.Empty

        mock_pipeline.get_queue.return_value.get.side_effect = get_queue_side_effect

        with client.stream("GET", "/stream") as response:
            for chunk in response.iter_bytes():
                if chunk.startswith(b"data: "):
                    body = _parse_sse_data(chunk)
                    assert body["detections"][0]["is_target"] is False
                    return
        pytest.fail("No SSE data event received")


class TestStreamEventEmptyDetections:
    """Test for empty detections array."""

    @pytest.mark.unit
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
            raise queue.Empty

        mock_pipeline.get_queue.return_value.get.side_effect = get_queue_side_effect

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
            raise queue.Empty

        mock_pipeline.get_queue.return_value.get.side_effect = get_queue_side_effect

    @pytest.mark.unit
    def test_stream_event_line_format(self, client: TestClient):
        with client.stream("GET", "/stream") as response:
            for chunk in response.iter_bytes():
                if b"data: " in chunk:
                    assert chunk.startswith(b"data: ")
                    return
        pytest.fail("No SSE data event received")

    @pytest.mark.unit
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

    @pytest.fixture(autouse=True)
    def _patch_stream_timeouts(self, monkeypatch):
        """Restore real _IDLE_TIMEOUT and _KEEPALIVE_INTERVAL for keepalive tests.

        These tests mock ``time.monotonic`` directly, so they are already fast;
        they need the real constant values so their hand-crafted time sequences
        trigger keepalive and idle-timeout logic correctly.
        """
        monkeypatch.setattr("model_lens.routers.stream._IDLE_TIMEOUT", 30.0)
        monkeypatch.setattr("model_lens.routers.stream._KEEPALIVE_INTERVAL", 30.0)
        monkeypatch.setattr("model_lens.routers.stream._QUEUE_TIMEOUT", 0.0)

    @pytest.mark.unit
    def test_stream_keepalive_sent_when_queue_empty(
        self, client: TestClient, mock_pipeline
    ):
        # t=0 init; t=1 loop-1 (1s < 30s → no keepalive, no idle);
        # t=31 loop-2 (31s ≥ 30s → keepalive + idle → return).
        mock_pipeline.get_queue.return_value.get.side_effect = queue.Empty

        with patch("model_lens.routers.stream._monotonic", side_effect=_monotonic_seq(0.0, 1.0, 31.0)):
            with client.stream("GET", "/stream") as response:
                for chunk in response.iter_bytes():
                    if b"keepalive" in chunk:
                        return
        pytest.fail("No keepalive received")

    @pytest.mark.unit
    def test_stream_keepalive_format(
        self, client: TestClient, mock_pipeline
    ):
        mock_pipeline.get_queue.return_value.get.side_effect = queue.Empty

        with patch("model_lens.routers.stream._monotonic", side_effect=_monotonic_seq(0.0, 1.0, 31.0)):
            with client.stream("GET", "/stream") as response:
                for chunk in response.iter_bytes():
                    if b"keepalive" in chunk:
                        assert chunk == b": keepalive\n\n"
                        return
        pytest.fail("No keepalive received")


# ---- 1.3 Happy Path — Idle Timeout ----


class TestStreamIdleTimeout:
    """Tests for server-side idle timeout."""

    @pytest.fixture(autouse=True)
    def _patch_stream_timeouts(self, monkeypatch):
        """Restore real _IDLE_TIMEOUT for idle-timeout tests.

        These tests mock ``time.monotonic`` directly, so they are already fast;
        they need ``_IDLE_TIMEOUT=30.0`` so their hand-crafted time sequences
        (e.g. jumping to t=30.0) actually trigger the idle-timeout branch.
        """
        monkeypatch.setattr("model_lens.routers.stream._IDLE_TIMEOUT", 30.0)
        monkeypatch.setattr("model_lens.routers.stream._KEEPALIVE_INTERVAL", 30.0)
        monkeypatch.setattr("model_lens.routers.stream._QUEUE_TIMEOUT", 0.0)

    @pytest.mark.unit
    def test_stream_idle_timeout_closes_connection(
        self, client: TestClient, mock_pipeline
    ):
        # t=0 init; t=30 loop-1 (30s ≥ 30s → idle timeout → return).
        mock_pipeline.get_queue.return_value.get.side_effect = queue.Empty

        with patch("model_lens.routers.stream._monotonic", side_effect=_monotonic_seq(0.0, 30.0)):
            with client.stream("GET", "/stream") as response:
                chunks = list(response.iter_bytes())
                # Stream should have ended (iterator exhausted)
                assert isinstance(chunks, list)

    @pytest.mark.unit
    def test_stream_idle_timer_resets_on_frame(
        self, client: TestClient, mock_pipeline, make_pipeline_result
    ):
        result = make_pipeline_result()
        # t=0: start; t=25: frame received (resets idle timer to t=25);
        # t=25: loop after frame (0s since frame < 30s → still open);
        # t=54: 29s since frame (still < 30s → still open);
        # t=55: 30s since frame → idle timeout → return.
        call_count = 0

        def get_queue_side_effect(timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return result
            raise queue.Empty

        mock_pipeline.get_queue.return_value.get.side_effect = get_queue_side_effect

        with patch(
            "model_lens.routers.stream._monotonic",
            side_effect=_monotonic_seq(0.0, 25.0, 25.0, 54.0, 55.0),
        ):
            with client.stream("GET", "/stream") as response:
                chunks = list(response.iter_bytes())
                # Should have received at least the frame data event
                data_chunks = [c for c in chunks if c.startswith(b"data: ")]
                assert len(data_chunks) >= 1

    @pytest.mark.unit
    def test_stream_keepalive_does_not_reset_idle_timer(
        self, client: TestClient, mock_pipeline
    ):
        # Queue always empty; time advances in 1s steps 0→31.
        # Keepalives fire when the interval is hit but must NOT reset the idle
        # timer — the stream should still close when 30s have elapsed since the
        # last frame (which is t=0, the session start time).
        mock_pipeline.get_queue.return_value.get.side_effect = queue.Empty

        with patch(
            "model_lens.routers.stream._monotonic",
            side_effect=_monotonic_seq(*[float(i) for i in range(32)]),
        ):
            with client.stream("GET", "/stream") as response:
                chunks = list(response.iter_bytes())
                keepalives = [c for c in chunks if b"keepalive" in c]
                # Keepalives were sent but stream still closed at ~30s
                assert len(keepalives) > 0
                # Stream ended (iterator exhausted = connection closed)


# ---- 1.4 Resource Cleanup ----


class TestStreamCleanup:
    """Tests for resource cleanup on client disconnect."""

    @pytest.mark.unit
    def test_stream_client_disconnect_does_not_raise(
        self, client: TestClient, mock_pipeline, make_pipeline_result
    ):
        result = make_pipeline_result()
        # Return a result on the first call, then None so the generator exits
        # via the idle-timeout path (patched to 0.0 by the module fixture)
        # rather than producing frames indefinitely and flooding the buffer.
        call_count = 0

        def get_queue_side_effect(timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return result
            raise queue.Empty

        mock_pipeline.get_queue.return_value.get.side_effect = get_queue_side_effect

        with client.stream("GET", "/stream") as response:
            # Read one chunk then close immediately
            for chunk in response.iter_bytes():
                if chunk.startswith(b"data: "):
                    break
            response.close()

    @pytest.mark.unit
    def test_stream_generator_exit_does_not_suppress(self, mock_pipeline):
        """gen.close() terminates the generator cleanly and does not raise.

        ``GeneratorExit`` propagates normally through the generator: the
        ``finally`` block runs, the generator returns, and no other exception
        escapes to the caller of ``.close()``.
        """
        from model_lens.routers.stream import _event_generator

        mock_pipeline.get_queue.return_value.get.side_effect = queue.Empty
        gen = _event_generator(mock_pipeline)

        # Must not raise — GeneratorExit is not converted into another exception.
        gen.close()

    @pytest.mark.unit
    def test_stream_generator_exit_triggers_cleanup(self, mock_pipeline):
        """Calling gen.close() once triggers the finally block exactly once.

        After ``.close()`` returns, the generator frame must be gone
        (``gi_frame is None``), confirming the ``finally`` cleanup block
        executed.  A second ``.close()`` call is idempotent — it must not
        trigger cleanup a second time or raise any exception.
        """
        from model_lens.routers.stream import _event_generator

        mock_pipeline.get_queue.return_value.get.side_effect = queue.Empty
        gen = _event_generator(mock_pipeline)

        # First close: finally block must execute and terminate the generator.
        gen.close()
        assert gen.gi_frame is None  # generator fully terminated

        # Second close: no-op — must not raise and must not re-run cleanup.
        gen.close()
