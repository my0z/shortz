"""일봉 차트와 수급으로 종목별 피처를 만든다. 모든 값은 당일 종가 시점까지의 정보만 쓴다."""

from __future__ import annotations

import numpy as np
import pandas as pd

SURGE = 0.05  # 익일 종가 기준 +5% 이상을 급등으로 본다
MIN_PRICE = 1000


def _streak(pos: pd.DataFrame) -> pd.DataFrame:
    """연속 True 일수."""
    out = np.zeros(pos.shape)
    arr = pos.to_numpy()
    run = np.zeros(pos.shape[1])
    for i in range(len(arr)):
        run = np.where(arr[i], run + 1, 0)
        out[i] = run
    return pd.DataFrame(out, index=pos.index, columns=pos.columns)


def build(panel: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.Series]:
    """(피처 long DataFrame, 익일 수익률 Series) 를 돌려준다. index = (date ticker)."""
    O, C, I, F = panel["open"], panel["close"], panel["inst"], panel["foreign"]
    ret = C.pct_change(fill_method=None)
    f: dict[str, pd.DataFrame] = {}

    # 가격 모멘텀
    for n in (1, 3, 5, 10, 20, 60):
        f[f"ret{n}"] = C / C.shift(n) - 1
    f["body"] = C / O - 1                 # 당일 양봉 크기
    f["gap"] = O / C.shift(1) - 1         # 시가 갭

    # 이동평균 이격과 정배열
    ma = {n: C.rolling(n, min_periods=n).mean() for n in (5, 20, 60, 120)}
    for n, m in ma.items():
        f[f"dist_ma{n}"] = C / m - 1
    f["ma_align"] = ((ma[5] > ma[20]).astype(float) + (ma[20] > ma[60]).astype(float)
                     + (ma[60] > ma[120]).astype(float))
    f["ma20_slope"] = ma[20] / ma[20].shift(5) - 1

    # 신고가 돌파 여부
    for n in (20, 60, 250):
        hi = C.rolling(n, min_periods=min(n, 60)).max()
        lo = C.rolling(n, min_periods=min(n, 60)).min()
        f[f"from_high{n}"] = C / hi - 1
        f[f"pos{n}"] = (C - lo) / (hi - lo)

    # 변동성 수축 (스퀴즈)
    vol5 = ret.rolling(5).std()
    vol20 = ret.rolling(20).std()
    f["vol20"] = vol20
    f["squeeze"] = vol5 / vol20
    f["range20"] = C.rolling(20).max() / C.rolling(20).min() - 1
    f["up10"] = (ret > 0).astype(float).rolling(10).sum()
    f["limit_hits20"] = (ret > 0.25).astype(float).rolling(20).sum()

    # 수급 (금액을 20일 평균 절대값으로 정규화)
    for name, flow in (("inst", I), ("frgn", F)):
        scale = flow.abs().rolling(20, min_periods=5).mean().replace(0, np.nan)
        f[f"{name}_z"] = flow / scale
        f[f"{name}_z5"] = flow.rolling(5).sum() / scale
        f[f"{name}_streak"] = _streak(flow > 0)
    f["both_buy"] = ((I > 0) & (F > 0)).astype(float)

    # 시장 대비 위치
    f["rank_ret1"] = f["ret1"].rank(axis=1, pct=True)
    f["rank_ret20"] = f["ret20"].rank(axis=1, pct=True)
    f["mkt_ret1"] = pd.DataFrame(
        np.repeat(ret.mean(axis=1).to_numpy()[:, None], C.shape[1], axis=1),
        index=C.index, columns=C.columns)
    f["log_price"] = np.log(C)

    X = pd.concat({k: v.stack(future_stack=True) for k, v in f.items()}, axis=1)
    X.index.names = ["date", "ticker"]
    y = (C.shift(-1) / C - 1).stack(future_stack=True).reindex(X.index)

    ok = (C.stack(future_stack=True).reindex(X.index) >= MIN_PRICE) & X["ret60"].notna()
    ok &= O.stack(future_stack=True).reindex(X.index).notna()
    X = X[ok].replace([np.inf, -np.inf], np.nan).astype("float32")
    return X, y[ok]
