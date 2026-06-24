"""Tests for model_lens.app — application factory, lifespan, and startup logic."""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Skip entire module if production app module is not yet implemented.
pytest.importorskip(
    "model_lens.app",
    reason="Production module model_lens.app not yet implemented",
)

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from model_lens.app import (  # noqa: E402
    _StartupExit,
    _startup,
    create_app,
    get_pipeline,
    lifespan,
    resolve_dist_dir,
)
from model_lens.exceptions import ConfigurationError, OperationError  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers & Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_dist_dir(tmp_path: Path) -> Path:
    """Create a temporary dist directory with index.html."""
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html></html>")
    return dist


@pytest.fixture()
def tmp_dist_dir_with_assets(tmp_dist_dir: Path) -> Path:
    """Create a temporary dist directory with index.html, favicon.svg, and assets/."""
    (tmp_dist_dir / "favicon.svg").write_text("<svg></svg>")
    assets = tmp_dist_dir / "assets"
    assets.mkdir()
    (assets / "main.js").write_text("console.log('hello')")
    return tmp_dist_dir


@pytest.fixture()
def mock_load_success() -> MagicMock:
    """Create a mock for model_lens.config.load that returns a valid AppConfig."""
    mock_config = MagicMock()
    mock_config.model.model = "yolov8n"
    mock_config.model.confidence_threshold = 0.5
    mock_config.camera.device_index = 0
    return mock_config


# ---------------------------------------------------------------------------
# _StartupExit — Type Hierarchy
# ---------------------------------------------------------------------------


class TestStartupExitTypeHierarchy:
    """Type Hierarchy — _StartupExit."""

    def test_startup_exit_inherits_system_exit(self) -> None:
        """_StartupExit is a subclass of SystemExit."""
        assert issubclass(_StartupExit, SystemExit)

    def test_startup_exit_inherits_exception(self) -> None:
        """_StartupExit is a subclass of Exception."""
        assert issubclass(_StartupExit, Exception)


# ---------------------------------------------------------------------------
# _StartupExit — Catch Behaviour
# ---------------------------------------------------------------------------


class TestStartupExitCatchBehaviour:
    """Catch Behaviour — _StartupExit."""

    def test_startup_exit_caught_by_exception_handler(self) -> None:
        """Can be caught by a bare except Exception clause."""
        caught = False
        try:
            raise _StartupExit(1)
        except Exception:
            caught = True
        assert caught


# ---------------------------------------------------------------------------
# resolve_dist_dir — Happy Path
# ---------------------------------------------------------------------------


class TestResolveDistDir:
    """Happy Path — resolve_dist_dir."""

    def test_resolve_dist_dir_returns_path(self) -> None:
        """Returns a Path ending with dist."""
        with patch("model_lens.app.importlib.resources.files") as mock_files:
            mock_files.return_value = "/fake/package"
            result = resolve_dist_dir()
        assert result == Path("/fake/package/dist")


# ---------------------------------------------------------------------------
# get_pipeline — Happy Path
# ---------------------------------------------------------------------------


class TestGetPipeline:
    """Happy Path — get_pipeline."""

    def test_get_pipeline_returns_pipeline_from_state(self) -> None:
        """Returns the pipeline stored in request.app.state.pipeline."""
        mock_pipeline = MagicMock()
        mock_request = MagicMock()
        mock_request.app.state.pipeline = mock_pipeline
        result = get_pipeline(mock_request)
        assert result is mock_pipeline


# ---------------------------------------------------------------------------
# _startup — Happy Path
# ---------------------------------------------------------------------------


class TestStartupHappyPath:
    """Happy Path — _startup."""

    def test_startup_success(self, tmp_dist_dir: Path, mock_load_success: MagicMock) -> None:
        """Returns (engine, pipeline) when all steps succeed."""
        mock_engine = MagicMock()
        mock_engine.get_label_map.return_value = {0: "person"}
        mock_pipeline = MagicMock()

        with (
            patch("model_lens.app.load", return_value=mock_load_success),
            patch("model_lens.app.resolve_dist_dir", return_value=tmp_dist_dir),
            patch("model_lens.app.YOLOInferenceEngine", return_value=mock_engine),
            patch("model_lens.app.DetectionPipeline", return_value=mock_pipeline),
        ):
            result = _startup()

        assert result == (mock_engine, mock_pipeline)
        mock_pipeline.start.assert_called_once()


