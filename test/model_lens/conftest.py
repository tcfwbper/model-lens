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

"""Re-export shared fixtures so pytest discovers them from the fixtures package."""

from fixtures.camera_capture import (  # noqa: F401
    mock_cap_closed,
    mock_cap_opened,
    valid_bgr_frame,
)
from fixtures.config import (  # noqa: F401
    bundled_paths,
    minimal_toml_content,
    valid_app_config,
)
from fixtures.detection_pipeline import (  # noqa: F401
    default_config,
    mock_camera,
    mock_engine,
    pipeline,
)
from fixtures.entities import (  # noqa: F401
    default_runtime_config,
    local_camera_config,
    valid_detection_result,
    valid_frame,
    valid_frame_array,
)
from fixtures.inference_engine import (  # noqa: F401
    dummy_model_file,
    engine_with_mock_model,
    label_map_file,
)
