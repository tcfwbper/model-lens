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

"""Tests for model_lens.routers.config."""

import pytest
from fastapi.testclient import TestClient

from model_lens.entities import (
    LocalCameraConfig,
    RtspCameraConfig,
    RuntimeConfig,
)


# ---- 1. GET /config — Local Camera ----


class TestGetConfigLocal:
    """Tests for GET /config with local camera (default)."""

    @pytest.mark.unit
    def test_get_config_returns_200(self, client: TestClient):
        response = client.get("/config")
        assert response.status_code == 200

    @pytest.mark.unit
    def test_get_config_local_source_type(self, client: TestClient):
        body = client.get("/config").json()
        assert body["camera"]["source_type"] == "local"

    @pytest.mark.unit
    def test_get_config_local_device_index(self, client: TestClient):
        body = client.get("/config").json()
        assert body["camera"]["device_index"] == 0

    @pytest.mark.unit
    def test_get_config_local_no_rtsp_url(self, client: TestClient):
        body = client.get("/config").json()
        assert "rtsp_url" not in body["camera"]

    @pytest.mark.unit
    def test_get_config_confidence_threshold(self, client: TestClient):
        body = client.get("/config").json()
        assert body["confidence_threshold"] == 0.5

    @pytest.mark.unit
    def test_get_config_target_labels_empty(self, client: TestClient):
        body = client.get("/config").json()
        assert body["target_labels"] == []

    @pytest.mark.unit
    def test_get_config_target_labels_non_empty(
        self, client: TestClient, mock_pipeline
    ):
        mock_pipeline.get_config.return_value = RuntimeConfig(
            camera=LocalCameraConfig(device_index=0),
            target_labels=["cat", "dog"],
            confidence_threshold=0.5,
        )
        body = client.get("/config").json()
        assert body["target_labels"] == ["cat", "dog"]


# ---- 1.2 GET /config — RTSP Camera ----


class TestGetConfigRtsp:
    """Tests for GET /config with RTSP camera."""

    @pytest.fixture(autouse=True)
    def _set_rtsp_config(self, mock_pipeline):
        mock_pipeline.get_config.return_value = RuntimeConfig(
            camera=RtspCameraConfig(rtsp_url="rtsp://192.168.1.10/stream"),
            target_labels=[],
            confidence_threshold=0.5,
        )

    @pytest.mark.unit
    def test_get_config_rtsp_source_type(self, client: TestClient):
        body = client.get("/config").json()
        assert body["camera"]["source_type"] == "rtsp"

    @pytest.mark.unit
    def test_get_config_rtsp_url(self, client: TestClient):
        body = client.get("/config").json()
        assert body["camera"]["rtsp_url"] == "rtsp://192.168.1.10/stream"

    @pytest.mark.unit
    def test_get_config_rtsp_no_device_index(self, client: TestClient):
        body = client.get("/config").json()
        assert "device_index" not in body["camera"]


# ---- 2. PUT /config/camera — Local ----


class TestPutCameraLocal:
    """Tests for PUT /config/camera with local camera."""

    @pytest.mark.unit
    def test_put_camera_local_returns_200(self, client: TestClient):
        response = client.put(
            "/config/camera",
            json={"camera": {"source_type": "local", "device_index": 0}},
        )
        assert response.status_code == 200

    @pytest.mark.unit
    def test_put_camera_local_calls_update_config(
        self, client: TestClient, mock_pipeline
    ):
        client.put(
            "/config/camera",
            json={"camera": {"source_type": "local", "device_index": 0}},
        )
        assert mock_pipeline.update_config.call_count == 1

    @pytest.mark.unit
    def test_put_camera_local_update_config_receives_runtime_config(
        self, client: TestClient, mock_pipeline
    ):
        client.put(
            "/config/camera",
            json={"camera": {"source_type": "local", "device_index": 2}},
        )
        config = mock_pipeline.update_config.call_args[0][0]
        assert isinstance(config, RuntimeConfig)
        assert config.camera.device_index == 2

    @pytest.mark.unit
    def test_put_camera_local_response_reflects_new_camera(
        self, client: TestClient, mock_pipeline
    ):
        # After update_config, get_config returns the new config
        def update_side_effect(new_config):
            mock_pipeline.get_config.return_value = new_config

        mock_pipeline.update_config.side_effect = update_side_effect
        body = client.put(
            "/config/camera",
            json={"camera": {"source_type": "local", "device_index": 2}},
        ).json()
        assert body["camera"]["device_index"] == 2

    @pytest.mark.unit
    def test_put_camera_local_preserves_target_labels(
        self, client: TestClient, mock_pipeline
    ):
        mock_pipeline.get_config.return_value = RuntimeConfig(
            camera=LocalCameraConfig(device_index=0),
            target_labels=["cat"],
            confidence_threshold=0.5,
        )
        client.put(
            "/config/camera",
            json={"camera": {"source_type": "local", "device_index": 1}},
        )
        config = mock_pipeline.update_config.call_args[0][0]
        assert config.target_labels == ["cat"]

    @pytest.mark.unit
    def test_put_camera_local_preserves_confidence_threshold(
        self, client: TestClient, mock_pipeline
    ):
        mock_pipeline.get_config.return_value = RuntimeConfig(
            camera=LocalCameraConfig(device_index=0),
            target_labels=[],
            confidence_threshold=0.75,
        )
        client.put(
            "/config/camera",
            json={"camera": {"source_type": "local", "device_index": 0}},
        )
        config = mock_pipeline.update_config.call_args[0][0]
        assert config.confidence_threshold == 0.75


