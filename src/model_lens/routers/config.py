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
"""Config router for ModelLens."""

from typing import Any, cast

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from model_lens.detection_pipeline import DetectionPipeline
from model_lens.entities import LocalCameraConfig, RtspCameraConfig, RuntimeConfig
from model_lens.inference_engine import YOLOInferenceEngine
from model_lens.schemas import LocalCameraRequest, UpdateCameraRequest, UpdateLabelsRequest

router = APIRouter()


def _serialize_config(config: RuntimeConfig) -> dict[str, Any]:
    camera = cast(LocalCameraConfig | RtspCameraConfig, config.camera)
    if isinstance(camera, LocalCameraConfig):
        cam_dict = {"source_type": "local", "device_index": camera.device_index}
    else:
        cam_dict = {"source_type": "rtsp", "rtsp_url": camera.rtsp_url}
    return {
        "camera": cam_dict,
        "confidence_threshold": config.confidence_threshold,
        "target_labels": config.target_labels,
    }


def _serialize_labels(label_map: dict[int, str]) -> dict[str, list[str]]:
    return {"valid_labels": list(label_map.values())}


@router.get("/config")
async def get_config(request: Request) -> JSONResponse:  # type: ignore[type-arg]
    """Return the current runtime configuration."""
    pipeline = cast(DetectionPipeline, request.app.state.pipeline)
    config = pipeline.get_config()
    return JSONResponse(_serialize_config(config))


@router.put("/config/camera")
async def put_camera(request: Request, body: UpdateCameraRequest) -> JSONResponse:  # type: ignore[type-arg]
    """Update the camera source configuration."""
    pipeline = cast(DetectionPipeline, request.app.state.pipeline)
    current = pipeline.get_config()

    camera_req = body.camera
    new_camera: LocalCameraConfig | RtspCameraConfig | None = None
    if isinstance(camera_req, LocalCameraRequest):
        new_camera = LocalCameraConfig(device_index=camera_req.device_index)
    else:
        new_camera = RtspCameraConfig(rtsp_url=camera_req.rtsp_url)

    new_config = RuntimeConfig(
        camera=new_camera,
        target_labels=current.target_labels,
        confidence_threshold=current.confidence_threshold,
    )
    pipeline.update_config(new_config)
    return JSONResponse(_serialize_config(pipeline.get_config()))


@router.get("/config/labels")
async def get_labels(request: Request) -> JSONResponse:  # type: ignore[type-arg]
    """Return the current target label filter."""
    engine = cast(YOLOInferenceEngine, request.app.state.engine)
    label_map = engine.get_label_map()
    return JSONResponse(_serialize_labels(label_map))


@router.put("/config/labels")
async def put_labels(request: Request, body: UpdateLabelsRequest) -> JSONResponse:  # type: ignore[type-arg]
    """Update the target label filter."""
    pipeline = cast(DetectionPipeline, request.app.state.pipeline)
    current = pipeline.get_config()

    new_config = RuntimeConfig(
        camera=current.camera,
        target_labels=body.target_labels,
        confidence_threshold=current.confidence_threshold,
    )
    pipeline.update_config(new_config)
    return JSONResponse(_serialize_config(pipeline.get_config()))
