import os

import ffmpeg

from .config import config
from .ffmpeg_utils import (
    cleanup_work_dir,
    concat_segments,
    final_render,
    make_work_dir,
    prepare_clip,
    prepare_gradient_clip,
    prepare_photo_clip,
    prepare_solid_clip,
    write_ass,
)
from .subtitles import Caption, split_into_captions

VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".ogv"}

FONT_PRESETS = {
    "라운드": "NanumSquareRound-Bold",
    "고딕": "NanumGothicBold",
    "바른고딕": "NanumBarunGothic-Bold",
    "명조": "NanumMyeongjoBold",
    "손글씨": "Nanum-Brush-Script",
}


def _fast_background_segments(
    background_path: str | None,
    duration: float,
    animated_fallback: bool,
    topic_images: list[str] | None,
    topic_videos: list[str] | None,
    scenes: list[dict] | None,
    work_dir: str,
) -> list[str]:
    w, h, fps = config.width, config.height, config.fps
    segments: list[str] = []

    if scenes:
        total_chars = sum(len(s["text"]) for s in scenes) or 1
        for scene in scenes:
            scene_duration = max(0.3, duration * (len(scene["text"]) / total_chars))
            video_path = scene.get("path")
            photo_paths = scene.get("photo_paths") or []
            if video_path and photo_paths:
                photo_duration = min(scene_duration * 0.5, max(scene_duration - 0.5, 0.0))
                video_duration = scene_duration - photo_duration
            elif video_path:
                video_duration, photo_duration = scene_duration, 0.0
            elif photo_paths:
                video_duration, photo_duration = 0.0, scene_duration
            else:
                video_duration, photo_duration = 0.0, 0.0

            if video_duration > 0:
                segments.append(prepare_clip(video_path, video_duration, w, h, fps, work_dir))
            if photo_duration > 0:
                per_photo = photo_duration / len(photo_paths)
                for photo_path in photo_paths:
                    segments.append(prepare_photo_clip(photo_path, per_photo, w, h, fps, work_dir))
            if video_duration <= 0 and photo_duration <= 0:
                segments.append(prepare_gradient_clip(scene_duration, w, h, fps, work_dir))
        return segments

    if topic_videos:
        per_clip = duration / len(topic_videos)
        return [prepare_clip(p, per_clip, w, h, fps, work_dir) for p in topic_videos]

    if topic_images:
        per_image = duration / len(topic_images)
        return [prepare_photo_clip(p, per_image, w, h, fps, work_dir) for p in topic_images]

    if background_path and os.path.exists(background_path):
        ext = os.path.splitext(background_path)[1].lower()
        if ext in VIDEO_EXTENSIONS:
            return [prepare_clip(background_path, duration, w, h, fps, work_dir)]
        return [prepare_photo_clip(background_path, duration, w, h, fps, work_dir)]

    if animated_fallback:
        return [prepare_gradient_clip(duration, w, h, fps, work_dir)]
    return [prepare_solid_clip(duration, w, h, fps, work_dir)]


def _build_shorts_video_fast(
    script_text: str,
    narration_path: str,
    background_path: str | None,
    out_path: str,
    animated_fallback: bool,
    topic_images: list[str] | None,
    topic_videos: list[str] | None,
    scenes: list[dict] | None,
    font_preset: str,
) -> str:
    duration = float(ffmpeg.probe(narration_path)["format"]["duration"])
    fade_len = min(0.6, duration / 4)
    work_dir = make_work_dir()

    print("배경 구간 준비 중 (ffmpeg)...")
    segments = _fast_background_segments(
        background_path, duration, animated_fallback, topic_images, topic_videos, scenes, work_dir
    )
    print(f"배경 구간 {len(segments)}개 이어붙이는 중...")
    background = concat_segments(segments, work_dir)

    captions: list[Caption] = split_into_captions(script_text, duration)
    ass_path = write_ass(captions, os.path.join(work_dir, "captions.ass"), config.width, config.height, font_preset)

    print("최종 렌더링 중 (색보정 + 자막 + 오디오)...")
    final_render(background, narration_path, ass_path, out_path, duration, config.fps, fade_len)
    cleanup_work_dir(work_dir)
    return out_path


def build_shorts_video(
    script_text: str,
    narration_path: str,
    background_path: str | None,
    out_path: str,
    animated_fallback: bool = True,
    topic_images: list[str] | None = None,
    topic_videos: list[str] | None = None,
    scenes: list[dict] | None = None,
    font_preset: str = "라운드",
    renderer: str = "fast",
) -> str:
    if renderer == "fast":
        try:
            return _build_shorts_video_fast(
                script_text,
                narration_path,
                background_path,
                out_path,
                animated_fallback,
                topic_images,
                topic_videos,
                scenes,
                font_preset,
            )
        except Exception as e:
            detail = getattr(e, "stderr", None)
            detail = detail.decode(errors="ignore")[-800:] if detail else str(e)
            print(f"빠른 렌더러 실패. 기존 moviepy 방식으로 다시 렌더링합니다.\n{detail}")

    from .video_classic import build_shorts_video_classic

    return build_shorts_video_classic(
        script_text,
        narration_path,
        background_path,
        out_path,
        animated_fallback,
        topic_images,
        topic_videos,
        scenes,
        font_preset,
    )
