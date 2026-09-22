"""익일 급등 후보 추천 CLI.

사용법:
    python -m surge.recommend                # 최신 거래일 기준 상위 20종목
    python -m surge.recommend --backtest     # 최근 120거래일 워크포워드 검증 먼저 출력
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from . import data, features, model

OUT = Path(__file__).resolve().parent.parent / "output"


def reasons(row: pd.Series) -> str:
    tags = []
    if row["from_high60"] >= -0.001:
        tags.append("60일 신고가")
    elif row["from_high20"] >= -0.001:
        tags.append("20일 신고가")
    if row["ma_align"] == 3:
        tags.append("정배열")
    if row["squeeze"] < 0.6:
        tags.append("변동성 수축")
    if row["body"] > 0.05:
        tags.append(f"장대양봉 {row['body']:+.1%}")
    if row["both_buy"] == 1:
        tags.append("기관·외국인 동반매수")
    elif row["inst_streak"] >= 3:
        tags.append(f"기관 {int(row['inst_streak'])}일 연속")
    elif row["frgn_streak"] >= 3:
        tags.append(f"외국인 {int(row['frgn_streak'])}일 연속")
    return " / ".join(tags) or "-"


def main() -> None:
    ap = argparse.ArgumentParser(description="일봉 차트 기반 익일 급등 후보 추천")
    ap.add_argument("--panel", help="panel.parquet 경로 (기본: aut.stock 에서 자동 다운로드)")
    ap.add_argument("--refresh", action="store_true", help="패널을 새로 내려받는다")
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--backtest", action="store_true", help="워크포워드 검증 결과를 함께 출력")
    ap.add_argument("--test-days", type=int, default=120)
    args = ap.parse_args()

    panel = data.load_panel(args.panel, args.refresh)
    print("피처 생성 중...")
    X, y = features.build(panel)

    if args.backtest:
        print(f"워크포워드 검증 (최근 {args.test_days}거래일 상위 {args.top}종목)")
        wf = model.walk_forward(X, y, test_days=args.test_days, top=args.top)
        OUT.mkdir(exist_ok=True)
        wf.to_csv(OUT / "surge_backtest.csv")
        print(f"  급등(+{features.SURGE:.0%}) 기본 확률   {wf['base_rate'].mean():.2%}")
        print(f"  추천 종목 적중률          {wf['hit_rate'].mean():.2%}")
        print(f"  추천 종목 익일 평균수익   {wf['pick_ret'].mean():+.2%}")
        print(f"  전체 시장 익일 평균수익   {wf['mkt_ret'].mean():+.2%}")
        print(f"  추천 수익 > 0 인 날 비율  {(wf['pick_ret'] > 0).mean():.1%}")

    print("최종 모델 학습 중...")
    m = model.fit(X, y)
    last = X.index.get_level_values("date").max()
    Xt = X.xs(last, level="date", drop_level=False)
    prob = pd.Series(m.predict_proba(Xt)[:, 1], index=Xt.index.get_level_values("ticker"))
    pick = prob.nlargest(args.top)

    close = panel["close"].loc[last]
    rows = []
    for t, p in pick.items():
        r = Xt.xs(t, level="ticker").iloc[0]
        rows.append({"종목코드": t, "급등확률": f"{p:.1%}", "종가": int(close[t]),
                     "당일": f"{r['ret1']:+.1%}", "20일": f"{r['ret20']:+.1%}",
                     "근거": reasons(r)})
    table = pd.DataFrame(rows)
    OUT.mkdir(exist_ok=True)
    table.to_csv(OUT / f"surge_{last:%Y%m%d}.csv", index=False, encoding="utf-8-sig")
    print(f"\n{last:%Y-%m-%d} 종가 기준 익일 급등 후보 (+{features.SURGE:.0%} 이상 확률 순)")
    print(table.to_string(index=False))
    print("\n참고용이다. 투자 판단과 손실 책임은 본인에게 있다.")


if __name__ == "__main__":
    main()
