"""일봉 OHLCV 로 종목별 차트 피처를 만든다. 모든 값은 당일 봉까지의 정보만 쓴다."""

from __future__ import annotations

import numpy as np
import pandas as pd

SURGE = 0.05  # 익일 종가 기준 +5% 이상을 급등으로 본다
MIN_PRICE = 1000


def _streak(pos: pd.DataFrame) -> pd.DataFrame:
    """연속 True 일수."""
    arr = pos.to_numpy()
    out = np.zeros(arr.shape)
    run = np.zeros(arr.shape[1])
    for i in range(len(arr)):
        run = np.where(arr[i], run + 1, 0)
        out[i] = run
    return pd.DataFrame(out, index=pos.index, columns=pos.columns)


def flow_features(flows: dict[str, pd.DataFrame], C: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """기관/외국인 수급 피처. 15시에는 오늘 수급을 모르므로 전일까지 값만 쓴다.

    데이터가 며칠 늦게 들어와도 쓰도록 최근 값을 5일까지 이어 쓴다.
    """
    f = {}
    both = None
    for name, key in (("inst", "inst"), ("frgn", "foreign")):
        fl = flows[key].reindex(columns=C.columns)
        fl = fl.reindex(fl.index.union(C.index)).sort_index()
        scale = fl.abs().rolling(20, min_periods=5).mean().replace(0, np.nan)
        z = (fl / scale)
        z5 = fl.rolling(5).sum() / scale
        st = _streak(fl > 0).where(fl.notna())
        for k, v in ((f"{name}_z", z), (f"{name}_z5", z5), (f"{name}_streak", st)):
            f[k] = v.shift(1).ffill(limit=5).reindex(C.index)
        pos = (fl > 0).astype(float).where(fl.notna())
        both = pos if both is None else both * pos
    f["both_buy"] = both.shift(1).ffill(limit=5).reindex(C.index)
    return f


def build(p: dict[str, pd.DataFrame], flows: dict[str, pd.DataFrame] | None = None
          ) -> tuple[pd.DataFrame, pd.Series]:
    """(피처 long DataFrame, 익일 시가 수익률 Series) 를 돌려준다. index = (date code)."""
    O, H, L, C, V = p["open"], p["high"], p["low"], p["close"], p["volume"]
    ret = C.pct_change(fill_method=None)
    value = C * V
    f: dict[str, pd.DataFrame] = {}

    # 가격 모멘텀
    for n in (1, 3, 5, 10, 20, 60):
        f[f"ret{n}"] = C / C.shift(n) - 1
    f["body"] = C / O - 1                          # 양봉 크기
    f["gap"] = O / C.shift(1) - 1                  # 시가 갭
    rng = (H - L).replace(0, np.nan)
    f["close_pos"] = (C - L) / rng                 # 고가 마감 여부
    f["upper_wick"] = (H - np.maximum(O, C)) / C   # 윗꼬리
    f["day_range"] = H / L - 1

    # 거래량
    v20 = V.rolling(20, min_periods=10).mean().shift(1)
    f["vol_ratio"] = V / v20
    f["vol_ratio5"] = V.rolling(5).mean() / v20
    f["log_value"] = np.log1p(value)
    f["log_value20"] = np.log1p(value.rolling(20, min_periods=10).mean())

    # 이동평균 이격과 정배열
    ma = {n: C.rolling(n, min_periods=n).mean() for n in (5, 20, 60, 120)}
    for n, m in ma.items():
        f[f"dist_ma{n}"] = C / m - 1
    f["ma_align"] = ((ma[5] > ma[20]).astype(float) + (ma[20] > ma[60]).astype(float)
                     + (ma[60] > ma[120]).astype(float))
    f["ma20_slope"] = ma[20] / ma[20].shift(5) - 1

    # 신고가 돌파
    for n in (20, 60, 250):
        hi = H.rolling(n, min_periods=min(n, 60)).max().shift(1)
        lo = L.rolling(n, min_periods=min(n, 60)).min().shift(1)
        f[f"from_high{n}"] = C / hi - 1
        f[f"pos{n}"] = (C - lo) / (hi - lo)

    # 변동성 수축
    vol20 = ret.rolling(20).std()
    f["vol20"] = vol20
    f["squeeze"] = ret.rolling(5).std() / vol20
    f["range20"] = H.rolling(20).max() / L.rolling(20).min() - 1
    f["up10"] = (ret > 0).astype(float).rolling(10).sum()
    f["limit_hits20"] = (ret > 0.25).astype(float).rolling(20).sum()

    # 시장 대비 위치
    f["rank_ret1"] = f["ret1"].rank(axis=1, pct=True)
    f["rank_ret20"] = f["ret20"].rank(axis=1, pct=True)
    f["rank_vol_ratio"] = f["vol_ratio"].rank(axis=1, pct=True)
    f["mkt_ret1"] = pd.DataFrame(
        np.repeat(ret.mean(axis=1).to_numpy()[:, None], C.shape[1], axis=1),
        index=C.index, columns=C.columns)
    f["log_price"] = np.log(C)
    if flows is not None:
        f.update(flow_features(flows, C))

    X = pd.concat({k: v.stack(future_stack=True) for k, v in f.items()}, axis=1)
    X.index.names = ["date", "code"]
    # 라벨: 오늘 15시 가격 (종가 근사) 에 사서 익일 시가에 판 수익률
    y = (O.shift(-1) / C - 1).stack(future_stack=True).reindex(X.index)

    ok = (C.stack(future_stack=True).reindex(X.index) >= MIN_PRICE) & X["ret60"].notna()
    ok &= O.stack(future_stack=True).reindex(X.index).notna() & (X["log_value"] > 0)
    X = X[ok].replace([np.inf, -np.inf], np.nan).astype("float32")
    return X, y[ok]
