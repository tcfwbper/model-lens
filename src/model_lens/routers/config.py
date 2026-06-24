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

"""Config router — endpoints for reading and updating RuntimeConfig at runtime.

All mutations trigger ``DetectionPipeline.update_config()`` so changes take
effect immediately without restarting the server.
"""

from __future__ import annotations

from typing import Any, cast

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from model_lens.detection_pipeline import DetectionPipeline
from model_lens.entities.camera_config import LocalCameraConfig, RtspCameraConfig
from model_lens.entities.runtime_config import RuntimeConfig
from model_lens.inference_engine import InferenceEngine
from model_lens.schemas import LocalCameraRequest, UpdateCameraRequest, UpdateLabelsRequest

router = APIRouter()


def _serialize_config(config: RuntimeConfig) -> dict[str, Any]:
    """Serialize a RuntimeConfig to a JSON-friendly dictionary.

    Args:
        config: The RuntimeConfig to serialize.

    Returns:
        A dictionary suitable for JSON response.
    """
    if isinstance(config.camera, LocalCameraConfig):
        cam_dict: dict[str, Any] = {"source_type": "local", "device_index": config.camera.device_index}
    else:
        cam_dict = {"source_type": "rtsp", "rtsp_url": cast(RtspCameraConfig, config.camera).rtsp_url}

    return {
        "camera": cam_dict,
        "confidence_threshold": config.confidence_threshold,
        "target_labels": config.target_labels,
    }


def _serialize_labels(label_map: dict[int, str]) -> dict[str, Any]:
    """Serialize a label map to a JSON-friendly dictionary.

    Args:
        label_map: Mapping of class indices to label strings.

    Returns:
        A dictionary with valid_labels list.
    """
    return {"valid_labels": list(label_map.values())}


@router.get("/config")
def get_config(request: Request) -> JSONResponse:  # type: ignore[type-arg]
    """Return the current RuntimeConfig as JSON.

    Args:
        request: The incoming HTTP request.

    Returns:
        JSONResponse with serialized config.
    """
    pipeline = cast(DetectionPipeline, request.app.state.pipeline)
    config = pipeline.get_config()
    return JSONResponse(_serialize_config(config))


@router.put("/config/camera")
def put_camera(request: Request, body: UpdateCameraRequest) -> JSONResponse:  # type: ignore[type-arg]
    """Update the camera configuration.

    Args:
        request: The incoming HTTP request.
        body: The validated camera update request.

    Returns:
        JSONResponse with the updated config.
    """
    pipeline = cast(DetectionPipeline, request.app.state.pipeline)
    current = pipeline.get_config()

    if isinstance(body.camera, LocalCameraRequest):
        new_camera: LocalCameraConfig | RtspCameraConfig = LocalCameraConfig(device_index=body.camera.device_index)
    else:
        new_camera = RtspCameraConfig(rtsp_url=body.camera.rtsp_url)

    new_config = RuntimeConfig(
        camera=new_camera,
        target_labels=current.target_labels,
        confidence_threshold=current.confidence_threshold,
    )
    pipeline.update_config(new_config)
    updated = pipeline.get_config()
    return JSONResponse(_serialize_config(updated))


@router.get("/config/labels")
def get_labels(request: Request) -> JSONResponse:  # type: ignore[type-arg]
    """Return all valid labels from the engine's label map.

    Args:
        request: The incoming HTTP request.

    Returns:
        JSONResponse with valid_labels list.
    """
    engine = cast(InferenceEngine, request.app.state.engine)
    label_map = engine.get_label_map()
    return JSONResponse(_serialize_labels(label_map))


@router.put("/config/labels")
def put_labels(request: Request, body: UpdateLabelsRequest) -> JSONResponse:  # type: ignore[type-arg]
    """Update the target labels.

    Args:
        request: The incoming HTTP request.
        body: The validated labels update request.

    Returns:
        JSONResponse with the updated config.
    """
    pipeline = cast(DetectionPipeline, request.app.state.pipeline)
    current = pipeline.get_config()

    new_config = RuntimeConfig(
        camera=current.camera,
        target_labels=body.target_labels,
        confidence_threshold=current.confidence_threshold,
    )
    pipeline.update_config(new_config)
    updated = pipeline.get_config()
    return JSONResponse(_serialize_config(updated))
