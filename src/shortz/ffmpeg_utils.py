import os
import random
import shutil
import uuid

import ffmpeg

from .config import config

GRADIENT_PALETTES = [
    ("0x140a28", "0x5a1e6e"),
    ("0x0a142d", "0x145a78"),
    ("0x230a19", "0x78283c"),
    ("0x0a1e19", "0x146e5a"),
    ("0x1e0f0a", "0x824614"),
]

ASS_FONTS = {
    "라운드": "NanumSquareRound",
    "고딕": "NanumGothic",
    "바른고딕": "NanumBarunGothic",
    "명조": "NanumMyeongjo",
    "손글씨": "Nanum Brush Script",
}


def _encode_kwargs(fps: int) -> dict:
    return {
        "vcodec": "libx264",
        "preset": "veryfast",
        "crf": 20,
        "pix_fmt": "yuv420p",
        "r": fps,
        "an": None,
    }


def _segment_path(work_dir: str, ext: str = ".mp4") -> str:
    return os.path.join(work_dir, f"seg_{uuid.uuid4().hex}{ext}")


def prepare_clip(input_path: str, duration: float, width: int, height: int, fps: int, work_dir: str | None = None) -> str:
    """Scale+crop a video to the target size and trim/loop it to duration with ffmpeg."""
    work_dir = work_dir or config.output_dir
    out_path = _segment_path(work_dir)
    video = (
        ffmpeg.input(input_path, stream_loop=-1)
        .video.filter("scale", width, height, force_original_aspect_ratio="increase")
        .filter("crop", width, height)
        .filter("setsar", 1)
        .filter("fps", fps)
    )
    ffmpeg.output(video, out_path, t=duration, **_encode_kwargs(fps)).overwrite_output().run(quiet=True)
    return out_path


def prepare_photo_clip(
    image_path: str, duration: float, width: int, height: int, fps: int, work_dir: str, zoom_end: float = 1.15
) -> str:
    """Ken Burns slow zoom on a still image using ffmpeg zoompan."""
    out_path = _segment_path(work_dir)
    frames = max(1, int(round(duration * fps)))
    zoom_expr = f"min({zoom_end},1+{zoom_end - 1}*on/{frames})"
    video = (
        ffmpeg.input(image_path)
        .video.filter("scale", width * 2, height * 2, force_original_aspect_ratio="increase")
        .filter("crop", width * 2, height * 2)
        .filter(
            "zoompan",
            z=zoom_expr,
            x="iw/2-(iw/zoom/2)",
            y="ih/2-(ih/zoom/2)",
            d=frames,
            s=f"{width}x{height}",
            fps=fps,
        )
        .filter("setsar", 1)
    )
    ffmpeg.output(video, out_path, t=duration, **_encode_kwargs(fps)).overwrite_output().run(quiet=True)
    return out_path


def prepare_gradient_clip(duration: float, width: int, height: int, fps: int, work_dir: str) -> str:
    out_path = _segment_path(work_dir)
    c0, c1 = random.choice(GRADIENT_PALETTES)
    src = (
        f"gradients=size={width}x{height}:rate={fps}:duration={duration:.3f}"
        f":c0={c0}:c1={c1}:nb_colors=2:speed=0.02"
    )
    video = ffmpeg.input(src, f="lavfi").video.filter("setsar", 1)
    ffmpeg.output(video, out_path, t=duration, **_encode_kwargs(fps)).overwrite_output().run(quiet=True)
    return out_path


def prepare_solid_clip(duration: float, width: int, height: int, fps: int, work_dir: str) -> str:
    out_path = _segment_path(work_dir)
    src = f"color=c=0x0f0f14:size={width}x{height}:rate={fps}:duration={duration:.3f}"
    video = ffmpeg.input(src, f="lavfi").video.filter("setsar", 1)
    ffmpeg.output(video, out_path, t=duration, **_encode_kwargs(fps)).overwrite_output().run(quiet=True)
    return out_path


def concat_segments(segment_paths: list[str], work_dir: str) -> str:
    """Join identically encoded segments without re-encoding using the concat demuxer."""
    list_path = os.path.join(work_dir, "concat.txt")
    with open(list_path, "w", encoding="utf-8") as f:
        for p in segment_paths:
            escaped = os.path.abspath(p).replace("'", "'\\''")
            f.write(f"file '{escaped}'\n")
    out_path = os.path.join(work_dir, "background.mp4")
    (
        ffmpeg.input(list_path, f="concat", safe=0)
        .output(out_path, c="copy")
        .overwrite_output()
        .run(quiet=True)
    )
    return out_path


def _ass_time(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _ass_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "(").replace("}", ")")


def write_ass(
    captions,
    ass_path: str,
    width: int,
    height: int,
    font_preset: str,
    fontsize: int = 72,
    box_opacity: float = 0.65,
    fade_ms: int = 150,
) -> str:
    """Write captions as an ASS file: a translucent box layer under a white text layer with black outline."""
    font = ASS_FONTS.get(font_preset, ASS_FONTS["라운드"])
    box_alpha = int(round(255 * (1 - box_opacity)))
    box_colour = f"&H{box_alpha:02X}000000"
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Box,{font},{fontsize},&HFFFFFFFF,&HFFFFFFFF,{box_colour},{box_colour},"
        "-1,0,0,0,100,100,0,0,3,20,0,5,54,54,0,1",
        f"Style: Text,{font},{fontsize},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,"
        "-1,0,0,0,100,100,0,0,1,2,0,5,54,54,0,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for cap in captions:
        start, end = _ass_time(cap.start), _ass_time(cap.end)
        text = _ass_escape(cap.text)
        fade = f"{{\\fad({fade_ms},{fade_ms})}}"
        lines.append(f"Dialogue: 0,{start},{end},Box,,0,0,0,,{fade}{text}")
        lines.append(f"Dialogue: 1,{start},{end},Text,,0,0,0,,{fade}{text}")
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return ass_path


def final_render(
    background_path: str,
    audio_path: str,
    ass_path: str,
    out_path: str,
    duration: float,
    fps: int,
    fade: float,
) -> str:
    """Color grade + vignette + burned-in ASS captions + fades + audio in one ffmpeg pass."""
    video = (
        ffmpeg.input(background_path)
        .video.filter("tpad", stop_mode="clone", stop_duration=3)
        .filter("eq", contrast=1.08, saturation=0.85)
        .filter("colorchannelmixer", rr=1.05, bb=0.95)
        .filter("vignette")
        .filter("ass", ass_path)
        .filter("fade", type="in", start_time=0, duration=fade)
        .filter("fade", type="out", start_time=max(0.0, duration - fade), duration=fade)
    )
    audio = (
        ffmpeg.input(audio_path)
        .audio.filter("loudnorm", I=-16, TP=-1.5, LRA=11)
        .filter("afade", type="in", start_time=0, duration=fade)
        .filter("afade", type="out", start_time=max(0.0, duration - fade), duration=fade)
    )
    (
        ffmpeg.output(
            video,
            audio,
            out_path,
            t=duration,
            vcodec="libx264",
            preset="veryfast",
            crf=21,
            pix_fmt="yuv420p",
            r=fps,
            acodec="aac",
            audio_bitrate="192k",
            movflags="+faststart",
        )
        .overwrite_output()
        .run(quiet=True)
    )
    return out_path


def make_work_dir() -> str:
    path = os.path.join(config.output_dir, f"_work_{uuid.uuid4().hex}")
    os.makedirs(path, exist_ok=True)
    return path


def cleanup_work_dir(path: str) -> None:
    shutil.rmtree(path, ignore_errors=True)
