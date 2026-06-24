"""Tests for model_lens.routers.config — config endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

# Skip entire module if production router module is not yet implemented.
pytest.importorskip(
    "model_lens.routers.config",
    reason="Production module model_lens.routers.config not yet implemented",
)

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from model_lens.entities.camera_config import LocalCameraConfig, RtspCameraConfig  # noqa: E402
from model_lens.entities.runtime_config import RuntimeConfig  # noqa: E402
from model_lens.routers import config  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def _app_with_config_router() -> FastAPI:
    """Create a FastAPI app with the config router mounted."""
    app = FastAPI()
    app.include_router(config.router)
    return app


@pytest.fixture()
def client(_app_with_config_router: FastAPI, mock_pipeline: MagicMock, mock_engine: MagicMock) -> TestClient:
    """Create a TestClient with pipeline and engine mocks wired into app.state."""
    app = _app_with_config_router
    app.state.pipeline = mock_pipeline
    app.state.engine = mock_engine
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# _serialize_config — Happy Path
# ---------------------------------------------------------------------------


class TestSerializeConfigHappyPath:
    """Happy Path — _serialize_config."""

    def test_serialize_config_local_camera(self) -> None:
        """Serializes a RuntimeConfig with LocalCameraConfig correctly."""
        from model_lens.routers.config import _serialize_config

        cfg = RuntimeConfig(
            camera=LocalCameraConfig(device_index=1),
            confidence_threshold=0.6,
            target_labels=["cat"],
        )
        result = _serialize_config(cfg)
        assert result == {
            "camera": {"source_type": "local", "device_index": 1},
            "confidence_threshold": 0.6,
            "target_labels": ["cat"],
        }

    def test_serialize_config_rtsp_camera(self) -> None:
        """Serializes a RuntimeConfig with RtspCameraConfig correctly."""
        from model_lens.routers.config import _serialize_config

        cfg = RuntimeConfig(
            camera=RtspCameraConfig(rtsp_url="rtsp://host/path"),
            confidence_threshold=0.5,
            target_labels=[],
        )
        result = _serialize_config(cfg)
        assert result == {
            "camera": {"source_type": "rtsp", "rtsp_url": "rtsp://host/path"},
            "confidence_threshold": 0.5,
            "target_labels": [],
        }


# ---------------------------------------------------------------------------
# _serialize_labels — Happy Path
# ---------------------------------------------------------------------------


class TestSerializeLabelsHappyPath:
    """Happy Path — _serialize_labels."""

    def test_serialize_labels(self) -> None:
        """Returns valid_labels list from label map values."""
        from model_lens.routers.config import _serialize_labels

        result = _serialize_labels({0: "person", 1: "car", 2: "dog"})
        assert result == {"valid_labels": ["person", "car", "dog"]}


# ---------------------------------------------------------------------------
# GET /config — Happy Path
# ---------------------------------------------------------------------------


class TestGetConfigHappyPath:
    """Happy Path — GET /config."""

    def test_get_config_returns_current_config(self, client: TestClient, mock_pipeline: MagicMock) -> None:
        """Returns serialized current RuntimeConfig."""
        mock_pipeline.get_config.return_value = RuntimeConfig(
            camera=LocalCameraConfig(device_index=0),
            confidence_threshold=0.5,
            target_labels=["person"],
        )
        response = client.get("/config")
        assert response.status_code == 200
        assert response.json() == {
            "camera": {"source_type": "local", "device_index": 0},
            "confidence_threshold": 0.5,
            "target_labels": ["person"],
        }


# ---------------------------------------------------------------------------
# PUT /config/camera — Happy Path
# ---------------------------------------------------------------------------


class TestPutCameraHappyPath:
    """Happy Path — PUT /config/camera."""

    def test_put_camera_local(self, client: TestClient, mock_pipeline: MagicMock) -> None:
        """Updates camera to local and returns updated config."""
        updated_config = RuntimeConfig(
            camera=LocalCameraConfig(device_index=2),
            confidence_threshold=0.5,
            target_labels=["person"],
        )
        # First call: get current config; second call: get updated config after update_config
        mock_pipeline.get_config.side_effect = [
            RuntimeConfig(camera=LocalCameraConfig(device_index=0), confidence_threshold=0.5, target_labels=["person"]),
            updated_config,
        ]
        response = client.put("/config/camera", json={"camera": {"source_type": "local", "device_index": 2}})
        assert response.status_code == 200
        body = response.json()
        assert body["camera"] == {"source_type": "local", "device_index": 2}

    def test_put_camera_rtsp(self, client: TestClient, mock_pipeline: MagicMock) -> None:
        """Updates camera to RTSP and returns updated config."""
        updated_config = RuntimeConfig(
            camera=RtspCameraConfig(rtsp_url="rtsp://10.0.0.1/feed"),
            confidence_threshold=0.5,
            target_labels=["person"],
        )
        mock_pipeline.get_config.side_effect = [
            RuntimeConfig(camera=LocalCameraConfig(device_index=0), confidence_threshold=0.5, target_labels=["person"]),
            updated_config,
        ]
        response = client.put(
            "/config/camera", json={"camera": {"source_type": "rtsp", "rtsp_url": "rtsp://10.0.0.1/feed"}}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["camera"] == {"source_type": "rtsp", "rtsp_url": "rtsp://10.0.0.1/feed"}


# ---------------------------------------------------------------------------
# PUT /config/camera — Mock / Dependency Interaction
# ---------------------------------------------------------------------------


class TestPutCameraInteraction:
    """Mock / Dependency Interaction — PUT /config/camera."""

    def test_put_camera_calls_update_config(self, client: TestClient, mock_pipeline: MagicMock) -> None:
        """Calls pipeline.update_config() with a new RuntimeConfig containing the new camera."""
        current = RuntimeConfig(
            camera=LocalCameraConfig(device_index=0), confidence_threshold=0.5, target_labels=["person"]
        )
        mock_pipeline.get_config.side_effect = [current, current]
        client.put("/config/camera", json={"camera": {"source_type": "local", "device_index": 3}})

        mock_pipeline.update_config.assert_called_once()
        arg = mock_pipeline.update_config.call_args[0][0]
        assert isinstance(arg, RuntimeConfig)
        assert isinstance(arg.camera, LocalCameraConfig)
        assert arg.camera.device_index == 3

    def test_put_camera_preserves_other_fields(self, client: TestClient, mock_pipeline: MagicMock) -> None:
        """Preserves target_labels and confidence_threshold from current config."""
        current = RuntimeConfig(
            camera=LocalCameraConfig(device_index=0), confidence_threshold=0.7, target_labels=["dog"]
        )
        mock_pipeline.get_config.side_effect = [current, current]
        client.put("/config/camera", json={"camera": {"source_type": "local", "device_index": 0}})

        arg = mock_pipeline.update_config.call_args[0][0]
        assert arg.target_labels == ["dog"]
        assert arg.confidence_threshold == 0.7


# ---------------------------------------------------------------------------
# GET /config/labels — Happy Path
# ---------------------------------------------------------------------------


class TestGetLabelsHappyPath:
    """Happy Path — GET /config/labels."""

    def test_get_labels_returns_valid_labels(self, client: TestClient, mock_engine: MagicMock) -> None:
        """Returns all labels from the engine's label map."""
        mock_engine.get_label_map.return_value = {0: "person", 1: "bicycle", 2: "car"}
        response = client.get("/config/labels")
        assert response.status_code == 200
        assert response.json() == {"valid_labels": ["person", "bicycle", "car"]}


