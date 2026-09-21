import os

from moviepy.editor import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    concatenate_videoclips,
)

from .config import config
from .subtitles import Caption, split_into_captions


def build_shorts_video(
    script_text: str,
    narration_path: str,
    background_path: str | None,
    out_path: str,
) -> str:
    audio = AudioFileClip(narration_path)
    duration = audio.duration

    if background_path and os.path.exists(background_path):
        background = ImageClip(background_path).set_duration(duration)
        background = background.resize(height=config.height)
    else:
        background = ColorClip(size=(config.width, config.height), color=(15, 15, 20)).set_duration(duration)

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
