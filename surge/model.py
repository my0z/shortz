"""급등 확률 모델 학습과 워크포워드 검증."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

from .features import SURGE


def make_model(seed: int = 0) -> HistGradientBoostingClassifier:
    return HistGradientBoostingClassifier(
        max_iter=300, learning_rate=0.05, max_leaf_nodes=31,
        min_samples_leaf=200, l2_regularization=1.0, random_state=seed)


def fit(X: pd.DataFrame, y: pd.Series, max_rows: int = 600_000, seed: int = 0):
    lab = y.notna()
    Xl, yl = X[lab], (y[lab] >= SURGE).astype(int)
    if len(Xl) > max_rows:
        idx = np.random.default_rng(seed).choice(len(Xl), max_rows, replace=False)
        Xl, yl = Xl.iloc[idx], yl.iloc[idx]
    return make_model(seed).fit(Xl, yl)


def fit_reg(X: pd.DataFrame, y: pd.Series, max_rows: int = 600_000, seed: int = 0):
    """익일 시가 수익률 (±15% 클립) 회귀. 연구 결과 가장 나은 기준 (surge/research.py)."""
    lab = y.notna()
    Xl, yl = X[lab], y[lab].clip(-0.15, 0.15)
    if len(Xl) > max_rows:
        idx = np.random.default_rng(seed).choice(len(Xl), max_rows, replace=False)
        Xl, yl = Xl.iloc[idx], yl.iloc[idx]
    return HistGradientBoostingRegressor(
        max_iter=250, learning_rate=0.05, min_samples_leaf=300,
        l2_regularization=1.0, random_state=seed).fit(Xl, yl)


def walk_forward(X: pd.DataFrame, y: pd.Series, test_days: int = 120,
                 step: int = 20, top: int = 20, gap: int = 1) -> pd.DataFrame:
    """test_days 기간을 step 일 단위로 나눠 그 이전 데이터로만 학습하고 상위 top 종목 성과를 기록한다."""
    dates = X.index.get_level_values("date").unique().sort_values()
    labeled = y.groupby(level="date").count()
    dates = dates[dates.isin(labeled[labeled > 0].index)]
    test = dates[-test_days:]
    rows = []
    for k in range(0, len(test), step):
        block = test[k:k + step]
        # 학습 라벨이 테스트 시작 전에 확정된 날까지만 쓴다
        train_end = dates[dates.get_loc(block[0]) - gap]
        d = X.index.get_level_values("date")
        m = fit(X[d <= train_end], y[d <= train_end])
        Xt = X[d.isin(block)]
        p = pd.Series(m.predict_proba(Xt)[:, 1], index=Xt.index)
        for day, s in p.groupby(level="date"):
            yt = y.reindex(s.index)
            pick = s.nlargest(top).index
            rows.append({
                "date": day,
                "base_rate": (yt >= SURGE).mean(),
                "hit_rate": (yt[pick] >= SURGE).mean(),
                "pick_ret": yt[pick].mean(),
                "mkt_ret": yt.mean(),
            })
        print(f"  {block[0].date()} ~ {block[-1].date()} 검증 완료")
    return pd.DataFrame(rows).set_index("date")
