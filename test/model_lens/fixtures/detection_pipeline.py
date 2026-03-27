import numpy as np
import pytest

from model_lens.entities import Frame, RuntimeConfig


@pytest.fixture
def mock_engine(mocker):
    """A mock InferenceEngine that returns an empty detection list by default."""
    engine = mocker.MagicMock()
    engine.detect.return_value = []
    return engine


@pytest.fixture
def default_config():
    """A RuntimeConfig using the default LocalCameraConfig."""
    return RuntimeConfig()


@pytest.fixture
def mock_camera(mocker):
    """A mock CameraCapture instance that returns a valid Frame by default."""
    camera = mocker.MagicMock()
    camera.read.return_value = Frame(
        data=np.zeros((480, 640, 3), dtype=np.uint8),
        timestamp=1748000400.0,
        source="local:0",
    )
    return camera


@pytest.fixture
def pipeline(mock_engine, default_config, mock_camera, mocker):
    """
    A fully constructed DetectionPipeline with the initial CameraCapture
    replaced by mock_camera. The background thread is NOT started.
    """
    mocker.patch(
        "model_lens.detection_pipeline.LocalCamera",
        return_value=mock_camera,
    )
    from model_lens.detection_pipeline import DetectionPipeline

    p = DetectionPipeline(engine=mock_engine, initial_config=default_config)
    return p
