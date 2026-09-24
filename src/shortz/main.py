import argparse
import json
import os

from .audio import mix_narration_with_music
from .background import fetch_random_background
from .characters import (
    build_character_sheet,
    character_reference_paths,
    character_seed,
    expand_prompt,
    load_scene_file,
)
from .config import config
from .scene_images import DEFAULT_STYLE, generate_scene_images
from .topic_images import fetch_topic_images
from .topic_videos import fetch_topic_videos
from .tts import VOICE_PRESETS, synthesize_scenes, synthesize_sync
from .video import FONT_PRESETS, build_shorts_video


def _load_scenes(
    scenes_path: str,
    scene_dir: str,
    photo_count: int = 0,
    image_gen: str = "none",
    image_style: str = DEFAULT_STYLE,
    image_seed: int = 0,
) -> tuple[list[dict], dict, dict]:
    raw_scenes, characters, meta = load_scene_file(scenes_path)
    if image_style == DEFAULT_STYLE and meta.get("style"):
        image_style = meta["style"]
    sheet_dir = os.path.join(config.output_dir, "characters")
    if image_gen == "cloudflare" and characters:
        missing = [n for n in characters if not os.path.exists(os.path.join(sheet_dir, n, "gen_0.jpg"))]
        if missing:
            print(f"캐릭터 시트가 없어 참조 없이 그립니다: {' '.join(missing)}. --character-sheet 로 먼저 만들 수 있습니다.")

    scenes = []
    for i, raw in enumerate(raw_scenes):
        scene_media_dir = os.path.join(scene_dir, f"scene_{i}")
        scene = {"text": raw["text"], "path": None, "photo_paths": [], "speaker": raw.get("speaker")}

        if image_gen in ("pollinations", "cloudflare"):
            prompts = raw.get("prompts") or [raw.get("prompt") or raw.get("query", "")]
            per_prompt = photo_count if photo_count > 0 else (1 if len(prompts) > 1 else 2)
            images = []
            for j, prompt in enumerate(prompts):
                ref_names, ref_paths = [], []
                if image_gen == "cloudflare":
                    ref_names, ref_paths = character_reference_paths(prompt, characters, sheet_dir)
                full = expand_prompt(prompt, characters, ref_names)
                seed = character_seed(prompt, characters, image_seed + i * 100 + j * 10)
                shot_dir = os.path.join(scene_media_dir, f"shot_{j}") if len(prompts) > 1 else scene_media_dir
                ref_note = f" (참조 {' '.join(ref_names)})" if ref_names else ""
                print(f"장면 {i + 1} 컷 {j + 1} 그림 {per_prompt}장 생성 중{ref_note}...")
                images.extend(
                    generate_scene_images(full, per_prompt, shot_dir, image_style, seed, image_gen, ref_paths)
                )
            if not images:
                print(f"장면 {i + 1} 그림 생성 실패. 그라디언트로 대체합니다.")
            scene["photo_paths"] = images
            scene["generated"] = True
            scenes.append(scene)
            continue

        query = raw["query"]
        paths = fetch_topic_videos(query, 1, scene_media_dir)
        if not paths:
            print(f"장면 {i + 1} ('{query}') 영상 검색 실패. 그라디언트로 대체합니다.")
        if photo_count > 0:
            scene["photo_paths"] = fetch_topic_images(query, photo_count, scene_media_dir)
        scene["path"] = paths[0] if paths else None
        scenes.append(scene)
    return scenes, characters, meta


