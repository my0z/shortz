"""네이버 증권에서 종목 목록과 일봉을 받는다. 장중에 받으면 오늘 봉은 현재가 기준 미완성 봉이다."""

from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
LIST_URL = "https://m.stock.naver.com/api/stocks/marketValue/{market}?page={page}&pageSize=100"
CHART_URL = "https://fchart.stock.naver.com/sise.nhn?symbol={code}&timeframe=day&count={count}&requestType=0"


def _get(url: str, tries: int = 3) -> requests.Response:
    for i in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=15)
            r.raise_for_status()
            return r
        except requests.RequestException:
            if i == tries - 1:
                raise
            time.sleep(1 + i)
    raise RuntimeError("unreachable")


def universe() -> pd.DataFrame:
    """코스피+코스닥 보통주 목록. columns code name market."""
    rows = []
    for market in ("KOSPI", "KOSDAQ"):
        page = 1
        while True:
            js = _get(LIST_URL.format(market=market, page=page)).json()
            stocks = js.get("stocks", [])
            for s in stocks:
                if s.get("stockEndType", "stock") != "stock":
                    continue
                rows.append({"code": s["itemCode"], "name": s["stockName"], "market": market})
            if not stocks or page * 100 >= js.get("totalCount", 0):
                break
            page += 1
    return pd.DataFrame(rows).drop_duplicates("code").reset_index(drop=True)


def daily(code: str, count: int = 520) -> pd.DataFrame:
    """일봉. columns date open high low close volume."""
    # 응답이 EUC-KR 선언 XML 이라 파서 대신 정규식으로 item 만 읽는다
    text = _get(CHART_URL.format(code=code, count=count)).content.decode("euc-kr", "replace")
    rows = []
    for data in re.findall(r'<item data="([^"]+)"', text):
        d, o, h, lo, c, v = data.split("|")
        rows.append((d, float(o), float(h), float(lo), float(c), float(v)))
    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    df["code"] = code
    return df


def all_daily(codes: list[str], count: int = 520, workers: int = 16) -> pd.DataFrame:
    def one(c: str) -> pd.DataFrame | None:
        try:
            return daily(c, count)
        except Exception as e:  # 한 종목 실패로 전체를 멈추지 않는다
            print(f"  {c} 실패: {e}")
            return None

    with ThreadPoolExecutor(workers) as ex:
        parts = [p for p in ex.map(one, codes) if p is not None and len(p)]
    return pd.concat(parts, ignore_index=True)


def wide(long: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """date x code 와이드 패널."""
    out = {}
    for col in ("open", "high", "low", "close", "volume"):
        out[col] = long.pivot(index="date", columns="code", values=col).sort_index()
    # 거래정지일 (시가 0) 은 결측
    for col in ("open", "high", "low"):
        out[col] = out[col].where(out[col] > 0)
    return out
