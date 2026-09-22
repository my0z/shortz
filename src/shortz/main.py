import argparse
import os

from .audio import mix_narration_with_music
from .background import fetch_random_background
from .config import config
from .topic_images import fetch_topic_images
from .tts import VOICE_PRESETS, synthesize_sync
from .video import build_shorts_video


def run(
    script_path: str,
    background: str | None,
    out_name: str,
    auto_background: bool,
    voice_preset: str,
    background_type: str,
    music: str | None,
    auto_music: bool,
    topic: str | None,
    topic_count: int,
) -> None:
    os.makedirs(config.output_dir, exist_ok=True)

    with open(script_path, "r", encoding="utf-8") as f:
        script_text = f.read().strip()

    narration_path = os.path.join(config.output_dir, "narration.mp3")
    synthesize_sync(script_text, narration_path, preset=voice_preset)

    mixed_path = os.path.join(config.output_dir, "narration_mixed.mp3")
    audio_path = mix_narration_with_music(narration_path, mixed_path, music_path=music, auto_ambient=auto_music)

    topic_images = None
    if topic:
        topic_dir = os.path.join(config.output_dir, "topic_images")
        topic_images = fetch_topic_images(topic, topic_count, topic_dir)
        if not topic_images:
            print("관련 이미지 검색 실패. 기본 배경으로 대체합니다.")

    if not topic_images and not background and auto_background and background_type == "image":
        background = fetch_random_background(os.path.join(config.output_dir, "background.jpg"))

    animated_fallback = auto_background and background_type == "animated"
    out_path = os.path.join(config.output_dir, out_name)
    build_shorts_video(script_text, audio_path, background, out_path, animated_fallback, topic_images)
    print(f"완성된 영상: {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="쇼츠 영상 생성기")
    parser.add_argument("script", help="나레이션 스크립트 텍스트 파일 경로")
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
        help="주제와 관련된 이미지를 자동 검색해 배경 슬라이드쇼로 사용",
        default=None,
    )
    parser.add_argument(
        "--topic-count",
        help="주제 이미지 개수",
        type=int,
        default=6,
    )
    args = parser.parse_args()
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
    )


if __name__ == "__main__":
    main()
