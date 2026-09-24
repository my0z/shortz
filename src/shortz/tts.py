import asyncio
import base64
import os

import ffmpeg

import edge_tts
import requests

from .config import config

VOICE_PRESETS = {
    "발랄": {"rate": "+15%", "pitch": "+25Hz"},
    "귀여운": {"rate": "+5%", "pitch": "+40Hz"},
    "차분": {"rate": "-5%", "pitch": "-10Hz"},
    "기본": {"rate": "+0%", "pitch": "+0Hz"},
}

GOOGLE_VOICE = "ko-KR-Neural2-A"
GOOGLE_VOICE_PRESETS = {
    "발랄": {"rate": 1.15, "pitch": 4.0},
    "귀여운": {"rate": 1.05, "pitch": 6.0},
    "차분": {"rate": 0.95, "pitch": -2.0},
    "기본": {"rate": 1.0, "pitch": 0.0},
}

GOOGLE_TTS_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"


async def synthesize(
    text: str,
    out_path: str,
    voice: str | None = None,
    preset: str = "기본",
) -> str:
    settings = VOICE_PRESETS.get(preset, VOICE_PRESETS["기본"])
    communicate = edge_tts.Communicate(
        text,
        voice or config.tts_voice,
        rate=settings["rate"],
        pitch=settings["pitch"],
    )
    await communicate.save(out_path)
    return out_path


def synthesize_google(
    text: str,
    out_path: str,
    voice: str | None = None,
    preset: str = "기본",
) -> str:
    settings = GOOGLE_VOICE_PRESETS.get(preset, GOOGLE_VOICE_PRESETS["기본"])
    payload = {
        "input": {"text": text},
        "voice": {"languageCode": "ko-KR", "name": voice or GOOGLE_VOICE},
        "audioConfig": {
            "audioEncoding": "MP3",
            "speakingRate": settings["rate"],
            "pitch": settings["pitch"],
        },
    }
    resp = requests.post(GOOGLE_TTS_URL, params={"key": config.google_tts_api_key}, json=payload, timeout=60)
    resp.raise_for_status()
    audio_content = resp.json()["audioContent"]
    with open(out_path, "wb") as f:
        f.write(base64.b64decode(audio_content))
    return out_path


def synthesize_sync(
    text: str,
    out_path: str,
    voice: str | None = None,
    preset: str = "기본",
    engine: str = "edge",
) -> str:
    if engine == "google":
        return synthesize_google(text, out_path, voice, preset)
    return asyncio.run(synthesize(text, out_path, voice, preset))


def synthesize_scenes(
    scenes: list[dict],
    characters: dict,
    narrator: dict,
    out_dir: str,
    out_path: str,
    preset: str = "기본",
    engine: str = "edge",
) -> str:
    """Synthesize each scene with its speaker's voice and join the pieces.

    Every scene gets a "duration" key with the exact audio length in seconds.
    """
    from .ffmpeg_utils import concat_audio

    os.makedirs(out_dir, exist_ok=True)
    voice_key = "google_voice" if engine == "google" else "voice"
    pieces = []
    for i, scene in enumerate(scenes):
        speaker = scene.get("speaker")
        info = characters.get(speaker) if speaker else narrator
        info = info or {}
        voice = info.get(voice_key) or None
        scene_preset = info.get("voice_preset") or preset
        piece = os.path.join(out_dir, f"scene_{i}.mp3")
        who = speaker or "나레이션"
        print(f"장면 {i + 1} 음성 합성 ({who})...")
        synthesize_sync(scene["text"], piece, voice, scene_preset, engine)
        scene["duration"] = float(ffmpeg.probe(piece)["format"]["duration"])
        pieces.append(piece)
    return concat_audio(pieces, out_path)