# ---- 2.2 PUT /config/camera — RTSP ----


class TestPutCameraRtsp:
    """Tests for PUT /config/camera with RTSP camera."""

    @pytest.mark.unit
    def test_put_camera_rtsp_returns_200(self, client: TestClient):
        response = client.put(
            "/config/camera",
            json={
                "camera": {
                    "source_type": "rtsp",
                    "rtsp_url": "rtsp://192.168.1.10/stream",
                }
            },
        )
        assert response.status_code == 200

    @pytest.mark.unit
    def test_put_camera_rtsp_update_config_receives_runtime_config(
        self, client: TestClient, mock_pipeline
    ):
        client.put(
            "/config/camera",
            json={
                "camera": {
                    "source_type": "rtsp",
                    "rtsp_url": "rtsp://192.168.1.10/stream",
                }
            },
        )
        config = mock_pipeline.update_config.call_args[0][0]
        assert isinstance(config, RuntimeConfig)
        assert config.camera.rtsp_url == "rtsp://192.168.1.10/stream"

    @pytest.mark.unit
    def test_put_camera_rtsp_response_reflects_new_camera(
        self, client: TestClient, mock_pipeline
    ):
        def update_side_effect(new_config):
            mock_pipeline.get_config.return_value = new_config

        mock_pipeline.update_config.side_effect = update_side_effect
        body = client.put(
            "/config/camera",
            json={
                "camera": {
                    "source_type": "rtsp",
                    "rtsp_url": "rtsp://192.168.1.10/stream",
                }
            },
        ).json()
        assert body["camera"]["source_type"] == "rtsp"
        assert body["camera"]["rtsp_url"] == "rtsp://192.168.1.10/stream"


# ---- 2.3 PUT /config/camera — Validation Failures ----


