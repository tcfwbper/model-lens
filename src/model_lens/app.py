# Copyright 2026 ModelLens Contributors
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

"""FastAPI application entry point — lifecycle, routing, and error handling.

Owns the server lifecycle, mounts all API routers and static assets, wires
together the DetectionPipeline, YOLOInferenceEngine, and RuntimeConfig into a
single running process.
"""

from __future__ import annotations

import hashlib
import importlib.resources
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from model_lens.config import load
from model_lens.detection_pipeline import DetectionPipeline
from model_lens.entities.camera_config import LocalCameraConfig
from model_lens.entities.runtime_config import RuntimeConfig
from model_lens.exceptions import ConfigurationError, OperationError
from model_lens.inference_engine import YOLOInferenceEngine
from model_lens.routers import config, health, stream

logger = logging.getLogger(__name__)


class _StartupExit(SystemExit, Exception):
    """Clean exit propagation through anyio task groups.

    Inherits from both SystemExit and Exception so it propagates cleanly
    through anyio's task groups instead of being wrapped in a BaseExceptionGroup.
    """


def resolve_dist_dir() -> Path:
    """Resolve the package's dist directory path.

    Uses importlib.resources.files to locate the model_lens package directory
    and returns the dist subdirectory path.

    Returns:
        Path to the dist directory.
    """
    pkg = importlib.resources.files("model_lens")
    return Path(str(pkg)) / "dist"


def get_pipeline(request: Request) -> DetectionPipeline:  # type: ignore[type-arg]
    """FastAPI dependency that returns the pipeline from app state.

    Args:
        request: The incoming HTTP request.

    Returns:
        The DetectionPipeline instance stored in app.state.
    """
    return request.app.state.pipeline  # type: ignore[no-any-return]


def _startup() -> tuple[YOLOInferenceEngine, DetectionPipeline]:
    """Execute the startup sequence.

    Loads config, resolves dist directory, constructs engine and pipeline,
    and starts the pipeline.

    Returns:
        Tuple of (engine, pipeline) on success.

    Raises:
        _StartupExit: On any startup failure (exit code 1).
    """
    # Step 1: Load config
    try:
        app_config = load()
    except (ConfigurationError, FileNotFoundError) as exc:
        logger.critical("Configuration load failed: %s", exc)
        raise _StartupExit(1) from exc

    # Step 2: Resolve dist dir
    try:
        dist_dir = resolve_dist_dir()
    except FileNotFoundError as exc:
        logger.critical("dist directory not found: %s", exc)
        raise _StartupExit(1) from exc

    # Step 3: Check index.html exists
    if not (dist_dir / "index.html").exists():
        logger.critical("dist/index.html not found")
        raise _StartupExit(1)

    # Step 4: Construct engine
    try:
        engine = YOLOInferenceEngine(
            model=app_config.model.model,
            confidence_threshold=app_config.model.confidence_threshold,
        )
    except (ConfigurationError, OperationError) as exc:
        logger.critical("Engine construction failed: %s", exc)
        raise _StartupExit(1) from exc

    # Step 5: Construct initial RuntimeConfig
    initial_config = RuntimeConfig(
        camera=LocalCameraConfig(device_index=app_config.camera.device_index),
        target_labels=list(engine.get_label_map().values()),
        confidence_threshold=app_config.model.confidence_threshold,
    )

    # Step 6: Construct and start pipeline
    pipeline = DetectionPipeline(engine=engine, initial_config=initial_config)
    try:
        pipeline.start()
    except Exception as exc:
        logger.critical("Pipeline start failed: %s", exc)
        pipeline.stop()
        raise _StartupExit(1) from exc

    return (engine, pipeline)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager.

    Handles startup (engine + pipeline construction) and shutdown (cleanup).
    Skips all logic if app.state.pipeline is already set (test injection).

    Args:
        app: The FastAPI application instance.

    Yields:
        None — application serves requests while yielded.
    """
    if hasattr(app.state, "pipeline"):
        yield
        return

    engine, pipeline = _startup()
    app.state.pipeline = pipeline
    app.state.engine = engine

    try:
        yield
    finally:
        pipeline.stop()
        engine.teardown()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Constructs the app with lifespan, registers exception handlers, includes
    routers, and mounts static files when available.

    Returns:
        Fully configured FastAPI application instance.
    """
    app = FastAPI(lifespan=lifespan)

    # Exception handlers
    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(request: Request, exc: RequestValidationError) -> Response:  # type: ignore[type-arg]
        """Handle request validation errors.

        Returns 400 for JSON parse errors, delegates otherwise.
        """
        for error in exc.errors():
            if error.get("type") == "json_invalid":
                return Response(status_code=400)
        # Delegate to FastAPI's default handler for non-JSON errors
        from fastapi.exception_handlers import request_validation_exception_handler

        return await request_validation_exception_handler(request, exc)

    @app.exception_handler(Exception)
    async def _generic_error_handler(request: Request, exc: Exception) -> JSONResponse:  # type: ignore[type-arg]
        """Handle unhandled exceptions with a 500 response."""
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

    # Include routers
    app.include_router(health.router)
    app.include_router(config.router)
    app.include_router(stream.router)

    # Static files
    try:
        dist_dir = resolve_dist_dir()
    except FileNotFoundError:
        return app

    if (dist_dir / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(dist_dir / "assets")), name="static_assets")

    @app.get("/favicon.svg", include_in_schema=False)
    def favicon() -> FileResponse:
        """Serve the favicon."""
        return FileResponse(str(dist_dir / "favicon.svg"), media_type="image/svg+xml")

    @app.get("/", include_in_schema=False)
    def index() -> Response:
        """Serve the index.html with ETag."""
        content = (dist_dir / "index.html").read_bytes()
        etag = '"' + hashlib.md5(content).hexdigest() + '"'
        return Response(content=content, media_type="text/html", headers={"etag": etag})

    return app
