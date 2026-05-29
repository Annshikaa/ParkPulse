from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    video_source: str = "sample_video.mp4"
    slots_path: Path = Path("data/parking_slots.json")
    db_url: str = "sqlite:///./parkpulse.db"
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    jwt_secret: str = "CHANGE_ME_IN_PROD_USE_LONG_RANDOM_STRING"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    price_per_hour_inr: float = 50.0
    log_level: str = "INFO"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
