import os
import threading
import time
from urllib.parse import quote

import requests

from .config import config

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"

DEFAULT_STYLE = (
    "anime style illustration, clean line art, soft cel shading, vibrant colors, "
    "cinematic lighting, highly detailed, vertical 9:16 composition, no text, no watermark"
)

_request_lock = threading.Lock()
_last_request_at = 0.0
MIN_REQUEST_GAP = 4.0


def _throttle() -> None:
    """Keep a minimum gap between requests so the free service does not rate limit us."""
    global _last_request_at
    with _request_lock:
        wait = MIN_REQUEST_GAP - (time.time() - _last_request_at)
        if wait > 0:
            time.sleep(wait)
        _last_request_at = time.time()


def _fetch_pollinations(prompt: str, out_path: str, seed: int, width: int, height: int, retries: int = 4) -> bool:
    url = POLLINATIONS_URL.format(prompt=quote(prompt, safe=""))
    params = {"width": width, "height": height, "seed": seed, "nologo": "true", "model": "flux"}
    for attempt in range(retries + 1):
        _throttle()
        try:
            resp = requests.get(url, params=params, timeout=240)
            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/"):
                with open(out_path, "wb") as f:
                    f.write(resp.content)
                return True
            print(f"  그림 요청 실패 (HTTP {resp.status_code}) 재시도 {attempt + 1}/{retries}")
        except requests.RequestException as e:
            print(f"  그림 요청 오류 ({type(e).__name__}) 재시도 {attempt + 1}/{retries}")
        time.sleep(8 * (attempt + 1))
    return False


def generate_scene_images(
    prompt: str,
    count: int,
    out_dir: str,
    style: str = DEFAULT_STYLE,
    seed_base: int = 0,
) -> list[str]:
    """Generate `count` images for one scene with Pollinations (free, no API key).

    Images that already exist in out_dir are reused so a re-run only fills the gaps.
    """
    os.makedirs(out_dir, exist_ok=True)
    full_prompt = f"{style}, {prompt}" if style else prompt

    paths = []
    for i in range(count):
        path = os.path.join(out_dir, f"gen_{i}.jpg")
        if os.path.exists(path) and os.path.getsize(path) > 10_000:
            paths.append(path)
            continue
        if _fetch_pollinations(full_prompt, path, seed_base + i, config.width, config.height):
            paths.append(path)
    return paths
