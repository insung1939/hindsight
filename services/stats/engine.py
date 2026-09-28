"""이벤트 스터디 계산 — 순수 함수. 시세는 밖에서 넣는다.

series: [(date, close)] 오름차순.  T0 = 게시일 이후(당일 포함) 첫 거래일.  T+n = 그로부터 n 거래일 뒤.
"""
from bisect import bisect_left
from datetime import date
from statistics import mean, median

HORIZONS = (5, 20, 60)


def forward_returns(series: list[tuple[date, float]], event_day: date) -> dict:
    """반환: {"t0_date", "t0_close", "r5", "r20", "r60"} — 아직 n 거래일이 안 지났으면 해당 값은 None."""
    if not series:
        return {"t0_date": None, "t0_close": None, **{f"r{h}": None for h in HORIZONS}}
    dates = [d for d, _ in series]
    i0 = bisect_left(dates, event_day)
    if i0 >= len(series) or (dates[i0] - event_day).days > 7:  # 게시 후 일주일 안에 거래일이 없으면 시세 없음
        return {"t0_date": None, "t0_close": None, **{f"r{h}": None for h in HORIZONS}}
    t0_close = series[i0][1]
    out = {"t0_date": dates[i0], "t0_close": t0_close}
    for h in HORIZONS:
        j = i0 + h
        out[f"r{h}"] = (series[j][1] / t0_close - 1) if j < len(series) and t0_close else None
    return out


def summarize(rows: list[dict], horizon: int) -> dict:
    """rows: [{"r": float|None, "x": float|None}] → 분포 요약. 표본 30 미만은 low_sample=True."""
    r = [x["r"] for x in rows if x["r"] is not None]
    x = [x["x"] for x in rows if x["x"] is not None]
    if not r:
        return {"horizon": horizon, "n": 0, "low_sample": True}
    buckets = [(-1, -0.2), (-0.2, -0.1), (-0.1, -0.05), (-0.05, 0), (0, 0.05), (0.05, 0.1), (0.1, 0.2), (0.2, 9)]
    hist = [{"from": a, "to": b, "n": sum(1 for v in r if a <= v < b)} for a, b in buckets]
    return {"horizon": horizon, "n": len(r), "low_sample": len(r) < 30,
            "mean": round(mean(r), 4), "median": round(median(r), 4), "win_rate": round(sum(1 for v in r if v > 0) / len(r), 4),
            "excess_mean": round(mean(x), 4) if x else None, "excess_n": len(x),
            "p10": round(sorted(r)[int(len(r) * 0.1)], 4), "p90": round(sorted(r)[min(len(r) - 1, int(len(r) * 0.9))], 4),
            "histogram": hist}
