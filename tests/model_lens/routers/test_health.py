"""Tests for model_lens.routers.health — health endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

# Skip entire module if production router module is not yet implemented.
pytest.importorskip(
    "model_lens.routers.health",
    reason="Production module model_lens.routers.health not yet implemented",
)

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from model_lens.routers import health  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client() -> TestClient:
    """Create a TestClient with the health router mounted and lifespan bypassed."""
    app = FastAPI()
    app.include_router(health.router)
    app.state.pipeline = MagicMock()
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# GET /healthz — Happy Path
# ---------------------------------------------------------------------------


class TestHealthzHappyPath:
    """Happy Path — GET /healthz."""

    def test_healthz_returns_200(self, client: TestClient) -> None:
        """Returns 200 with empty body."""
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.content == b""
