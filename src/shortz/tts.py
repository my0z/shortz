import asyncio

import edge_tts

from .config import config

VOICE_PRESETS = {
    "발랄": {"rate": "+15%", "pitch": "+25Hz"},
    "귀여운": {"rate": "+5%", "pitch": "+40Hz"},
    "차분": {"rate": "-5%", "pitch": "-10Hz"},
    "기본": {"rate": "+0%", "pitch": "+0Hz"},
}


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


def synthesize_sync(
    text: str,
    out_path: str,
    voice: str | None = None,
    preset: str = "기본",
) -> str:
    return asyncio.run(synthesize(text, out_path, voice, preset))
