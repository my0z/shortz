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
SOURCE_REPO = "my0z/aut.stock"
SOURCE_PATH = "data/panel.parquet"
API = "https://api.github.com"


FALLBACK_BRANCHES = ["claude/youthful-mayer-gw2qup", "claude/work-session-38u6d5"]


def source_branches() -> list[str]:
    """aut.stock 브랜치 목록. API 를 못 쓰면 알려진 브랜치로 대신한다."""
    try:
        js = requests.get(f"{API}/repos/{SOURCE_REPO}/branches?per_page=100", timeout=30).json()
        names = [b["name"] for b in js] if isinstance(js, list) else []
    except Exception:
        names = []
    return names or FALLBACK_BRANCHES


def fetch_source() -> tuple[pd.DataFrame, str]:
    """브랜치별 패널을 받아 날짜가 가장 최신인 것을 고른다."""
    best, best_branch = None, ""
    for branch in source_branches():
        resp = requests.get(source_url(branch), timeout=120)
        if resp.status_code != 200:
            continue
        pn = pd.read_parquet(io.BytesIO(resp.content))
        if best is None or pn.index.get_level_values("date").max() > best.index.get_level_values("date").max():
            best, best_branch = pn, branch
    if best is None:
        raise RuntimeError("aut.stock 에서 panel.parquet 를 못 받았다")
    return best, best_branch


def source_url(branch: str) -> str:
    return f"https://raw.githubusercontent.com/{SOURCE_REPO}/{branch}/{SOURCE_PATH}"


def load() -> pd.DataFrame:
    """seed + 증분을 합친 long 패널. index (date ticker)."""
    parts = [pd.read_parquet(p) for p in sorted(DIR.glob("krx_*.parquet"))]
    pn = pd.concat(parts)
    return pn[~pn.index.duplicated(keep="last")].sort_index()


def refresh() -> str:
    """aut.stock 최신 패널에서 새 날짜만 증분 파일로 저장한다."""
    have = load().index.get_level_values("date").max()
    src, branch = fetch_source()
    new = src[src.index.get_level_values("date") > have]
    if new.empty:
        return f"새 수급 데이터 없음 (보유 마지막 {have:%Y-%m-%d} / 원본 {branch})"
    last = new.index.get_level_values("date").max()
    new.to_parquet(DIR / f"krx_{last:%Y%m%d}.parquet")
    return f"수급 {new.index.get_level_values('date').nunique()}일 추가 (~{last:%Y-%m-%d} / 원본 {branch})"


def flows() -> dict[str, pd.DataFrame]:
    """date x ticker 기관/외국인 순매수 금액."""
    pn = load()
    return {"inst": pn["inst"].unstack("ticker"), "foreign": pn["foreign"].unstack("ticker")}
