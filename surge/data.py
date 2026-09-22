"""aut.stock 의 KRX 일봉+수급 패널 로드."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import requests

PANEL_URL = (
    "https://raw.githubusercontent.com/my0z/aut.stock/"
    "claude/work-session-38u6d5/data/panel.parquet"
)
CACHE = Path(__file__).resolve().parent.parent / "data" / "panel.parquet"


def resolve_panel(path: str | None = None, refresh: bool = False) -> Path:
    """패널 파일 경로를 정한다. 없으면 aut.stock 저장소에서 내려받는다."""
    if path:
        return Path(path)
    env = os.getenv("SURGE_PANEL")
    if env:
        return Path(env)
    if refresh or not CACHE.exists():
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        print(f"패널 다운로드: {PANEL_URL}")
        resp = requests.get(PANEL_URL, timeout=120)
        resp.raise_for_status()
        CACHE.write_bytes(resp.content)
    return CACHE


def load_panel(path: str | None = None, refresh: bool = False) -> dict[str, pd.DataFrame]:
    """date x ticker 와이드 패널 (open close inst foreign) 을 돌려준다."""
    pn = pd.read_parquet(resolve_panel(path, refresh))
    wide = {c: pn[c].unstack("ticker").sort_index() for c in ["open", "close", "inst", "foreign"]}
    # 거래정지일 시가 0 은 결측으로 본다
    wide["open"] = wide["open"].where(wide["open"] > 0)
    return wide
