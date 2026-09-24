import os
import threading
import time
from urllib.parse import quote

import requests
from PIL import Image

from .config import config

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"

DEFAULT_STYLE = "anime style illustration. soft cel shading. detailed. no text"

# Pollinations stamps a small logo at the bottom right. Cut that strip off.
LOGO_CROP_RATIO = 0.06

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


MODEL_ORDER = ["flux", "turbo", None]


def _crop_logo(path: str) -> None:
    try:
        img = Image.open(path).convert("RGB")
        keep = int(img.height * (1 - LOGO_CROP_RATIO))
        img.crop((0, 0, img.width, keep)).save(path, quality=92)
    except Exception as e:
        print(f"  로고 자르기 실패 ({type(e).__name__})")


def _fetch_pollinations(prompt: str, out_path: str, seed: int, width: int, height: int, retries: int = 4) -> bool:
    url = POLLINATIONS_URL.format(prompt=quote(prompt, safe=""))
    for attempt in range(retries + 1):
        model = MODEL_ORDER[min(attempt // 2, len(MODEL_ORDER) - 1)]
        params = {"width": width, "height": height, "seed": seed, "nologo": "true"}
        if model:
            params["model"] = model
        _throttle()
        try:
            resp = requests.get(url, params=params, timeout=240)
            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/"):
                with open(out_path, "wb") as f:
                    f.write(resp.content)
                _crop_logo(out_path)
                return True
            body = resp.text[:160].replace("\n", " ")
            print(f"  그림 요청 실패 (HTTP {resp.status_code} model={model or 'default'}) {body}")
        except requests.RequestException as e:
            print(f"  그림 요청 오류 ({type(e).__name__} model={model or 'default'})")
        if attempt < retries:
            print(f"  재시도 {attempt + 1}/{retries}")
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
    # The scene prompt goes first. Image models read only the first few dozen tokens
    # so the character look must not be pushed behind a long style string.
    full_prompt = f"{prompt}. {style}" if style else prompt

    paths = []
    for i in range(count):
        path = os.path.join(out_dir, f"gen_{i}.jpg")
        if os.path.exists(path) and os.path.getsize(path) > 10_000:
            paths.append(path)
            continue
        if _fetch_pollinations(full_prompt, path, seed_base + i, config.width, config.height):
            paths.append(path)
    return paths
