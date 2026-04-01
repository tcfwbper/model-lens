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

import importlib.resources
from pathlib import Path

from fastapi import FastAPI
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from model_lens.routers import config, health, stream


def resolve_dist_dir() -> Path:
    """Return the path to the bundled frontend dist directory."""
    pkg = importlib.resources.files("model_lens")
    return Path(str(pkg)) / "dist"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI()

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request, exc):
        for error in exc.errors():
            if error.get("type") == "json_invalid":
                return Response(status_code=400)
        return await request_validation_exception_handler(request, exc)

    app.include_router(health.router)
    app.include_router(config.router)
    app.include_router(stream.router)

    dist_dir = resolve_dist_dir()
    static_dir = dist_dir / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    index_html = dist_dir / "index.html"

    @app.get("/{full_path:path}", include_in_schema=False)
    async def _spa_fallback(full_path: str):
        return FileResponse(str(index_html))

    return app
