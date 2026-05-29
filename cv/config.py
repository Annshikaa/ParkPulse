from pathlib import Path
from typing import Literal
from pydantic_settings import BaseSettings
from pydantic import Field


class CVConfig(BaseSettings):
    video_source: str = "sample_video.mp4"
    slots_path: Path = Path("data/parking_slots.json")
    weights_path: str = "yolov8n.pt"
    conf_threshold: float = 0.20        # lower for aerial/top-down camera angle
    iou_threshold: float = 0.45
    occupancy_iou_threshold: float = 0.05  # very low — any meaningful overlap counts
    enter_frames: int = 3               # faster to mark occupied
    exit_frames: int = 8                # slightly faster to mark free
    preprocessor_enabled: bool = True
    default_backend: Literal["pytorch", "onnx_fp32", "onnx_int8"] = "pytorch"

    model_config = {"env_prefix": "CV_", "env_file": ".env", "extra": "ignore"}


cv_config = CVConfig()