# ---------------------------------------------------------------------------
# _startup — Error Propagation
# ---------------------------------------------------------------------------


class TestStartupErrorPropagation:
    """Error Propagation — _startup."""

    def test_startup_config_load_configuration_error(self) -> None:
        """Raises _StartupExit(1) when load() raises ConfigurationError."""
        with patch("model_lens.app.load", side_effect=ConfigurationError("bad config")):
            with pytest.raises(_StartupExit) as exc_info:
                _startup()
        assert exc_info.value.code == 1

    def test_startup_config_load_file_not_found(self) -> None:
        """Raises _StartupExit(1) when load() raises FileNotFoundError."""
        with patch("model_lens.app.load", side_effect=FileNotFoundError("no file")):
            with pytest.raises(_StartupExit) as exc_info:
                _startup()
        assert exc_info.value.code == 1

    def test_startup_dist_dir_not_found(self, mock_load_success: MagicMock) -> None:
        """Raises _StartupExit(1) when resolve_dist_dir() raises FileNotFoundError."""
        with (
            patch("model_lens.app.load", return_value=mock_load_success),
            patch("model_lens.app.resolve_dist_dir", side_effect=FileNotFoundError()),
        ):
            with pytest.raises(_StartupExit) as exc_info:
                _startup()
        assert exc_info.value.code == 1

    def test_startup_index_html_missing(self, tmp_path: Path, mock_load_success: MagicMock) -> None:
        """Raises _StartupExit(1) when dist/index.html does not exist."""
        dist = tmp_path / "dist"
        dist.mkdir()
        # Do NOT create index.html
        with (
            patch("model_lens.app.load", return_value=mock_load_success),
            patch("model_lens.app.resolve_dist_dir", return_value=dist),
        ):
            with pytest.raises(_StartupExit) as exc_info:
                _startup()
        assert exc_info.value.code == 1

    def test_startup_engine_configuration_error(self, tmp_dist_dir: Path, mock_load_success: MagicMock) -> None:
        """Raises _StartupExit(1) when YOLOInferenceEngine raises ConfigurationError."""
        with (
            patch("model_lens.app.load", return_value=mock_load_success),
            patch("model_lens.app.resolve_dist_dir", return_value=tmp_dist_dir),
            patch("model_lens.app.YOLOInferenceEngine", side_effect=ConfigurationError("bad threshold")),
        ):
            with pytest.raises(_StartupExit) as exc_info:
                _startup()
        assert exc_info.value.code == 1

    def test_startup_engine_operation_error(self, tmp_dist_dir: Path, mock_load_success: MagicMock) -> None:
        """Raises _StartupExit(1) when YOLOInferenceEngine raises OperationError."""
        with (
            patch("model_lens.app.load", return_value=mock_load_success),
            patch("model_lens.app.resolve_dist_dir", return_value=tmp_dist_dir),
            patch("model_lens.app.YOLOInferenceEngine", side_effect=OperationError("model load failed")),
        ):
            with pytest.raises(_StartupExit) as exc_info:
                _startup()
        assert exc_info.value.code == 1

    def test_startup_pipeline_start_failure_calls_stop(self, tmp_dist_dir: Path, mock_load_success: MagicMock) -> None:
        """Calls pipeline.stop() then raises _StartupExit(1) when pipeline.start() raises."""
        mock_engine = MagicMock()
        mock_engine.get_label_map.return_value = {0: "person"}
        mock_pipeline = MagicMock()
        mock_pipeline.start.side_effect = RuntimeError("start failed")

        with (
            patch("model_lens.app.load", return_value=mock_load_success),
            patch("model_lens.app.resolve_dist_dir", return_value=tmp_dist_dir),
            patch("model_lens.app.YOLOInferenceEngine", return_value=mock_engine),
            patch("model_lens.app.DetectionPipeline", return_value=mock_pipeline),
        ):
            with pytest.raises(_StartupExit) as exc_info:
                _startup()
        assert exc_info.value.code == 1
        mock_pipeline.stop.assert_called_once()


