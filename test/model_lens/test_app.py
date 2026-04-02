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

"""Tests for model_lens.app."""

import hashlib
import importlib.resources
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from model_lens.entities import (
    LocalCameraConfig,
    RuntimeConfig,
)
from model_lens.exceptions import ConfigurationError, OperationError


# ---- Fixtures ----


@pytest.fixture
def mock_pipeline():
    pipeline = MagicMock()
    pipeline.get_config.return_value = RuntimeConfig(
        camera=LocalCameraConfig(device_index=0),
        target_labels=[],
        confidence_threshold=0.5,
    )
    return pipeline


@pytest.fixture
def client(mock_pipeline, tmp_path):
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    index_html = dist_dir / "index.html"
    index_html.write_bytes(b"<html><body>ModelLens</body></html>")
    static_dir = dist_dir / "static"
    static_dir.mkdir()

    with patch("model_lens.app.resolve_dist_dir", return_value=dist_dir):
        from model_lens.app import create_app

        app = create_app()

    app.state.pipeline = mock_pipeline

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture
def static_client(mock_pipeline, tmp_path):
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    index_content = b"<html><body>ModelLens</body></html>"
    (dist_dir / "index.html").write_bytes(index_content)
    static_dir = dist_dir / "static"
    static_dir.mkdir()
    (static_dir / "app.js").write_bytes(b"console.log('hello');")

    with patch("model_lens.app.resolve_dist_dir", return_value=dist_dir):
        from model_lens.app import create_app

        app = create_app()

    app.state.pipeline = mock_pipeline

    with TestClient(app) as c:
        yield c, index_content


@pytest.fixture
def lifespan_mocks(tmp_path):
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_bytes(b"<html></html>")
    (dist_dir / "static").mkdir()

    mock_config = MagicMock()
    mock_config.model.model = "fake.pt"
    mock_config.model.confidence_threshold = 0.5
    mock_config.camera.source_type = "local"
    mock_config.camera.device_index = 0

    with (
        patch("model_lens.app.load", return_value=mock_config) as mock_load,
        patch("model_lens.app.YOLOInferenceEngine") as mock_engine_cls,
        patch("model_lens.app.DetectionPipeline") as mock_pipeline_cls,
        patch("model_lens.app.resolve_dist_dir", return_value=dist_dir),
    ):
        mock_engine = MagicMock()
        mock_engine_cls.return_value = mock_engine
        mock_pipeline = MagicMock()
        mock_pipeline_cls.return_value = mock_pipeline

        yield {
            "load": mock_load,
            "engine_cls": mock_engine_cls,
            "engine": mock_engine,
            "pipeline_cls": mock_pipeline_cls,
            "pipeline": mock_pipeline,
            "config": mock_config,
        }


@pytest.fixture
def client_with_broken_pipeline(mock_pipeline, tmp_path):
    mock_pipeline.get_config.side_effect = RuntimeError("unexpected failure")

    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_bytes(b"<html></html>")
    (dist_dir / "static").mkdir()

    with patch("model_lens.app.resolve_dist_dir", return_value=dist_dir):
        from model_lens.app import create_app

        app = create_app()

    app.state.pipeline = mock_pipeline

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ---- 1. Static Assets ----


