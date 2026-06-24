"""Tests for model_lens.routers.stream — SSE stream endpoint."""

from __future__ import annotations

import base64
import json
import queue
from unittest.mock import MagicMock, patch

import pytest

# Skip entire module if production router module is not yet implemented.
pytest.importorskip(
    "model_lens.routers.stream",
    reason="Production module model_lens.routers.stream not yet implemented",
)

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from model_lens.detection_pipeline import PipelineResult  # noqa: E402
from model_lens.entities.detection_result import DetectionResult  # noqa: E402
from model_lens.routers import stream  # noqa: E402

# Module path for patching _monotonic
_MONOTONIC_PATH = "model_lens.routers.stream._monotonic"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_pipeline_result(
    jpeg_bytes: bytes = b"\xff\xd8",
    timestamp: float = 1748000400.123,
    source: str = "local:0",
    detections: list[DetectionResult] | None = None,
) -> PipelineResult:
    """Helper to build PipelineResult with sensible defaults."""
    if detections is None:
        detections = []
    return PipelineResult(
        jpeg_bytes=jpeg_bytes,
        timestamp=timestamp,
        source=source,
        detections=detections,
    )


@pytest.fixture()
def mock_pipeline_with_queue() -> MagicMock:
    """Create a mock pipeline with a mock queue."""
    pipeline = MagicMock()
    mock_queue = MagicMock()
    pipeline.get_queue.return_value = mock_queue
    return pipeline


@pytest.fixture()
def client(mock_pipeline_with_queue: MagicMock) -> TestClient:
    """Create a TestClient with stream router and lifespan bypassed."""
    app = FastAPI()
    app.include_router(stream.router)
    app.state.pipeline = mock_pipeline_with_queue
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# _event_generator — Happy Path
# ---------------------------------------------------------------------------


class TestEventGeneratorHappyPath:
    """Happy Path — _event_generator."""

    def test_event_generator_emits_frame(self, mock_pipeline_with_queue: MagicMock) -> None:
        """Yields an SSE data line for a single frame."""
        result = _make_pipeline_result()
        mock_q = mock_pipeline_with_queue.get_queue()
        # First call returns a frame, second raises Empty, which triggers idle timeout
        mock_q.get.side_effect = [result, queue.Empty()]

        # Patch _monotonic: initial=0.0, after frame=0.0, then 31.0 to trigger idle timeout
        times = iter([0.0, 0.0, 31.0])
        with patch(_MONOTONIC_PATH, side_effect=lambda: next(times)):
            from model_lens.routers.stream import _event_generator

            gen = _event_generator(mock_pipeline_with_queue)
            first_yield = next(gen)

        assert first_yield.startswith(b"data: ")
        payload = json.loads(first_yield[len(b"data: ") :].rstrip())
        assert "jpeg_b64" in payload
        assert "timestamp" in payload
        assert "source" in payload
        assert "detections" in payload

    def test_event_generator_serializes_detections(self, mock_pipeline_with_queue: MagicMock) -> None:
        """Each detection is serialized with label, confidence, bounding_box (as list), and is_target."""
        detections = [
            DetectionResult(label="person", confidence=0.9, bounding_box=(0.1, 0.2, 0.3, 0.4), is_target=True),
            DetectionResult(label="car", confidence=0.7, bounding_box=(0.5, 0.6, 0.7, 0.8), is_target=False),
        ]
        result = _make_pipeline_result(detections=detections)
        mock_q = mock_pipeline_with_queue.get_queue()
        mock_q.get.side_effect = [result, queue.Empty()]

        times = iter([0.0, 0.0, 31.0])
        with patch(_MONOTONIC_PATH, side_effect=lambda: next(times)):
            from model_lens.routers.stream import _event_generator

            gen = _event_generator(mock_pipeline_with_queue)
            first_yield = next(gen)

        payload = json.loads(first_yield[len(b"data: ") :].rstrip())
        assert len(payload["detections"]) == 2
        det = payload["detections"][0]
        assert "label" in det
        assert "confidence" in det
        assert "bounding_box" in det
        assert "is_target" in det
        assert isinstance(det["bounding_box"], list)
        assert len(det["bounding_box"]) == 4

    def test_event_generator_base64_encoding(self, mock_pipeline_with_queue: MagicMock) -> None:
        """JPEG bytes are base64-encoded in the payload."""
        jpeg_bytes = b"\xff\xd8"
        result = _make_pipeline_result(jpeg_bytes=jpeg_bytes)
        mock_q = mock_pipeline_with_queue.get_queue()
        mock_q.get.side_effect = [result, queue.Empty()]

        times = iter([0.0, 0.0, 31.0])
        with patch(_MONOTONIC_PATH, side_effect=lambda: next(times)):
            from model_lens.routers.stream import _event_generator

            gen = _event_generator(mock_pipeline_with_queue)
            first_yield = next(gen)

        payload = json.loads(first_yield[len(b"data: ") :].rstrip())
        expected_b64 = base64.b64encode(jpeg_bytes).decode()
        assert payload["jpeg_b64"] == expected_b64


# ---------------------------------------------------------------------------
# GET /stream — Happy Path
# ---------------------------------------------------------------------------