# ---------------------------------------------------------------------------
# PUT /config/labels — Happy Path
# ---------------------------------------------------------------------------


class TestPutLabelsHappyPath:
    """Happy Path — PUT /config/labels."""

    def test_put_labels_updates_target_labels(self, client: TestClient, mock_pipeline: MagicMock) -> None:
        """Updates target labels and returns updated config."""
        current = RuntimeConfig(
            camera=LocalCameraConfig(device_index=0), confidence_threshold=0.5, target_labels=["person"]
        )
        updated = RuntimeConfig(
            camera=LocalCameraConfig(device_index=0), confidence_threshold=0.5, target_labels=["cat", "dog"]
        )
        mock_pipeline.get_config.side_effect = [current, updated]
        response = client.put("/config/labels", json={"target_labels": ["cat", "dog"]})
        assert response.status_code == 200
        assert response.json()["target_labels"] == ["cat", "dog"]

    def test_put_labels_empty_list(self, client: TestClient, mock_pipeline: MagicMock) -> None:
        """Accepts an empty target labels list."""
        current = RuntimeConfig(
            camera=LocalCameraConfig(device_index=0), confidence_threshold=0.5, target_labels=["person"]
        )
        updated = RuntimeConfig(camera=LocalCameraConfig(device_index=0), confidence_threshold=0.5, target_labels=[])
        mock_pipeline.get_config.side_effect = [current, updated]
        response = client.put("/config/labels", json={"target_labels": []})
        assert response.status_code == 200
        assert response.json()["target_labels"] == []


# ---------------------------------------------------------------------------
# PUT /config/labels — Mock / Dependency Interaction
# ---------------------------------------------------------------------------


class TestPutLabelsInteraction:
    """Mock / Dependency Interaction — PUT /config/labels."""

    def test_put_labels_calls_update_config(self, client: TestClient, mock_pipeline: MagicMock) -> None:
        """Calls pipeline.update_config() with new RuntimeConfig containing updated labels."""
        current = RuntimeConfig(camera=LocalCameraConfig(device_index=0), confidence_threshold=0.5, target_labels=[])
        mock_pipeline.get_config.side_effect = [current, current]
        client.put("/config/labels", json={"target_labels": ["person"]})

        mock_pipeline.update_config.assert_called_once()
        arg = mock_pipeline.update_config.call_args[0][0]
        assert isinstance(arg, RuntimeConfig)
        assert arg.target_labels == ["person"]

    def test_put_labels_preserves_camera_and_threshold(self, client: TestClient, mock_pipeline: MagicMock) -> None:
        """Preserves camera and confidence_threshold from current config."""
        current = RuntimeConfig(
            camera=RtspCameraConfig(rtsp_url="rtsp://x/y"), confidence_threshold=0.8, target_labels=[]
        )
        mock_pipeline.get_config.side_effect = [current, current]
        client.put("/config/labels", json={"target_labels": ["cat"]})

        arg = mock_pipeline.update_config.call_args[0][0]
        assert isinstance(arg.camera, RtspCameraConfig)
        assert arg.camera.rtsp_url == "rtsp://x/y"
        assert arg.confidence_threshold == 0.8
