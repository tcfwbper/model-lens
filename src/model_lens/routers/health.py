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

"""Health router — minimal liveness endpoint.

Provides a single ``GET /healthz`` endpoint that returns 200 OK with no body.
Does not check pipeline status, camera connectivity, or any other runtime health
indicator.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter()


@router.get("/healthz")
def healthz() -> Response:
    """Return 200 OK with no body.

    Returns:
        Response with status_code=200 and empty body.
    """
    return Response(status_code=200)
