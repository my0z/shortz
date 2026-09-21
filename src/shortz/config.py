import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    tts_voice: str = os.getenv("TTS_VOICE", "ko-KR-SunHiNeural")
    width: int = int(os.getenv("VIDEO_WIDTH", "1080"))
    height: int = int(os.getenv("VIDEO_HEIGHT", "1920"))
    fps: int = int(os.getenv("VIDEO_FPS", "30"))
    output_dir: str = "output"
    assets_dir: str = "assets"


config = Config()
