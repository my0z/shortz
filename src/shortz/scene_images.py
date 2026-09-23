import os
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

import requests

from .config import config

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"

DEFAULT_STYLE = (
    "anime style illustration, clean line art, soft cel shading, vibrant colors, "
    "cinematic lighting, highly detailed, vertical 9:16 composition, no text, no watermark"
)


def _fetch_pollinations(prompt: str, out_path: str, seed: int, width: int, height: int, retries: int = 2) -> bool:
    url = POLLINATIONS_URL.format(prompt=quote(prompt, safe=""))
    params = {"width": width, "height": height, "seed": seed, "nologo": "true", "model": "flux"}
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=180)
            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/"):
                with open(out_path, "wb") as f:
                    f.write(resp.content)
                return True
        except requests.RequestException:
            pass
        time.sleep(3 * (attempt + 1))
    return False


def generate_scene_images(
    prompt: str,
    count: int,
    out_dir: str,
    style: str = DEFAULT_STYLE,
    seed_base: int = 0,
    workers: int = 3,
) -> list[str]:
    """Generate `count` images for one scene with Pollinations (free, no API key)."""
    os.makedirs(out_dir, exist_ok=True)
    full_prompt = f"{style}, {prompt}" if style else prompt

    def job(i: int) -> str | None:
        path = os.path.join(out_dir, f"gen_{i}.jpg")
        ok = _fetch_pollinations(full_prompt, path, seed_base + i, config.width, config.height)
        return path if ok else None

    with ThreadPoolExecutor(max_workers=min(workers, count)) as executor:
        results = list(executor.map(job, range(count)))
    return [p for p in results if p]
