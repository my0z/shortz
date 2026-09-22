import os
import random

import requests

from .config import config

BACKGROUND_VIDEOS = [
    "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
    "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4",
    "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerFun.mp4",
    "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4",
    "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerMeltdowns.mp4",
    "https://storage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4",
]


def fetch_random_background(out_path: str) -> str:
    seed = random.randint(1, 100000)
    url = f"https://picsum.photos/seed/{seed}/{config.width}/{config.height}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    with open(out_path, "wb") as f:
        f.write(response.content)
    return out_path


def fetch_random_background_video(out_path: str) -> str:
    url = random.choice(BACKGROUND_VIDEOS)
    response = requests.get(url, timeout=60, stream=True)
    response.raise_for_status()
    with open(out_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024 * 256):
            f.write(chunk)
    return out_path