class TestStaticAssetsRoot:
    """Tests for GET /."""

    @pytest.mark.unit
    def test_root_returns_200(self, static_client):
        client, _ = static_client
        response = client.get("/")
        assert response.status_code == 200

    @pytest.mark.unit
    def test_root_content_type_is_html(self, static_client):
        client, _ = static_client
        response = client.get("/")
        assert "text/html" in response.headers["content-type"]

    @pytest.mark.unit
    def test_root_body_is_index_html(self, static_client):
        client, index_content = static_client
        response = client.get("/")
        assert response.content == index_content

    @pytest.mark.unit
    def test_root_etag_header_present(self, static_client):
        client, _ = static_client
        response = client.get("/")
        assert "etag" in response.headers

    @pytest.mark.unit
    def test_root_etag_is_md5_of_content(self, static_client):
        client, index_content = static_client
        response = client.get("/")
        expected = f'"{hashlib.md5(index_content).hexdigest()}"'
        assert response.headers["etag"] == expected

    @pytest.mark.unit
    def test_root_etag_is_quoted_string(self, static_client):
        client, _ = static_client
        response = client.get("/")
        etag = response.headers["etag"]
        assert etag.startswith('"')
        assert etag.endswith('"')
    
    @pytest.mark.unit
    def test_resolve_dist_dir_returns_package_dist_path(self):
        from model_lens.app import resolve_dist_dir

        expected = Path(str(importlib.resources.files("model_lens"))) / "dist"
        assert resolve_dist_dir() == expected

class TestStaticAssetsFiles:
    """Tests for GET /static/{path}."""

    @pytest.mark.unit
    def test_static_file_returns_200(self, static_client):
        client, _ = static_client
        response = client.get("/static/app.js")
        assert response.status_code == 200

    @pytest.mark.unit
    def test_static_file_body_matches_content(self, static_client):
        client, _ = static_client
        response = client.get("/static/app.js")
        assert response.content == b"console.log('hello');"

    @pytest.mark.unit
    def test_static_file_not_found_returns_404(self, static_client):
        client, _ = static_client
        response = client.get("/static/nonexistent.js")
        assert response.status_code == 404


class TestStaticAssetsValidation:
    """Validation tests for unknown paths."""

    @pytest.mark.unit
    def test_unknown_path_returns_404(self, static_client):
        client, _ = static_client
        response = client.get("/unknown")
        assert response.status_code == 404


# ---- 2. Dependency Injection ----