def run(
    script_path: str | None,
    background: str | None,
    out_name: str,
    auto_background: bool,
    voice_preset: str,
    background_type: str,
    music: str | None,
    auto_music: bool,
    topic: str | None,
    topic_count: int,
    topic_media: str,
    scenes_path: str | None,
    font_preset: str,
    scene_photos: int,
    tts_engine: str,
    renderer: str,
    image_gen: str,
    image_style: str,
    image_seed: int,
    character_sheet: bool = False,
) -> None:
    os.makedirs(config.output_dir, exist_ok=True)

    if character_sheet:
        _, characters, meta = load_scene_file(scenes_path)
        style = image_style if image_style != DEFAULT_STYLE else meta.get("style", DEFAULT_STYLE)
        backend = image_gen if image_gen in ("pollinations", "cloudflare") else "pollinations"
        sheet = build_character_sheet(characters, os.path.join(config.output_dir, "characters"), style, backend)
        if sheet:
            print(f"캐릭터 시트: {sheet}")
        return

    scenes = None
    characters: dict = {}
    meta: dict = {}
    if scenes_path:
        scene_dir = os.path.join(config.output_dir, "scene_media")
        scenes, characters, meta = _load_scenes(
            scenes_path, scene_dir, scene_photos, image_gen, image_style, image_seed
        )
        script_text = "".join(s["text"] for s in scenes)
    else:
        with open(script_path, "r", encoding="utf-8") as f:
            script_text = f.read().strip()

    narration_path = os.path.join(config.output_dir, "narration.mp3")
    if scenes and (characters or meta.get("narrator")):
        synthesize_scenes(
            scenes,
            characters,
            meta.get("narrator") or {},
            os.path.join(config.output_dir, "narration_parts"),
            narration_path,
            voice_preset,
            tts_engine,
        )
    else:
        synthesize_sync(script_text, narration_path, preset=voice_preset, engine=tts_engine)

    mixed_path = os.path.join(config.output_dir, "narration_mixed.mp3")
    audio_path = mix_narration_with_music(narration_path, mixed_path, music_path=music, auto_ambient=auto_music)

    topic_images = None
    topic_videos = None
    if topic and not scenes:
        topic_dir = os.path.join(config.output_dir, "topic_media")
        if topic_media in ("video", "auto"):
            topic_videos = fetch_topic_videos(topic, topic_count, topic_dir)
        if not topic_videos:
            if topic_media == "video":
                print("관련 영상 검색 실패. 이미지로 대체합니다.")
            topic_images = fetch_topic_images(topic, topic_count, topic_dir)
        if not topic_videos and not topic_images:
            print("관련 미디어 검색 실패. 기본 배경으로 대체합니다.")

    if (
        not scenes
        and not topic_images
        and not topic_videos
        and not background
        and auto_background
        and background_type == "image"
    ):
        background = fetch_random_background(os.path.join(config.output_dir, "background.jpg"))

    animated_fallback = auto_background and background_type == "animated"
    out_path = os.path.join(config.output_dir, out_name)
    build_shorts_video(
        script_text,
        audio_path,
        background,
        out_path,
        animated_fallback,
        topic_images,
        topic_videos,
        scenes,
        font_preset,
        renderer,
    )
    print(f"완성된 영상: {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="쇼츠 영상 생성기")
    parser.add_argument("script", help="나레이션 스크립트 텍스트 파일 경로", nargs="?", default=None)
    parser.add_argument("--background", help="배경 이미지 경로", default=None)
    parser.add_argument("--out", help="출력 파일명", default="shorts.mp4")
    parser.add_argument(
        "--no-auto-background",
        help="배경 미지정 시 자동 다운로드 비활성화",
        action="store_true",
    )
    parser.add_argument(
        "--voice-preset",
        help=f"목소리 톤 프리셋 {list(VOICE_PRESETS.keys())}",
        default="기본",
        choices=list(VOICE_PRESETS.keys()),
    )
    parser.add_argument(
        "--background-type",
        help="배경 미지정 시 처리 방식",
        default="animated",
        choices=["animated", "image", "solid"],
    )
    parser.add_argument("--music", help="배경음악 파일 경로", default=None)
    parser.add_argument(
        "--auto-music",
        help="음악 미지정 시 앰비언트 사운드 자동 추가",
        action="store_true",
    )
    parser.add_argument(
        "--topic",
        help="주제와 관련된 영상이나 이미지를 자동 검색해 배경으로 사용",
        default=None,
    )
    parser.add_argument(
        "--topic-count",
        help="주제 미디어 개수",
        type=int,
        default=6,
    )
    parser.add_argument(
        "--topic-media",
        help="주제 검색 시 우선 미디어 종류",
        default="video",
        choices=["video", "image"],
    )
    parser.add_argument(
        "--scenes",
        help="문장별 검색어를 담은 JSON 파일 경로. 지정 시 script 인자 대신 사용되고 --topic은 무시됩니다",
        default=None,
    )
    parser.add_argument(
        "--font-preset",
        help=f"자막 폰트 프리셋 {list(FONT_PRESETS.keys())}",
        default="라운드",
        choices=list(FONT_PRESETS.keys()),
    )
    parser.add_argument(
        "--scene-photos",
        help="--scenes 사용 시 각 장면 뒤에 붙일 사진 슬라이드 개수. 0이면 사진 없이 영상만 사용",
        type=int,
        default=0,
    )
    parser.add_argument(
        "--tts-engine",
        help="나레이션 음성 합성 엔진. google은 GOOGLE_TTS_API_KEY 필요",
        default="edge",
        choices=["edge", "google"],
    )
    parser.add_argument(
        "--renderer",
        help="fast는 ffmpeg 필터와 ASS 자막으로 빠르게 렌더링. classic은 기존 moviepy 방식",
        default="fast",
        choices=["fast", "classic"],
    )
    parser.add_argument(
        "--image-gen",
        help="--scenes 사용 시 스톡 대신 장면마다 AI 그림 생성. pollinations는 키 없이 무료. cloudflare는 Workers AI 키 필요",
        default="none",
        choices=["none", "pollinations", "cloudflare"],
    )
    parser.add_argument(
        "--image-style",
        help="AI 그림 생성 시 모든 장면 앞에 붙는 공통 화풍 프롬프트 (영어)",
        default=DEFAULT_STYLE,
    )
    parser.add_argument(
        "--image-seed",
        help="AI 그림 생성 seed 기준값. 같으면 같은 그림이 나옵니다",
        type=int,
        default=0,
    )
    parser.add_argument(
        "--character-sheet",
        help="--scenes 파일의 characters만 그려서 output/characters/character_sheet.jpg를 만들고 종료",
        action="store_true",
    )
    args = parser.parse_args()
    if not args.script and not args.scenes:
        parser.error("script 또는 --scenes 중 하나는 반드시 필요합니다")
    if args.character_sheet and not args.scenes:
        parser.error("--character-sheet 는 --scenes 와 함께 써야 합니다")
    run(
        args.script,
        args.background,
        args.out,
        not args.no_auto_background,
        args.voice_preset,
        args.background_type,
        args.music,
        args.auto_music,
        args.topic,
        args.topic_count,
        args.topic_media,
        args.scenes,
        args.font_preset,
        args.scene_photos,
        args.tts_engine,
        args.renderer,
        args.image_gen,
        args.image_style,
        args.image_seed,
        args.character_sheet,
    )


if __name__ == "__main__":
    main()
