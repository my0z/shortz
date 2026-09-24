import base64
import io
import json
import time

import requests
from PIL import Image

from .config import config

CF_RUN_URL = "https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/{model}"

# Models that take multipart form input and support reference images.
MULTIPART_MODELS = ("flux-2-klein", "flux-2-dev")
# Models that only take a prompt and steps and always return 1024x1024.
SQUARE_ONLY_MODELS = ("flux-1-schnell",)

REFERENCE_MAX_SIDE = 500


def _round16(value: int) -> int:
    return ((value + 15) // 16) * 16


def _reference_bytes(path: str) -> bytes:
    img = Image.open(path).convert("RGB")
    img.thumbnail((REFERENCE_MAX_SIDE, REFERENCE_MAX_SIDE))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _decode_image(resp: requests.Response) -> bytes | None:
    ctype = resp.headers.get("content-type", "")
    if ctype.startswith("image/"):
        return resp.content
    try:
        data = resp.json()
    except ValueError:
        return None
    result = data.get("result") or {}
    b64 = result.get("image") if isinstance(result, dict) else None
    return base64.b64decode(b64) if b64 else None


def _error_text(resp: requests.Response) -> str:
    try:
        data = resp.json()
        errors = data.get("errors") or []
        if errors:
            return "; ".join(f"{e.get('code')} {e.get('message')}" for e in errors)[:200]
    except ValueError:
        pass
    return resp.text[:200].replace("\n", " ")


def _fit_to_size(raw: bytes, width: int, height: int) -> Image.Image:
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    if img.size == (width, height):
        return img
    scale = max(width / img.width, height / img.height)
    resized = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    left = (resized.width - width) // 2
    top = (resized.height - height) // 2
    return resized.crop((left, top, left + width, top + height))


def fetch_cloudflare_image(
    prompt: str,
    out_path: str,
    seed: int,
    width: int,
    height: int,
    reference_paths: list[str] | None = None,
    model: str | None = None,
    retries: int = 2,
) -> bool:
    """Generate one image with Cloudflare Workers AI and save it at exactly width x height."""
    if not config.cloudflare_account_id or not config.cloudflare_api_token:
        print("  CLOUDFLARE_ACCOUNT_ID 또는 CLOUDFLARE_API_TOKEN 이 .env 에 없습니다.")
        return False
    model = model or config.cloudflare_image_model
    url = CF_RUN_URL.format(account=config.cloudflare_account_id, model=model)
    headers = {"Authorization": f"Bearer {config.cloudflare_api_token}"}
    seed = int(seed) % 2_000_000_000
    multipart = any(key in model for key in MULTIPART_MODELS)
    square_only = any(key in model for key in SQUARE_ONLY_MODELS)

    for attempt in range(retries + 1):
        try:
            if multipart:
                fields = {
                    "prompt": (None, prompt),
                    "width": (None, str(_round16(width))),
                    "height": (None, str(_round16(height))),
                    "seed": (None, str(seed)),
                }
                for i, ref in enumerate((reference_paths or [])[:4]):
                    fields[f"input_image_{i}"] = (f"ref{i}.png", _reference_bytes(ref), "image/png")
                resp = requests.post(url, headers=headers, files=fields, timeout=180)
            elif square_only:
                body = {"prompt": prompt, "steps": 8, "seed": seed}
                resp = requests.post(url, headers=headers, json=body, timeout=180)
            else:
                body = {
                    "prompt": prompt,
                    "width": width if width % 8 == 0 else _round16(width),
                    "height": height if height % 8 == 0 else _round16(height),
                    "num_steps": 20,
                    "guidance": 7.5,
                    "seed": seed,
                }
                resp = requests.post(url, headers=headers, json=body, timeout=180)

            if resp.status_code == 200:
                raw = _decode_image(resp)
                if raw:
                    _fit_to_size(raw, width, height).save(out_path, quality=94)
                    return True
                print("  응답에 이미지가 없습니다.")
            else:
                print(f"  Cloudflare 요청 실패 (HTTP {resp.status_code}) {_error_text(resp)}")
                if resp.status_code in (401, 403):
                    return False
                if resp.status_code == 429:
                    print("  하루 무료 한도(10000 뉴런)를 넘었거나 요청이 너무 잦습니다.")
        except requests.RequestException as e:
            print(f"  Cloudflare 요청 오류 ({type(e).__name__})")
        if attempt < retries:
            time.sleep(5 * (attempt + 1))
    return False
