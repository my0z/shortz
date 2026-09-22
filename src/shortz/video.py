import os

from PIL import Image

if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.LANCZOS

from moviepy.editor import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    VideoFileClip,
    concatenate_videoclips,
)
from moviepy.video.fx.all import crop, loop

from .config import config
from .subtitles import Caption, split_into_captions

VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv", ".avi"}


def _load_background_clip(path: str):
    ext = os.path.splitext(path)[1].lower()
    if ext in VIDEO_EXTENSIONS:
        return VideoFileClip(path, audio=False)
    return ImageClip(path)


def _fit_cover(clip, width: int, height: int):
    if clip.w / clip.h > width / height:
        clip = clip.resize(height=height)
    else:
        clip = clip.resize(width=width)
    return crop(clip, width=width, height=height, x_center=clip.w / 2, y_center=clip.h / 2)


def _build_background(background_path: str | None, duration: float):
    if background_path and os.path.exists(background_path):
        clip = _load_background_clip(background_path)
        clip = _fit_cover(clip, config.width, config.height)
        if clip.duration and clip.duration < duration:
            clip = loop(clip, duration=duration)
        elif clip.duration and clip.duration > duration:
            clip = clip.subclip(0, duration)
        return clip.set_duration(duration)
    return ColorClip(size=(config.width, config.height), color=(15, 15, 20)).set_duration(duration)


def build_shorts_video(
    script_text: str,
    narration_path: str,
    background_path: str | None,
    out_path: str,
) -> str:
    audio = AudioFileClip(narration_path)
    duration = audio.duration

    background = _build_background(background_path, duration)

    captions: list[Caption] = split_into_captions(script_text, duration)
    caption_clips = []
    for caption in captions:
        clip = (
            TextClip(
                caption.text,
                fontsize=64,
                color="white",
                font="NanumGothicBold",
                stroke_color="black",
                stroke_width=2,
                size=(int(config.width * 0.9), None),
                method="caption",
            )
            .set_start(caption.start)
            .set_end(caption.end)
            .set_position(("center", "center"))
        )
        caption_clips.append(clip)

    final = CompositeVideoClip([background, *caption_clips], size=(config.width, config.height))
    final = final.set_audio(audio)
    final.write_videofile(out_path, fps=config.fps, codec="libx264", audio_codec="aac")
    return out_path