class TestDependencyInjection:
    """Tests for get_pipeline and get_queue dependency injection."""

    @pytest.mark.unit
    def test_get_pipeline_returns_pipeline_from_app_state(
        self, mock_pipeline, tmp_path
    ):
        dist_dir = tmp_path / "dist"
        dist_dir.mkdir()
        (dist_dir / "index.html").write_bytes(b"<html></html>")
        (dist_dir / "static").mkdir()

        with patch("model_lens.app.resolve_dist_dir", return_value=dist_dir):
            from model_lens.app import create_app, get_pipeline

            app = create_app()

        app.state.pipeline = mock_pipeline

        # Simulate a request object with the app attached
        mock_request = MagicMock()
        mock_request.app = app
        result = get_pipeline(mock_request)
        assert result is mock_pipeline

    @pytest.mark.unit
    def test_get_pipeline_used_by_config_router(
        self, client: TestClient, mock_pipeline
    ):
        client.get("/config")
        assert mock_pipeline.get_config.call_count == 1

    @pytest.mark.unit
    def test_stream_router_calls_get_queue(
        self, client: TestClient, mock_pipeline
    ):
        # Set up a queue with one result so the stream has something to yield
        result = MagicMock()
        result.jpeg_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 16
        result.timestamp = 1748000400.0
        result.source = "local:0"
        result.detections = []

        call_count = 0

        def queue_get_side_effect(timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return result
            return None

        mock_queue = MagicMock()
        mock_pipeline.get_queue.return_value = mock_queue
        mock_queue.get.side_effect = queue_get_side_effect

        with (
            patch("model_lens.routers.stream._IDLE_TIMEOUT", 0.0),
            patch("model_lens.routers.stream._QUEUE_TIMEOUT", 0.0),
            client.stream("GET", "/stream") as response,
        ):
            # Consume at least one chunk to trigger the get_queue call
            for chunk in response.iter_bytes():
                if chunk.startswith(b"data: "):
                    break

        assert mock_pipeline.get_queue.call_count >= 1
        assert mock_pipeline.get_result_queue.call_count == 0


# ---- 3. Lifespan — Startup and Shutdown ----


class TestLifespanStartup:
    """Tests for lifespan startup sequence."""

    @pytest.mark.unit
    def test_lifespan_inference_engine_constructed(self, lifespan_mocks):
        from model_lens.app import create_app

        app = create_app()
        with TestClient(app):
            pass

        lifespan_mocks["engine_cls"].assert_called_once_with(
            model=lifespan_mocks["config"].model.model,
            confidence_threshold=lifespan_mocks["config"].model.confidence_threshold,
        )

    @pytest.mark.unit
    def test_lifespan_detection_pipeline_constructed(self, lifespan_mocks):
        from model_lens.app import create_app

        app = create_app()
        with TestClient(app):
            pass

        assert lifespan_mocks["pipeline_cls"].call_count == 1

    @pytest.mark.unit
    def test_lifespan_initial_runtime_config_camera_from_app_config(
        self, lifespan_mocks
    ):
        from model_lens.app import create_app

        app = create_app()
        with TestClient(app):
            pass

        call_args = lifespan_mocks["pipeline_cls"].call_args
        # RuntimeConfig may be passed as positional or keyword argument
        if call_args.args:
            # Check keyword arguments for initial_config or second positional arg
            runtime_config = None
            for arg in call_args.args:
                if isinstance(arg, RuntimeConfig):
                    runtime_config = arg
                    break
            if runtime_config is None and call_args.kwargs:
                runtime_config = call_args.kwargs.get("initial_config")
        else:
            runtime_config = call_args.kwargs.get("initial_config")

        if runtime_config is None:
            # Try to find it in any positional/keyword arg
            all_args = list(call_args.args) + list(call_args.kwargs.values())
            for arg in all_args:
                if isinstance(arg, RuntimeConfig):
                    runtime_config = arg
                    break

        assert runtime_config is not None
        assert (
            runtime_config.camera.device_index
            == lifespan_mocks["config"].camera.device_index
        )

    @pytest.mark.unit
    def test_lifespan_initial_runtime_config_target_labels_from_engine(
        self, lifespan_mocks
    ):
        from model_lens.app import create_app

        app = create_app()
        with TestClient(app):
            pass

        call_args = lifespan_mocks["pipeline_cls"].call_args
        all_args = list(call_args.args) + list(call_args.kwargs.values())
        runtime_config = None
        for arg in all_args:
            if isinstance(arg, RuntimeConfig):
                runtime_config = arg
                break

        assert runtime_config is not None
        expected_labels = list(
            lifespan_mocks["engine"].get_label_map.return_value.values()
        )
        assert runtime_config.target_labels == expected_labels

    @pytest.mark.unit
    def test_lifespan_pipeline_start_called(self, lifespan_mocks):
        from model_lens.app import create_app

        app = create_app()
        with TestClient(app):
            pass

        assert lifespan_mocks["pipeline"].start.call_count == 1

    @pytest.mark.unit
    def test_lifespan_pipeline_stored_in_app_state(self, lifespan_mocks):
        from model_lens.app import create_app

        app = create_app()
        with TestClient(app):
            assert app.state.pipeline is lifespan_mocks["pipeline"]


class TestLifespanShutdown:
    """Tests for lifespan shutdown sequence."""

    @pytest.mark.unit
    def test_lifespan_pipeline_stop_called_on_shutdown(self, lifespan_mocks):
        from model_lens.app import create_app

        app = create_app()
        with TestClient(app):
            pass

        assert lifespan_mocks["pipeline"].stop.call_count == 1

    @pytest.mark.unit
    def test_lifespan_engine_teardown_called_on_shutdown(self, lifespan_mocks):
        from model_lens.app import create_app

        app = create_app()
        with TestClient(app):
            pass

        assert lifespan_mocks["engine"].teardown.call_count == 1

    @pytest.mark.unit
    def test_lifespan_engine_teardown_after_pipeline_stop(self, lifespan_mocks):
        from model_lens.app import create_app

        call_order = []
        lifespan_mocks["pipeline"].stop.side_effect = (
            lambda: call_order.append("stop")
        )
        lifespan_mocks["engine"].teardown.side_effect = (
            lambda: call_order.append("teardown")
        )

        app = create_app()
        with TestClient(app):
            pass

        assert call_order.index("stop") < call_order.index("teardown")


class TestLifespanErrorPropagation:
    """Tests for lifespan error propagation."""

    @pytest.mark.unit
    def test_lifespan_load_error_exits(self, lifespan_mocks):
        lifespan_mocks["load"].side_effect = ConfigurationError("bad config")

        from model_lens.app import create_app

        app = create_app()
        with pytest.raises(SystemExit) as exc_info:
            with TestClient(app):
                pass
        assert exc_info.value.code == 1

    @pytest.mark.unit
    def test_lifespan_inference_engine_configuration_error_exits(
        self, lifespan_mocks
    ):
        lifespan_mocks["engine_cls"].side_effect = ConfigurationError("bad model")

        from model_lens.app import create_app

        app = create_app()
        with pytest.raises(SystemExit) as exc_info:
            with TestClient(app):
                pass
        assert exc_info.value.code == 1

    @pytest.mark.unit
    def test_lifespan_inference_engine_operation_error_exits(self, lifespan_mocks):
        lifespan_mocks["engine_cls"].side_effect = OperationError("load failed")

        from model_lens.app import create_app

        app = create_app()
        with pytest.raises(SystemExit) as exc_info:
            with TestClient(app):
                pass
        assert exc_info.value.code == 1

    @pytest.mark.unit
    def test_lifespan_missing_dist_dir_exits(self, lifespan_mocks):
        with patch(
            "model_lens.app.resolve_dist_dir", side_effect=FileNotFoundError
        ):
            from model_lens.app import create_app

            app = create_app()
            with pytest.raises(SystemExit) as exc_info:
                with TestClient(app):
                    pass
            assert exc_info.value.code == 1

    @pytest.mark.unit
    def test_lifespan_missing_index_html_exits(self, lifespan_mocks, tmp_path):
        dist_dir = tmp_path / "dist_no_index"
        dist_dir.mkdir()
        (dist_dir / "static").mkdir()
        # index.html is intentionally absent

        with patch("model_lens.app.resolve_dist_dir", return_value=dist_dir):
            from model_lens.app import create_app

            app = create_app()
            with pytest.raises(SystemExit) as exc_info:
                with TestClient(app):
                    pass
            assert exc_info.value.code == 1

    @pytest.mark.unit
    def test_lifespan_pipeline_stop_called_even_after_startup_failure(
        self, lifespan_mocks
    ):
        lifespan_mocks["pipeline"].start.side_effect = RuntimeError("double start")

        from model_lens.app import create_app

        app = create_app()
        with pytest.raises(SystemExit):
            with TestClient(app):
                pass

        assert lifespan_mocks["pipeline"].stop.call_count == 1


# ---- 4. Error Handling — HTTP 500 ----


class TestErrorHandling:
    """Tests for unhandled exception → HTTP 500."""

    @pytest.mark.unit
    def test_unhandled_exception_returns_500(self, client_with_broken_pipeline):
        response = client_with_broken_pipeline.get("/config")
        assert response.status_code == 500

    @pytest.mark.unit
    def test_unhandled_exception_response_is_json(self, client_with_broken_pipeline):
        response = client_with_broken_pipeline.get("/config")
        assert "application/json" in response.headers["content-type"]
        response.json()  # should not raise

    @pytest.mark.unit
    def test_unhandled_exception_response_has_detail_key(
        self, client_with_broken_pipeline
    ):
        response = client_with_broken_pipeline.get("/config")
        assert "detail" in response.json()
