import os
import threading
import time
from urllib.parse import quote

import requests
from PIL import Image

from .cf_images import check_anatomy, fetch_cloudflare_image
from .config import config

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}"

DEFAULT_STYLE = (
    "anime style illustration with a subtle 3D rendered look. soft cel shading with volumetric lighting "
    "and gentle depth. correct anatomy with exactly two arms and two legs and natural hands. detailed. no text"
)

ANATOMY_RETRIES = 2

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
    backend: str = "pollinations",
    reference_paths: list[str] | None = None,
    check: bool = True,
) -> list[str]:
    """Generate `count` images for one scene.

    backend is "pollinations" (free without a key) or "cloudflare" (Workers AI with a key).
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
        seed = seed_base + i
        if backend == "cloudflare":
            ok = _cloudflare_with_check(full_prompt, path, seed, reference_paths, check)
        else:
            ok = _fetch_pollinations(full_prompt, path, seed, config.width, config.height)
        if ok:
            paths.append(path)
    return paths


def _cloudflare_with_check(prompt: str, path: str, seed: int, reference_paths, check: bool) -> bool:
    """Generate and then let the vision model reject broken anatomy. Retries with a new seed."""
    for attempt in range(ANATOMY_RETRIES + 1):
        ok = fetch_cloudflare_image(prompt, path, seed + attempt * 1000, config.width, config.height, reference_paths)
        if not ok:
            return False
        if not check:
            return True
        verdict = check_anatomy(path)
        if verdict is False and attempt < ANATOMY_RETRIES:
            print(f"  검수에서 팔다리 오류 발견. 다른 seed로 다시 그립니다 ({attempt + 1}/{ANATOMY_RETRIES})")
            continue
        if verdict is False:
            print("  재시도 후에도 오류가 남아 마지막 그림을 사용합니다")
        return True
    return True
