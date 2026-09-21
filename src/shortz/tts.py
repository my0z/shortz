import asyncio

import edge_tts

from .config import config


async def synthesize(text: str, out_path: str, voice: str | None = None) -> str:
    communicate = edge_tts.Communicate(text, voice or config.tts_voice)
    await communicate.save(out_path)
    return out_path


def synthesize_sync(text: str, out_path: str, voice: str | None = None) -> str:
    return asyncio.run(synthesize(text, out_path, voice))