class TestPutCameraValidation:
    """Validation failure tests for PUT /config/camera."""

    @pytest.mark.unit
    def test_put_camera_invalid_source_type_returns_422(self, client: TestClient):
        response = client.put(
            "/config/camera", json={"camera": {"source_type": "usb"}}
        )
        assert response.status_code == 422

    @pytest.mark.unit
    def test_put_camera_local_negative_device_index_returns_422(
        self, client: TestClient
    ):
        response = client.put(
            "/config/camera",
            json={"camera": {"source_type": "local", "device_index": -1}},
        )
        assert response.status_code == 422

    @pytest.mark.unit
    def test_put_camera_rtsp_missing_url_returns_422(self, client: TestClient):
        response = client.put(
            "/config/camera", json={"camera": {"source_type": "rtsp"}}
        )
        assert response.status_code == 422

    @pytest.mark.unit
    def test_put_camera_rtsp_empty_url_returns_422(self, client: TestClient):
        response = client.put(
            "/config/camera",
            json={"camera": {"source_type": "rtsp", "rtsp_url": ""}},
        )
        assert response.status_code == 422

    @pytest.mark.unit
    def test_put_camera_rtsp_url_wrong_scheme_returns_422(self, client: TestClient):
        response = client.put(
            "/config/camera",
            json={
                "camera": {
                    "source_type": "rtsp",
                    "rtsp_url": "http://192.168.1.10/stream",
                }
            },
        )
        assert response.status_code == 422

    @pytest.mark.unit
    def test_put_camera_missing_camera_field_returns_422(self, client: TestClient):
        response = client.put("/config/camera", json={})
        assert response.status_code == 422

    @pytest.mark.unit
    def test_put_camera_malformed_json_returns_400(self, client: TestClient):
        response = client.put(
            "/config/camera",
            content=b"not json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400

    @pytest.mark.unit
    def test_put_camera_confidence_threshold_in_body_is_ignored(
        self, client: TestClient
    ):
        response = client.put(
            "/config/camera",
            json={
                "camera": {"source_type": "local", "device_index": 0},
                "confidence_threshold": 0.9,
            },
        )
        assert response.status_code == 200


# ---- 3. PUT /config/labels — Happy Path ----


class TestPutLabels:
    """Tests for PUT /config/labels."""

    @pytest.mark.unit
    def test_put_labels_returns_200(self, client: TestClient):
        response = client.put(
            "/config/labels", json={"target_labels": ["cat", "dog"]}
        )
        assert response.status_code == 200

    @pytest.mark.unit
    def test_put_labels_calls_update_config(
        self, client: TestClient, mock_pipeline
    ):
        client.put("/config/labels", json={"target_labels": ["cat"]})
        assert mock_pipeline.update_config.call_count == 1

    @pytest.mark.unit
    def test_put_labels_update_config_receives_runtime_config(
        self, client: TestClient, mock_pipeline
    ):
        client.put("/config/labels", json={"target_labels": ["cat", "dog"]})
        config = mock_pipeline.update_config.call_args[0][0]
        assert isinstance(config, RuntimeConfig)
        assert config.target_labels == ["cat", "dog"]

    @pytest.mark.unit
    def test_put_labels_empty_list_is_valid(self, client: TestClient):
        response = client.put("/config/labels", json={"target_labels": []})
        assert response.status_code == 200

    @pytest.mark.unit
    def test_put_labels_response_reflects_new_labels(
        self, client: TestClient, mock_pipeline
    ):
        def update_side_effect(new_config):
            mock_pipeline.get_config.return_value = new_config

        mock_pipeline.update_config.side_effect = update_side_effect
        body = client.put(
            "/config/labels", json={"target_labels": ["person"]}
        ).json()
        assert body["target_labels"] == ["person"]

    @pytest.mark.unit
    def test_put_labels_preserves_camera(
        self, client: TestClient, mock_pipeline
    ):
        mock_pipeline.get_config.return_value = RuntimeConfig(
            camera=LocalCameraConfig(device_index=1),
            target_labels=[],
            confidence_threshold=0.5,
        )
        client.put("/config/labels", json={"target_labels": ["cat"]})
        config = mock_pipeline.update_config.call_args[0][0]
        assert config.camera.device_index == 1

    @pytest.mark.unit
    def test_put_labels_preserves_confidence_threshold(
        self, client: TestClient, mock_pipeline
    ):
        mock_pipeline.get_config.return_value = RuntimeConfig(
            camera=LocalCameraConfig(device_index=0),
            target_labels=[],
            confidence_threshold=0.75,
        )
        client.put("/config/labels", json={"target_labels": ["cat"]})
        config = mock_pipeline.update_config.call_args[0][0]
        assert config.confidence_threshold == 0.75


# ---- 3.2 PUT /config/labels — Validation Failures ----


class TestPutLabelsValidation:
    """Validation failure tests for PUT /config/labels."""

    @pytest.mark.unit
    def test_put_labels_missing_field_returns_422(self, client: TestClient):
        response = client.put("/config/labels", json={})
        assert response.status_code == 422

    @pytest.mark.unit
    def test_put_labels_non_array_returns_422(self, client: TestClient):
        response = client.put("/config/labels", json={"target_labels": "cat"})
        assert response.status_code == 422

    @pytest.mark.unit
    def test_put_labels_array_of_non_strings_returns_422(self, client: TestClient):
        response = client.put(
            "/config/labels", json={"target_labels": [1, 2, 3]}
        )
        assert response.status_code == 422

    @pytest.mark.unit
    def test_put_labels_malformed_json_returns_400(self, client: TestClient):
        response = client.put(
            "/config/labels",
            content=b"not json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400
