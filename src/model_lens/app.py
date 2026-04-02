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
"""FastAPI application factory for ModelLens."""

import hashlib
import importlib.resources
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import cast

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from model_lens.config import load
from model_lens.detection_pipeline import DetectionPipeline
from model_lens.entities import LocalCameraConfig, RuntimeConfig
from model_lens.exceptions import ConfigurationError, OperationError
from model_lens.inference_engine import YOLOInferenceEngine
from model_lens.routers import config, health, stream


def resolve_dist_dir() -> Path:
    """Return the path to the bundled frontend dist directory."""
    pkg = importlib.resources.files("model_lens")
    return Path(str(pkg)) / "dist"


def get_pipeline(request: Request) -> DetectionPipeline:  # type: ignore[type-arg]
    """Return the pipeline instance from app state."""
    return cast(DetectionPipeline, request.app.state.pipeline)


class _StartupExit(SystemExit, Exception):
    """SystemExit subclass that also inherits from Exception.

    This ensures the exit propagates cleanly through anyio's task groups instead of being wrapped in a
    BaseExceptionGroup.
    """


def _startup() -> tuple[YOLOInferenceEngine, DetectionPipeline]:
    """Run synchronous startup logic.

    Returns (engine, pipeline) or raises _StartupExit(1).
    """
    try:
        app_config = load()
    except (ConfigurationError, FileNotFoundError) as err:
        raise _StartupExit(1) from err

    try:
        dist_dir = resolve_dist_dir()
    except FileNotFoundError as err:
        raise _StartupExit(1) from err

    if not (dist_dir / "index.html").exists():
        raise _StartupExit(1)

    try:
        engine = YOLOInferenceEngine(
            model=app_config.model.model,
            confidence_threshold=app_config.model.confidence_threshold,
        )
    except (ConfigurationError, OperationError) as err:
        raise _StartupExit(1) from err

    initial_config = RuntimeConfig(
        camera=LocalCameraConfig(
            device_index=app_config.camera.device_index,
        ),
        target_labels=list(engine.get_label_map().values()),
        confidence_threshold=app_config.model.confidence_threshold,
    )

    pipeline = DetectionPipeline(
        engine=engine,
        initial_config=initial_config,
    )

    try:
        pipeline.start()
    except Exception as err:
        pipeline.stop()
        raise _StartupExit(1) from err

    return engine, pipeline


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown."""
    # If pipeline is already set (e.g. by tests), skip startup/shutdown.
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
    """Create and configure the FastAPI application."""
    app = FastAPI(lifespan=lifespan)

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError) -> Response:  # type: ignore[type-arg]
        for error in exc.errors():
            if error.get("type") == "json_invalid":
                return Response(status_code=400)
        return await request_validation_exception_handler(request, exc)

    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(  # pylint: disable=unused-argument
        request: Request, exc: Exception  # type: ignore[type-arg]
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error"},
        )

    app.include_router(health.router)
    app.include_router(config.router)
    app.include_router(stream.router)

    try:
        dist_dir = resolve_dist_dir()
    except FileNotFoundError:
        return app

    static_dir = dist_dir / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    index_html = dist_dir / "index.html"

    @app.get("/", include_in_schema=False)
    async def _root() -> Response:
        content = index_html.read_bytes()
        etag = f'"{hashlib.md5(content).hexdigest()}"'
        return Response(
            content=content,
            media_type="text/html",
            headers={"etag": etag},
        )

    return app
