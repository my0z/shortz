"""장중 (15:00 전후) 에 실행해 익일 급등 후보를 뽑고 점검 결과를 저장한다.

    python -m surge.live            # 네이버에서 받아 모델 학습 후 추천
    python -m surge.live --top 5

결과: surge_data/picks/YYYYMMDD.json (추천+점검+카톡 문구) / surge_data/daily/YYYYMMDD.csv (오늘 봉 스냅샷)
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from . import features, history, model, naver

KST = ZoneInfo("Asia/Seoul")
ROOT = Path(__file__).resolve().parent.parent / "surge_data"
MIN_VALUE20 = 1e9   # 20일 평균 거래대금 10억 미만 제외
LIMIT_UP = 0.29     # 이미 상한가면 매수 불가
COST = 0.002        # 왕복 수수료+세금


def reasons(r: pd.Series) -> str:
    tags = []
    if r["from_high60"] > 0:
        tags.append("60일신고가")
    elif r["from_high20"] > 0:
        tags.append("20일신고가")
    if r["ma_align"] == 3:
        tags.append("정배열")
    if r["vol_ratio"] >= 3:
        tags.append(f"거래량{r['vol_ratio']:.0f}배")
    if r["squeeze"] < 0.6:
        tags.append("변동성수축")
    if r["body"] > 0.05 and r["close_pos"] > 0.8:
        tags.append("고가권장대양봉")
    if r.get("both_buy") == 1:
        tags.append("전일기관외인동반매수")
    elif r.get("inst_streak", 0) >= 3:
        tags.append(f"기관{int(r['inst_streak'])}일연속")
    return " ".join(tags) or "-"


def check(Xt: pd.DataFrame, names: pd.Series) -> pd.Series:
    """매수 가능한 종목만 남기는 점검. 통과 여부 Series (index=code)."""
    code = Xt.index
    name = names.reindex(code).fillna("")
    ok = pd.Series(True, index=code)
    ok &= Xt["ret1"] < LIMIT_UP                                  # 상한가 잔량 매수 불가
    ok &= np.expm1(Xt["log_value20"]) >= MIN_VALUE20             # 유동성
    ok &= ~name.str.contains("스팩").to_numpy()                   # 스팩 제외
    ok &= ~name.str.contains(r"우$|우B$|우\(").to_numpy()          # 우선주 제외
    ok &= pd.Series(code.str[-1] == "0", index=code)             # 보통주 코드
    return ok


def holdout(X: pd.DataFrame, y: pd.Series, days: int, top: int, names: pd.Series) -> dict:
    """최근 days 거래일을 빼고 학습해 그 기간 점검 통과 상위 top 성과를 잰다."""
    d = X.index.get_level_values("date")
    lab = y.notna()
    dates = d[lab].unique().sort_values()
    test = dates[-days:]
    m = model.fit_reg(X[d < test[0]], y[d < test[0]])
    Xt = X[d.isin(test)]
    p = pd.Series(m.predict(Xt), index=Xt.index)
    rets, base = [], []
    for day, s in p.groupby(level="date"):
        yt = y.reindex(s.index)
        ok = check(Xt.xs(day, level="date"), names).to_numpy()
        pick = s[ok].nlargest(top).index
        rets.append(yt[pick].fillna(0).mean() - COST)
        base.append(yt.mean())
    rets = np.array(rets)
    return {"days": days, "pick_ret": float(rets.mean()), "mkt_ret": float(np.nanmean(base)),
            "win_days": float((rets > 0).mean())}


def message(day: datetime, now: datetime, picks: list[dict], ho: dict) -> str:
    lines = [f"[종목 추천] {day:%m/%d} {now:%H:%M} 종가매수 익일시가매도"]
    for i, p in enumerate(picks, 1):
        lines.append(f"{i}.{p['name']}({p['code']}) {p['price']}원 기대{p['exp']:+.1%}")
    lines.append(f"최근{ho['days']}일 비용후 평균{ho['pick_ret']:+.2%} 승률{ho['win_days']:.0%}")
    text = "\n".join(lines)
    while len(text) > 200 and len(lines) > 2:   # 카톡 200자 제한
        lines.pop(-2)
        text = "\n".join(lines)
    return text


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--count", type=int, default=760, help="종목당 일봉 개수 (약 3년)")
    ap.add_argument("--holdout-days", type=int, default=60)
    ap.add_argument("--force", action="store_true", help="오늘 봉이 없어도 (휴장) 마지막 봉으로 추천")
    args = ap.parse_args()

    now = datetime.now(KST)
    stamp = now.strftime("%Y%m%d")
    (ROOT / "picks").mkdir(parents=True, exist_ok=True)
    (ROOT / "daily").mkdir(parents=True, exist_ok=True)
    out = ROOT / "picks" / f"{stamp}.json"

    uni = naver.universe()
    print(f"종목 {len(uni)}개 일봉 수집")
    long = naver.all_daily(uni["code"].tolist(), args.count)
    last = long["date"].max()
    long[long["date"] == last].to_csv(ROOT / "daily" / f"{stamp}.csv", index=False)

    if last.date() != now.date() and not args.force:
        out.write_text(json.dumps({"status": "closed", "asof": now.isoformat(),
                                   "last_bar": f"{last:%Y-%m-%d}"}, ensure_ascii=False, indent=1))
        print(f"오늘 봉 없음 (마지막 {last:%Y-%m-%d}). 휴장으로 기록")
        return

    try:
        print(history.refresh())
    except Exception as e:  # aut.stock 을 못 읽어도 보유 데이터로 진행
        print(f"수급 갱신 실패: {e}")
    fl = history.flows()
    flow_last = fl["inst"].index.max()
    X, y = features.build(naver.wide(long), fl)
    names = uni.set_index("code")["name"]
    ho = holdout(X, y, args.holdout_days, args.top, names)
    print(f"홀드아웃 {ho}")
    m = model.fit_reg(X, y)

    Xt = X.xs(last, level="date")
    prob = pd.Series(m.predict(Xt), index=Xt.index)
    passed = check(Xt, names)
    ranked = prob.sort_values(ascending=False)
    dropped = [c for c in ranked.index[:args.top * 3] if not passed[c]]
    chosen = [c for c in ranked.index if passed[c]][:args.top]

    close = long[long["date"] == last].set_index("code")["close"]
    picks = [{"code": c, "name": names.get(c, c), "price": int(close[c]),
              "ret1": float(Xt.loc[c, "ret1"]), "exp": float(prob[c]),
              "reasons": reasons(Xt.loc[c])} for c in chosen]
    result = {
        "status": "ok", "asof": now.isoformat(), "bar_date": f"{last:%Y-%m-%d}",
        "flow_last": f"{flow_last:%Y-%m-%d}",
        "picks": picks, "holdout": ho,
        "dropped_by_check": [{"code": c, "name": names.get(c, c), "exp": float(prob[c]),
                              "ret1": float(Xt.loc[c, "ret1"])} for c in dropped],
        "message": message(last, now, picks, ho),
    }
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1))
    print(result["message"])


if __name__ == "__main__":
    main()