# ---------------------------------------------------------------------------
# lifespan — Happy Path
# ---------------------------------------------------------------------------


class TestLifespanHappyPath:
    """Happy Path — lifespan."""

    def test_lifespan_sets_state_and_yields(self) -> None:
        """Sets app.state.pipeline and app.state.engine then yields."""
        mock_engine = MagicMock()
        mock_pipeline = MagicMock()

        app = FastAPI(lifespan=lifespan)

        @app.get("/probe")
        def probe() -> dict[str, bool]:
            return {
                "pipeline_set": app.state.pipeline is mock_pipeline,
                "engine_set": app.state.engine is mock_engine,
            }

        with patch("model_lens.app._startup", return_value=(mock_engine, mock_pipeline)):
            with TestClient(app) as client:
                resp = client.get("/probe")
        assert resp.json() == {"pipeline_set": True, "engine_set": True}


# ---------------------------------------------------------------------------
# lifespan — State Transitions
# ---------------------------------------------------------------------------


class TestLifespanStateTransitions:
    """State Transitions — lifespan."""

    def test_lifespan_skips_when_pipeline_preset(self) -> None:
        """Yields immediately without running startup when app.state.pipeline is already set."""
        app = FastAPI(lifespan=lifespan)
        mock_pipeline = MagicMock()
        app.state.pipeline = mock_pipeline

        with patch("model_lens.app._startup") as mock_startup:
            with TestClient(app):
                pass
        mock_startup.assert_not_called()


# ---------------------------------------------------------------------------
# lifespan — Resource Cleanup
# ---------------------------------------------------------------------------


class TestLifespanResourceCleanup:
    """Resource Cleanup — lifespan."""

    def test_lifespan_shutdown_calls_stop_then_teardown(self) -> None:
        """On shutdown, calls pipeline.stop() then engine.teardown() in order."""
        mock_engine = MagicMock()
        mock_pipeline = MagicMock()
        call_order: list[str] = []
        mock_pipeline.stop.side_effect = lambda: call_order.append("stop")
        mock_engine.teardown.side_effect = lambda: call_order.append("teardown")

        app = FastAPI(lifespan=lifespan)

        with patch("model_lens.app._startup", return_value=(mock_engine, mock_pipeline)):
            with TestClient(app):
                pass  # Lifespan startup runs; exiting triggers shutdown

        assert call_order == ["stop", "teardown"]


# ---------------------------------------------------------------------------
# create_app — Happy Path (router inclusion)
# ---------------------------------------------------------------------------


class TestCreateAppRouterInclusion:
    """Happy Path — create_app (router inclusion)."""

    def test_create_app_includes_health_router(self, tmp_dist_dir_with_assets: Path) -> None:
        """The app contains the /healthz route."""
        with patch("model_lens.app.resolve_dist_dir", return_value=tmp_dist_dir_with_assets):
            app = create_app()
        route_paths = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/healthz" in route_paths

    def test_create_app_includes_config_router(self, tmp_dist_dir_with_assets: Path) -> None:
        """The app contains the /config route."""
        with patch("model_lens.app.resolve_dist_dir", return_value=tmp_dist_dir_with_assets):
            app = create_app()
        route_paths = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/config" in route_paths

    def test_create_app_includes_stream_router(self, tmp_dist_dir_with_assets: Path) -> None:
        """The app contains the /stream route."""
        with patch("model_lens.app.resolve_dist_dir", return_value=tmp_dist_dir_with_assets):
            app = create_app()
        route_paths = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/stream" in route_paths


# ---------------------------------------------------------------------------
# create_app — Happy Path (GET /)
# ---------------------------------------------------------------------------


class TestCreateAppGetIndex:
    """Happy Path — GET /."""

    def test_get_index_returns_html_with_etag(self, tmp_dist_dir_with_assets: Path) -> None:
        """Returns index.html content with correct Content-Type and ETag header."""
        html_content = b"<html></html>"
        (tmp_dist_dir_with_assets / "index.html").write_bytes(html_content)

        with patch("model_lens.app.resolve_dist_dir", return_value=tmp_dist_dir_with_assets):
            app = create_app()

        app.state.pipeline = MagicMock()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        expected_etag = '"' + hashlib.md5(html_content).hexdigest() + '"'
        assert response.headers["etag"] == expected_etag


