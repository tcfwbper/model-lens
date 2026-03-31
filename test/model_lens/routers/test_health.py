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

"""Tests for model_lens.routers.health."""

import pytest
from fastapi.testclient import TestClient


class TestHealthz:
    """Tests for GET /healthz."""

    def test_healthz_returns_200(self, client: TestClient):
        response = client.get("/healthz")
        assert response.status_code == 200

    def test_healthz_returns_empty_body(self, client: TestClient):
        response = client.get("/healthz")
        assert response.content == b""
