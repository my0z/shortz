import os
import uuid

import ffmpeg

from .config import config


def prepare_clip(input_path: str, duration: float, width: int, height: int, fps: int) -> str:
    """Scale+crop a video to the target size and trim/loop it to duration using ffmpeg directly.

    This offloads per-frame resize/crop work from moviepy's Python loop to ffmpeg's C
    implementation, which is much faster for straight video-in video-out processing.
    """
    out_path = os.path.join(config.output_dir, f"_prepared_{uuid.uuid4().hex}.mp4")
    stream = ffmpeg.input(input_path, stream_loop=-1)
    video = (
        stream.video.filter("scale", width, height, force_original_aspect_ratio="increase")
        .filter("crop", width, height)
        .filter("setsar", 1)
    )
    (
        ffmpeg.output(video, out_path, t=duration, an=None, r=fps, pix_fmt="yuv420p")
        .overwrite_output()
        .run(quiet=True)
    )
    return out_path
