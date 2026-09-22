import os
import random

import numpy as np
from PIL import Image, ImageDraw

if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.LANCZOS

from moviepy.audio.fx.all import audio_fadein, audio_fadeout, audio_normalize
from moviepy.editor import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    VideoClip,
    VideoFileClip,
    concatenate_videoclips,
)
from moviepy.video.compositing.transitions import crossfadein, crossfadeout
from moviepy.video.fx.all import crop, fadein, fadeout, loop

from .config import config
from .subtitles import Caption, split_into_captions

VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".ogv"}

GRADIENT_PALETTES = [
    ((20, 10, 40), (90, 30, 110)),
    ((10, 20, 45), (20, 90, 120)),
    ((35, 10, 25), (120, 40, 60)),
    ((10, 30, 25), (20, 110, 90)),
    ((30, 15, 10), (130, 70, 20)),
]


def _generate_animated_background(duration: float, width: int, height: int):
    color1, color2 = random.choice(GRADIENT_PALETTES)
    color1 = np.array(color1, dtype=np.float64)
    color2 = np.array(color2, dtype=np.float64)
    y, x = np.mgrid[0:height, 0:width]
    xn = x / width
    yn = y / height

    def make_frame(t):
        phase = t * 0.25
        mask = 0.5 + 0.5 * np.sin(2 * np.pi * (xn * 1.2 + yn * 0.8 + phase))
        frame = color1[None, None, :] * (1 - mask[..., None]) + color2[None, None, :] * mask[..., None]
        return frame.astype("uint8")

    return VideoClip(make_frame, duration=duration)


def _ken_burns_clip(image_path: str, duration: float, width: int, height: int, zoom_end: float = 1.15):
    img = Image.open(image_path).convert("RGB")
    img_ratio = img.width / img.height
    target_ratio = width / height
    if img_ratio > target_ratio:
        base_h, base_w = height, int(height * img_ratio)
    else:
        base_w, base_h = width, int(width / img_ratio)
    base_img = img.resize((base_w, base_h), Image.LANCZOS)

    def make_frame(t):
        scale = 1 + (zoom_end - 1) * (t / duration)
        fw, fh = int(base_w * scale), int(base_h * scale)
        frame_img = base_img.resize((fw, fh), Image.LANCZOS)
        x1 = (fw - width) // 2
        y1 = (fh - height) // 2
        return np.array(frame_img.crop((x1, y1, x1 + width, y1 + height)))

    return VideoClip(make_frame, duration=duration)


def _caption_box_clip(width: int, height: int, radius: int = 24, opacity: float = 0.45):
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, width - 1, height - 1], radius=radius, fill=(0, 0, 0, int(255 * opacity)))
    return ImageClip(np.array(img))


def _vignette_clip(width: int, height: int, duration: float, strength: float = 0.55):
    y, x = np.mgrid[0:height, 0:width]
    cx, cy = width / 2, height / 2
    max_dist = np.sqrt(cx**2 + cy**2)
    dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / max_dist
    alpha = np.clip((dist - 0.4) / 0.6, 0, 1) * strength
    rgba = np.zeros((height, width, 4), dtype="uint8")
    rgba[..., 3] = (alpha * 255).astype("uint8")
    return ImageClip(rgba).set_duration(duration)


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


def _build_slideshow_background(image_paths: list[str], duration: float, width: int, height: int):
    per_image = duration / len(image_paths)
    clips = [_ken_burns_clip(p, per_image, width, height) for p in image_paths]
    return concatenate_videoclips(clips, method="compose")


def _build_topic_video_background(video_paths: list[str], duration: float, width: int, height: int):
    per_clip = duration / len(video_paths)
    clips = []
    for path in video_paths:
        clip = _load_background_clip(path)
        clip = _fit_cover(clip, width, height)
        src_duration = clip.duration or per_clip
        if src_duration < per_clip:
            clip = loop(clip, duration=per_clip)
        else:
            clip = clip.subclip(0, min(per_clip, src_duration))
        clips.append(clip.set_duration(per_clip).without_audio())
    return concatenate_videoclips(clips, method="compose")


def _build_background(
    background_path: str | None,
    duration: float,
    animated_fallback: bool = True,
    topic_images: list[str] | None = None,
    topic_videos: list[str] | None = None,
):
    if topic_videos:
        return _build_topic_video_background(topic_videos, duration, config.width, config.height)
    if topic_images:
        return _build_slideshow_background(topic_images, duration, config.width, config.height)
    if background_path and os.path.exists(background_path):
        ext = os.path.splitext(background_path)[1].lower()
        if ext not in VIDEO_EXTENSIONS:
            return _ken_burns_clip(background_path, duration, config.width, config.height)
        clip = _load_background_clip(background_path)
        clip = _fit_cover(clip, config.width, config.height)
        if clip.duration and clip.duration < duration:
            clip = loop(clip, duration=duration)
        elif clip.duration and clip.duration > duration:
            clip = clip.subclip(0, duration)
        return clip.set_duration(duration)
    if animated_fallback:
        return _generate_animated_background(duration, config.width, config.height)
    return ColorClip(size=(config.width, config.height), color=(15, 15, 20)).set_duration(duration)


def build_shorts_video(
    script_text: str,
    narration_path: str,
    background_path: str | None,
    out_path: str,
    animated_fallback: bool = True,
    topic_images: list[str] | None = None,
    topic_videos: list[str] | None = None,
) -> str:
    audio = AudioFileClip(narration_path)
    try:
        audio = audio_normalize(audio)
    except Exception:
        pass
    duration = audio.duration
    fade_len = min(0.6, duration / 4)
    audio = audio_fadein(audio, fade_len)
    audio = audio_fadeout(audio, fade_len)

    background = _build_background(background_path, duration, animated_fallback, topic_images, topic_videos)

    captions: list[Caption] = split_into_captions(script_text, duration)
    caption_clips = []
    for caption in captions:
        text_clip = TextClip(
            caption.text,
            fontsize=64,
            color="white",
            font="NanumGothicBold",
            stroke_color="black",
            stroke_width=2,
            size=(int(config.width * 0.9), None),
            method="caption",
        )
        box_clip = _caption_box_clip(text_clip.w + 48, text_clip.h + 32)

        box_clip = box_clip.set_start(caption.start).set_end(caption.end).set_position(("center", "center"))
        text_clip = text_clip.set_start(caption.start).set_end(caption.end).set_position(("center", "center"))

        cap_fade = min(0.15, (caption.end - caption.start) / 3)
        box_clip = crossfadein(box_clip, cap_fade)
        box_clip = crossfadeout(box_clip, cap_fade)
        text_clip = crossfadein(text_clip, cap_fade)
        text_clip = crossfadeout(text_clip, cap_fade)

        caption_clips.append(box_clip)
        caption_clips.append(text_clip)

    vignette = _vignette_clip(config.width, config.height, duration)
    final = CompositeVideoClip([background, vignette, *caption_clips], size=(config.width, config.height))
    final = fadein(final, fade_len)
    final = fadeout(final, fade_len)
    final = final.set_audio(audio)
    final.write_videofile(out_path, fps=config.fps, codec="libx264", audio_codec="aac")
    return out_path
