import json
import os
import re

from PIL import Image, ImageDraw, ImageFont

from .config import config
from .scene_images import DEFAULT_STYLE, generate_scene_images

CHARACTER_SHEET_PROMPT = "{look}. full body front view standing. plain light background. clear face"

NAME_PATTERN = re.compile(r"\{([^{}]+)\}")

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
]


def load_scene_file(path: str) -> tuple[list[dict], dict, dict]:
    """Read a scene JSON file.

    Old format: a plain list of scenes.
    New format: {"characters": {...}, "narrator": {...}, "style": "...", "scenes": [...]}.
    Returns (scenes, characters, meta).
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data, {}, {}
    scenes = data.get("scenes", [])
    characters = data.get("characters", {}) or {}
    meta = {k: v for k, v in data.items() if k not in ("scenes", "characters")}
    return scenes, characters, meta


def referenced_names(prompt: str, characters: dict) -> list[str]:
    return [name for name in NAME_PATTERN.findall(prompt) if name in characters]


def expand_prompt(prompt: str, characters: dict, reference_names: list[str] | None = None) -> str:
    """Replace {name} with that character's look description.

    When reference_names is given the names are also tied to reference image
    indexes so the model can copy the face from the attached images.
    """
    reference_names = reference_names or []

    def _sub(match):
        name = match.group(1)
        info = characters.get(name)
        if not info:
            return match.group(0)
        look = info.get("look", name)
        if name in reference_names:
            return f"{look} (exactly the character shown in image {reference_names.index(name)})"
        return look

    return NAME_PATTERN.sub(_sub, prompt)


def character_reference_paths(prompt: str, characters: dict, sheet_dir: str) -> tuple[list[str], list[str]]:
    """Reference sheet images for the characters named in prompt. Returns (names, paths)."""
    names, paths = [], []
    for name in referenced_names(prompt, characters):
        path = os.path.join(sheet_dir, name, "gen_0.jpg")
        if os.path.exists(path) and len(paths) < 4:
            names.append(name)
            paths.append(path)
    return names, paths


def character_seed(prompt: str, characters: dict, fallback: int) -> int:
    names = referenced_names(prompt, characters)
    if not names:
        return fallback
    return int(characters[names[0]].get("seed", 0)) * 1000 + (fallback % 1000)


def _load_font(size: int):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def build_character_sheet(
    characters: dict, out_dir: str, style: str = DEFAULT_STYLE, backend: str = "pollinations"
) -> str | None:
    """Generate one reference image per character and tile them into a single sheet."""
    if not characters:
        print("characters 항목이 없습니다.")
        return None
    os.makedirs(out_dir, exist_ok=True)
    tiles = []
    for name, info in characters.items():
        look = info.get("look", "")
        seed = int(info.get("seed", 0)) * 1000
        prompt = CHARACTER_SHEET_PROMPT.format(look=look)
        print(f"캐릭터 '{name}' 시트 생성 중 (seed {seed})...")
        char_dir = os.path.join(out_dir, name)
        paths = generate_scene_images(prompt, 1, char_dir, style, seed, backend)
        if paths:
            tiles.append((name, paths[0]))
        else:
            print(f"캐릭터 '{name}' 생성 실패")
    if not tiles:
        return None

    tile_w, tile_h, label_h = 540, 960, 80
    sheet = Image.new("RGB", (tile_w * len(tiles), tile_h + label_h), (245, 245, 245))
    draw = ImageDraw.Draw(sheet)
    font = _load_font(44)
    for i, (name, path) in enumerate(tiles):
        img = Image.open(path).convert("RGB")
        img.thumbnail((tile_w, tile_h))
        x = i * tile_w + (tile_w - img.width) // 2
        sheet.paste(img, (x, label_h))
        draw.text((i * tile_w + 24, 18), name, fill=(20, 20, 20), font=font)
    sheet_path = os.path.join(out_dir, "character_sheet.jpg")
    sheet.save(sheet_path, quality=90)
    return sheet_path
