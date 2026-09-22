"""추천 기준 비교 연구. 3년 KRX 패널 (시가 종가 수급) 로 워크포워드 검증한다.

    python -m surge.research

15:10 매수 상황을 흉내 낸다: 당일 종가를 매수가로 보고 수급은 전일까지만 쓴다.
청산은 익일 시가 / 익일 종가 두 가지를 본다. 비용 0.2% 차감.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

from . import features, history

COST = 0.002
TOP = 5


def panel_features() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    pn = history.load()
    O = pn["open"].unstack().where(lambda x: x > 0)
    C = pn["close"].unstack()
    fl = {"inst": pn["inst"].unstack(), "foreign": pn["foreign"].unstack()}
    ret = C.pct_change(fill_method=None)
    f = {}
    for n in (1, 3, 5, 10, 20, 60):
        f[f"ret{n}"] = C / C.shift(n) - 1
    f["body"] = C / O - 1
    f["gap"] = O / C.shift(1) - 1
    ma = {n: C.rolling(n, min_periods=n).mean() for n in (5, 20, 60, 120)}
    for n, m in ma.items():
        f[f"dist_ma{n}"] = C / m - 1
    f["ma_align"] = sum((ma[a] > ma[b]).astype(float) for a, b in ((5, 20), (20, 60), (60, 120)))
    for n in (20, 60, 250):
        hi = C.rolling(n, min_periods=min(n, 60)).max().shift(1)
        f[f"from_high{n}"] = C / hi - 1
    vol20 = ret.rolling(20).std()
    f["vol20"] = vol20
    f["squeeze"] = ret.rolling(5).std() / vol20
    f["up10"] = (ret > 0).astype(float).rolling(10).sum()
    f["rank_ret1"] = f["ret1"].rank(axis=1, pct=True)
    f["log_price"] = np.log(C)
    f.update(features.flow_features(fl, C))
    X = pd.concat({k: v.stack(future_stack=True) for k, v in f.items()}, axis=1)
    X.index.names = ["date", "code"]
    nxt_close = (C.shift(-1) / C - 1).stack(future_stack=True).reindex(X.index)
    nxt_open = (O.shift(-1) / C - 1).stack(future_stack=True).reindex(X.index)
    ok = (C.stack(future_stack=True).reindex(X.index) >= features.MIN_PRICE) & X["ret60"].notna()
    ok &= X["ret1"] < 0.29
    ok &= pd.Series(X.index.get_level_values("code").str[-1] == "0", index=X.index)
    X = X[ok].replace([np.inf, -np.inf], np.nan).astype("float32")
    Y = pd.DataFrame({"close": nxt_close[ok], "open": nxt_open[ok]})
    return X, Y


def targets(Y: pd.DataFrame) -> dict:
    cs = Y["close"].groupby(level="date").transform(lambda s: s.rank(pct=True))
    return {
        "A 급등확률(+5%)": ("clf", (Y["close"] >= 0.05).astype(int)),
        "B 기대수익 회귀(종가)": ("reg", Y["close"].clip(-0.15, 0.15)),
        "C 순위 회귀(종가)": ("reg", cs),
        "D 기대수익 회귀(시가)": ("reg", Y["open"].clip(-0.15, 0.15)),
        "E 상승확률(종가>+1%)": ("clf", (Y["close"] > 0.01).astype(int)),
    }


def run(test_days: int = 240, step: int = 40, max_rows: int = 500_000) -> pd.DataFrame:
    X, Y = panel_features()
    dates = X.index.get_level_values("date")
    ud = dates.unique().sort_values()
    ud = ud[:-1]  # 마지막 날은 라벨 없음
    test = ud[-test_days:]
    rng = np.random.default_rng(0)
    rows = []
    for name, (kind, t) in targets(Y).items():
        for k in range(0, len(test), step):
            block = test[k:k + step]
            tr = (dates < block[0]) & (dates >= block[0] - pd.Timedelta(days=730)) & t.notna().to_numpy()
            Xi, ti = X[tr], t[tr]
            # 학습 끝을 1일 띄워 라벨 누수 방지
            last_tr = ud[ud.get_loc(block[0]) - 1]
            keep = Xi.index.get_level_values("date") < last_tr
            Xi, ti = Xi[keep], ti[keep]
            if len(Xi) > max_rows:
                idx = rng.choice(len(Xi), max_rows, replace=False)
                Xi, ti = Xi.iloc[idx], ti.iloc[idx]
            if kind == "clf":
                m = HistGradientBoostingClassifier(max_iter=250, learning_rate=0.05, min_samples_leaf=300,
                                                   l2_regularization=1.0, random_state=0).fit(Xi, ti)
            else:
                m = HistGradientBoostingRegressor(max_iter=250, learning_rate=0.05, min_samples_leaf=300,
                                                  l2_regularization=1.0, random_state=0).fit(Xi, ti)
            te = dates.isin(block)
            Xt = X[te]
            s = m.predict_proba(Xt)[:, 1] if kind == "clf" else m.predict(Xt)
            s = pd.Series(s, index=Xt.index)
            for day, g in s.groupby(level="date"):
                pick = g.nlargest(TOP).index
                y = Y.loc[pick].fillna(0)
                rows.append({"model": name, "date": day,
                             "ret_close": y["close"].mean() - COST, "ret_open": y["open"].mean() - COST,
                             "hit5": (y["close"] >= 0.05).mean(), "mkt": Y.loc[g.index, "close"].mean()})
        print(f"{name} 완료")
    return pd.DataFrame(rows)


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("model")
    out = pd.DataFrame({
        "익일종가청산 평균": g["ret_close"].mean(),
        "종가 승률": g["ret_close"].apply(lambda s: (s > 0).mean()),
        "종가 샤프(연)": g["ret_close"].apply(lambda s: s.mean() / s.std() * np.sqrt(250)),
        "익일시가청산 평균": g["ret_open"].mean(),
        "시가 승률": g["ret_open"].apply(lambda s: (s > 0).mean()),
        "시가 샤프(연)": g["ret_open"].apply(lambda s: s.mean() / s.std() * np.sqrt(250)),
        "+5%적중": g["hit5"].mean(),
    })
    return out


if __name__ == "__main__":
    res = run()
    res.to_csv(history.DIR.parent / "research_compare.csv", index=False)
    pd.set_option("display.width", 200)
    print(summarize(res).to_string(float_format=lambda v: f"{v:.4f}"))
    print(f"시장 평균 익일 종가 수익 {res.groupby('date')['mkt'].first().mean():+.4%}")
