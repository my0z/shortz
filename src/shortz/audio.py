import numpy as np
from moviepy.audio.AudioClip import AudioArrayClip
from moviepy.audio.fx.all import audio_fadein, audio_fadeout, audio_loop, volumex
from moviepy.editor import AudioFileClip, CompositeAudioClip


def _generate_ambient_pad(duration: float, fps: int = 44100):
    t = np.linspace(0, duration, int(duration * fps), endpoint=False)
    freqs = [110.0, 165.0, 220.0]
    wave = np.zeros_like(t)
    for freq in freqs:
        wave += np.sin(2 * np.pi * freq * t)
    wave /= len(freqs)
    lfo = 0.6 + 0.4 * np.sin(2 * np.pi * 0.08 * t)
    wave *= lfo * 0.08
    stereo = np.column_stack([wave, wave])
    return AudioArrayClip(stereo, fps=fps)


def mix_narration_with_music(
    narration_path: str,
    out_path: str,
    music_path: str | None = None,
    auto_ambient: bool = False,
    music_volume: float = 0.18,
) -> str:
    narration = AudioFileClip(narration_path)
    duration = narration.duration

    if music_path:
        music = AudioFileClip(music_path)
    elif auto_ambient:
        music = _generate_ambient_pad(duration)
    else:
        narration.write_audiofile(out_path)
        return out_path

    if music.duration < duration:
        music = audio_loop(music, duration=duration)
    else:
        music = music.subclip(0, duration)

    music = volumex(music, music_volume)
    fade = min(1.5, duration / 4)
    music = audio_fadein(music, fade)
    music = audio_fadeout(music, fade)

    mixed = CompositeAudioClip([music, narration]).set_duration(duration)
    mixed.fps = narration.fps or 44100
    mixed.write_audiofile(out_path, fps=mixed.fps)
    return out_path