# ---------------------------------------------------------------------------
# create_app — Happy Path (GET /favicon.svg)
# ---------------------------------------------------------------------------


class TestCreateAppGetFavicon:
    """Happy Path — GET /favicon.svg."""

    def test_get_favicon_returns_svg(self, tmp_dist_dir_with_assets: Path) -> None:
        """Returns favicon with SVG media type."""
        with patch("model_lens.app.resolve_dist_dir", return_value=tmp_dist_dir_with_assets):
            app = create_app()

        app.state.pipeline = MagicMock()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/favicon.svg")

        assert response.status_code == 200
        assert "image/svg+xml" in response.headers["content-type"]


# ---------------------------------------------------------------------------
# create_app — Happy Path (Static Assets)
# ---------------------------------------------------------------------------


class TestCreateAppStaticAssets:
    """Happy Path — Static Assets."""

    def test_create_app_mounts_static_assets(self, tmp_dist_dir_with_assets: Path) -> None:
        """Mounts /assets when dist/assets/ directory exists."""
        with patch("model_lens.app.resolve_dist_dir", return_value=tmp_dist_dir_with_assets):
            app = create_app()

        app.state.pipeline = MagicMock()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/assets/main.js")

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# create_app — Error Propagation
# ---------------------------------------------------------------------------


class TestCreateAppErrorPropagation:
    """Error Propagation — create_app."""

    def test_create_app_no_static_when_dist_missing(self) -> None:
        """Skips static route mounting when resolve_dist_dir() raises FileNotFoundError."""
        with patch("model_lens.app.resolve_dist_dir", side_effect=FileNotFoundError()):
            app = create_app()

        # API routes still present
        route_paths = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/healthz" in route_paths
        # No /assets mount — either /assets is absent or it has no sub-app
        assert "/assets" not in route_paths or all(
            not hasattr(r, "app") for r in app.routes if hasattr(r, "path") and r.path == "/assets"
        )

    def test_create_app_no_assets_mount_when_assets_dir_missing(self, tmp_path: Path) -> None:
        """Skips /assets mount when dist/assets/ does not exist."""
        dist = tmp_path / "dist"
        dist.mkdir()
        (dist / "index.html").write_text("<html></html>")
        (dist / "favicon.svg").write_text("<svg></svg>")
        # Do NOT create assets/ subdirectory

        with patch("model_lens.app.resolve_dist_dir", return_value=dist):
            app = create_app()

        app.state.pipeline = MagicMock()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/assets/anything.js")
        # Should 404 or not found
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# create_app — Exception Handlers
# ---------------------------------------------------------------------------


class TestCreateAppExceptionHandlers:
    """Happy Path — Exception Handlers."""

    def test_json_parse_error_returns_400(self, tmp_dist_dir_with_assets: Path) -> None:
        """Returns 400 with empty body for malformed JSON in request body."""
        with patch("model_lens.app.resolve_dist_dir", return_value=tmp_dist_dir_with_assets):
            app = create_app()

        app.state.pipeline = MagicMock()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.put(
            "/config/camera",
            content=b"not json{",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400
        assert response.content == b""

    def test_unhandled_exception_returns_500(self, tmp_dist_dir_with_assets: Path) -> None:
        """Returns 500 with generic error JSON for unhandled exceptions."""
        with patch("model_lens.app.resolve_dist_dir", return_value=tmp_dist_dir_with_assets):
            app = create_app()

        # Add a test route that raises an unhandled exception
        @app.get("/test-error")
        def raise_error() -> None:
            raise RuntimeError("unexpected")

        app.state.pipeline = MagicMock()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/test-error")
        assert response.status_code == 500
        assert response.json() == {"detail": "Internal Server Error"}

    def test_validation_error_non_json_returns_422(self, tmp_dist_dir_with_assets: Path) -> None:
        """Returns 422 for Pydantic validation errors that are not JSON parse errors."""
        with patch("model_lens.app.resolve_dist_dir", return_value=tmp_dist_dir_with_assets):
            app = create_app()

        app.state.pipeline = MagicMock()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.put(
            "/config/camera",
            json={"camera": {"source_type": "invalid"}},
        )
        assert response.status_code == 422
