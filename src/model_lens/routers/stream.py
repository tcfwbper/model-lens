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
"""Stream router for ModelLens (SSE)."""

import base64
import json
import queue
import time
from collections.abc import Generator
from typing import cast

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from model_lens.detection_pipeline import DetectionPipeline

router = APIRouter()

_IDLE_TIMEOUT = 30.0
_KEEPALIVE_INTERVAL = 30.0
_QUEUE_TIMEOUT = 1.0
# Module-level alias so tests can patch only the stream module's time source
# without touching the global ``time`` module (which would break anyio).
_monotonic = time.monotonic


def _event_generator(pipeline: DetectionPipeline) -> Generator[bytes, None, None]:
    last_frame_time = _monotonic()
    last_keepalive_time = last_frame_time

    try:
        while True:
            # get detection result
            try:
                result = pipeline.get_queue().get(timeout=_QUEUE_TIMEOUT)
            except queue.Empty:
                result = None

            now = _monotonic()

            if result is not None:
                last_frame_time = now
                detections = [
                    {
                        "label": d.label,
                        "confidence": d.confidence,
                        "bounding_box": list(d.bounding_box),
                        "is_target": d.is_target,
                    }
                    for d in result.detections
                ]
                payload = json.dumps(
                    {
                        "jpeg_b64": base64.b64encode(result.jpeg_bytes).decode(),
                        "timestamp": result.timestamp,
                        "source": result.source,
                        "detections": detections,
                    }
                )
                yield f"data: {payload}\n\n".encode()
            else:
                if now - last_keepalive_time >= _KEEPALIVE_INTERVAL:
                    last_keepalive_time = now
                    yield b": keepalive\n\n"
                if now - last_frame_time >= _IDLE_TIMEOUT:
                    return
    finally:
        pass  # generator teardown; extend here for resource cleanup


@router.get("/stream")
async def stream(request: Request) -> StreamingResponse:  # type: ignore[type-arg]
    """Stream detection frames as Server-Sent Events."""
    pipeline = cast(DetectionPipeline, request.app.state.pipeline)
    return StreamingResponse(
        _event_generator(pipeline),
        media_type="text/event-stream",
    )
