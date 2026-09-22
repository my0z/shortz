import argparse
import os

from .background import fetch_random_background
from .config import config
from .tts import VOICE_PRESETS, synthesize_sync
from .video import build_shorts_video


def run(
    script_path: str,
    background: str | None,
    out_name: str,
    auto_background: bool,
    voice_preset: str,
    background_type: str,
) -> None:
    os.makedirs(config.output_dir, exist_ok=True)

    with open(script_path, "r", encoding="utf-8") as f:
        script_text = f.read().strip()

    narration_path = os.path.join(config.output_dir, "narration.mp3")
    synthesize_sync(script_text, narration_path, preset=voice_preset)

    if not background and auto_background and background_type == "image":
        background = fetch_random_background(os.path.join(config.output_dir, "background.jpg"))

    animated_fallback = auto_background and background_type == "animated"
    out_path = os.path.join(config.output_dir, out_name)
    build_shorts_video(script_text, narration_path, background, out_path, animated_fallback)
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
    args = parser.parse_args()
    run(
        args.script,
        args.background,
        args.out,
        not args.no_auto_background,
        args.voice_preset,
        args.background_type,
    )


if __name__ == "__main__":
    main()
