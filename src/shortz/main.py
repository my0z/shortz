import argparse
import json
import os

from .audio import mix_narration_with_music
from .background import fetch_random_background
from .config import config
from .topic_images import fetch_topic_images
from .topic_videos import fetch_topic_videos
from .tts import VOICE_PRESETS, synthesize_sync
from .video import FONT_PRESETS, build_shorts_video


def _load_scenes(scenes_path: str, scene_dir: str) -> list[dict]:
    with open(scenes_path, "r", encoding="utf-8") as f:
        raw_scenes = json.load(f)

    scenes = []
    for i, raw in enumerate(raw_scenes):
        query = raw["query"]
        paths = fetch_topic_videos(query, 1, os.path.join(scene_dir, f"scene_{i}"))
        if not paths:
            print(f"장면 {i + 1} ('{query}') 영상 검색 실패. 그라디언트로 대체합니다.")
        scenes.append({"text": raw["text"], "path": paths[0] if paths else None})
    return scenes


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
) -> None:
    os.makedirs(config.output_dir, exist_ok=True)

    scenes = None
    if scenes_path:
        scene_dir = os.path.join(config.output_dir, "scene_media")
        scenes = _load_scenes(scenes_path, scene_dir)
        script_text = "".join(s["text"] for s in scenes)
    else:
        with open(script_path, "r", encoding="utf-8") as f:
            script_text = f.read().strip()

    narration_path = os.path.join(config.output_dir, "narration.mp3")
    synthesize_sync(script_text, narration_path, preset=voice_preset)

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
    args = parser.parse_args()
    if not args.script and not args.scenes:
        parser.error("script 또는 --scenes 중 하나는 반드시 필요합니다")
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
    )


if __name__ == "__main__":
    main()
