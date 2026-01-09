"""
Digigami Backend Configuration
"""
from pydantic_settings import BaseSettings
from typing import Optional
import torch


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Server
    host: str = "0.0.0.0"
    port: int = 8765
    debug: bool = True

    # CORS
    cors_origins: list[str] = ["http://localhost:8080", "http://127.0.0.1:8080", "https://digigami.me"]

    # Model paths
    weights_dir: str = "weights"

    # Style transfer settings
    default_style: str = "kingdom-hearts"
    output_size: int = 512

    # Processing
    max_image_size: int = 1280
    jpeg_quality: int = 90

    # Device
    device: str = "cuda" if torch.cuda.is_available() else "cpu"

    # 3D Generation API Keys
    tripo3d_api_key: Optional[str] = None
    meshy_api_key: Optional[str] = None
    makergrid_token: Optional[str] = None  # Friend's platform at makergrid.ai

    # 3D Generation Settings
    gen3d_output_dir: str = "outputs/3d"
    gen3d_default_backend: str = "makergrid"  # makergrid (preferred), tripo3d, or meshy
    gen3d_poll_interval: float = 3.0
    gen3d_timeout: float = 600.0  # 10 minutes

    class Config:
        env_file = ".env"
        env_prefix = "DIGIGAMI_"


settings = Settings()


# Style configurations
STYLE_CONFIGS = {
    "kingdom-hearts": {
        "name": "Kingdom Hearts",
        "description": "Vibrant anime style inspired by Kingdom Hearts series",
        "model": "kh_style_v1",
        "color_palette": ["#6B5CE7", "#00D9FF", "#FFD700"],
        "strength": 0.8
    },
    "dark-cloud": {
        "name": "Dark Cloud 2",
        "description": "Cel-shaded style from Dark Cloud 2 / Dark Chronicle",
        "model": "dc2_style_v1",
        "color_palette": ["#FF6B35", "#4ECDC4", "#2C3E50"],
        "strength": 0.85
    },
    "ghibli": {
        "name": "Studio Ghibli",
        "description": "Soft, painterly style inspired by Studio Ghibli films",
        "model": "ghibli_style_v1",
        "color_palette": ["#87CEEB", "#98D8C8", "#F7DC6F"],
        "strength": 0.7
    },
    "cel-shade": {
        "name": "Cel Shade",
        "description": "Bold cel-shaded cartoon style with hard edges",
        "model": "celshade_v1",
        "color_palette": ["#E74C3C", "#3498DB", "#2ECC71"],
        "strength": 0.9
    }
}
