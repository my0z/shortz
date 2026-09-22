"""aut.stock 에서 가져온 3년치 KRX 일봉+수급 패널 (open close inst foreign).

초기 3년치는 surge_data/history/krx_panel.parquet 로 복사해 두었다.
실행 때마다 aut.stock 최신 패널을 읽어 새 날짜만 krx_YYYYMMDD.parquet 로 따로 저장한다.
aut.stock 쪽에는 아무것도 쓰지 않는다.
"""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import requests

DIR = Path(__file__).resolve().parent.parent / "surge_data" / "history"
SEED = DIR / "krx_panel.parquet"
SOURCE_URL = ("https://raw.githubusercontent.com/my0z/aut.stock/"
              "claude/work-session-38u6d5/data/panel.parquet")


def load() -> pd.DataFrame:
    """seed + 증분을 합친 long 패널. index (date ticker)."""
    parts = [pd.read_parquet(p) for p in sorted(DIR.glob("krx_*.parquet"))]
    pn = pd.concat(parts)
    return pn[~pn.index.duplicated(keep="last")].sort_index()


def refresh() -> str:
    """aut.stock 최신 패널에서 새 날짜만 증분 파일로 저장한다."""
    have = load().index.get_level_values("date").max()
    resp = requests.get(SOURCE_URL, timeout=120)
    resp.raise_for_status()
    src = pd.read_parquet(io.BytesIO(resp.content))
    new = src[src.index.get_level_values("date") > have]
    if new.empty:
        return f"새 수급 데이터 없음 (보유 마지막 {have:%Y-%m-%d})"
    last = new.index.get_level_values("date").max()
    new.to_parquet(DIR / f"krx_{last:%Y%m%d}.parquet")
    return f"수급 {new.index.get_level_values('date').nunique()}일 추가 (~{last:%Y-%m-%d})"


def flows() -> dict[str, pd.DataFrame]:
    """date x ticker 기관/외국인 순매수 금액."""
    pn = load()
    return {"inst": pn["inst"].unstack("ticker"), "foreign": pn["foreign"].unstack("ticker")}