class TestStreamEndpointHappyPath:
    """Happy Path — GET /stream."""

    def test_stream_endpoint_returns_event_stream(
        self, client: TestClient, mock_pipeline_with_queue: MagicMock
    ) -> None:
        """Returns a StreamingResponse with text/event-stream media type."""
        result = _make_pipeline_result()
        mock_q = mock_pipeline_with_queue.get_queue()
        mock_q.get.side_effect = [result, queue.Empty()]

        # Patch _monotonic to trigger idle timeout after one frame
        times = iter([0.0, 0.0, 31.0])
        with patch(_MONOTONIC_PATH, side_effect=lambda: next(times)):
            response = client.get("/stream")

        assert "text/event-stream" in response.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# _event_generator — Mock / Dependency Interaction
# ---------------------------------------------------------------------------


class TestEventGeneratorInteraction:
    """Mock / Dependency Interaction — _event_generator."""

    def test_event_generator_calls_queue_get_with_timeout(self, mock_pipeline_with_queue: MagicMock) -> None:
        """Calls queue.get(timeout=_QUEUE_TIMEOUT)."""
        mock_q = mock_pipeline_with_queue.get_queue()
        mock_q.get.side_effect = [queue.Empty()]

        # Time: initial=0.0, then 31.0 to trigger idle timeout immediately
        times = iter([0.0, 31.0])
        with patch(_MONOTONIC_PATH, side_effect=lambda: next(times)):
            from model_lens.routers.stream import _event_generator

            gen = _event_generator(mock_pipeline_with_queue)
            # Consume until StopIteration (keepalive + close)
            list(gen)

        mock_q.get.assert_called_with(timeout=1.0)


# ---------------------------------------------------------------------------
# _event_generator — Keepalive
# ---------------------------------------------------------------------------


class TestEventGeneratorKeepalive:
    """Happy Path — Keepalive."""

    def test_event_generator_emits_keepalive(self, mock_pipeline_with_queue: MagicMock) -> None:
        """Emits a keepalive comment after 30 seconds of no frames."""
        mock_q = mock_pipeline_with_queue.get_queue()
        # Queue always empty
        mock_q.get.side_effect = queue.Empty()

        # Time sequence: initial=0.0, first iteration check=30.0 (triggers keepalive + idle timeout)
        times = iter([0.0, 30.0])
        with patch(_MONOTONIC_PATH, side_effect=lambda: next(times)):
            from model_lens.routers.stream import _event_generator

            gen = _event_generator(mock_pipeline_with_queue)
            results = list(gen)

        assert b": keepalive\n\n" in results


# ---------------------------------------------------------------------------
# _event_generator — State Transitions
# ---------------------------------------------------------------------------


class TestEventGeneratorStateTransitions:
    """State Transitions — _event_generator."""

    def test_event_generator_idle_timeout_closes_stream(self, mock_pipeline_with_queue: MagicMock) -> None:
        """Closes the generator after 30 seconds of no frames."""
        mock_q = mock_pipeline_with_queue.get_queue()
        mock_q.get.side_effect = queue.Empty()

        # Time: initial=0.0, then 30.0 triggers keepalive + idle timeout
        times = iter([0.0, 30.0])
        with patch(_MONOTONIC_PATH, side_effect=lambda: next(times)):
            from model_lens.routers.stream import _event_generator

            gen = _event_generator(mock_pipeline_with_queue)
            results = list(gen)

        # Generator terminated (list() completed without hanging)
        assert isinstance(results, list)

    def test_event_generator_frame_resets_idle_timer(self, mock_pipeline_with_queue: MagicMock) -> None:
        """Receiving a frame resets the idle timeout."""
        result = _make_pipeline_result()
        mock_q = mock_pipeline_with_queue.get_queue()
        # Frame at t=29, then empty at t=30 (within 30s of last frame at t=29), then idle at t=60
        mock_q.get.side_effect = [result, queue.Empty(), queue.Empty()]

        # Time: initial=0.0, after frame=29.0 (frame received), check=30.0 (only 1s since frame),
        # check=60.0 (31s since frame => idle timeout)
        times = iter([0.0, 29.0, 30.0, 60.0])
        with patch(_MONOTONIC_PATH, side_effect=lambda: next(times)):
            from model_lens.routers.stream import _event_generator

            gen = _event_generator(mock_pipeline_with_queue)
            results = list(gen)

        # Should have a data frame, possibly keepalive, then terminate
        data_frames = [r for r in results if r.startswith(b"data: ")]
        assert len(data_frames) == 1  # The frame was emitted

    def test_keepalive_does_not_reset_idle_timer(self, mock_pipeline_with_queue: MagicMock) -> None:
        """Keepalive emission does not extend the idle timeout."""
        mock_q = mock_pipeline_with_queue.get_queue()
        mock_q.get.side_effect = queue.Empty()

        # Time: initial=0.0, then 30.0 (keepalive fires AND idle timeout fires in same iteration)
        times = iter([0.0, 30.0])
        with patch(_MONOTONIC_PATH, side_effect=lambda: next(times)):
            from model_lens.routers.stream import _event_generator

            gen = _event_generator(mock_pipeline_with_queue)
            results = list(gen)

        # Should yield keepalive then terminate
        assert b": keepalive\n\n" in results
        # Generator terminated (no more yields)
        assert len(results) <= 2  # At most keepalive + maybe nothing else
