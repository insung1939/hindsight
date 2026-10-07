"""이벤트 스터디 계산 — 순수 함수. 시세는 밖에서 넣는다.

series: [(date, close, volume|None)] 오름차순.  T0 = 사건일(event_day) 이후(당일 포함) 첫 거래일.  T+n = 그로부터 n 거래일 뒤.
event_day 는 "영상을 본 사람이 처음 거래할 수 있는 날" — 시장별 장 마감 시각 기준(event_day 함수).
"""
from bisect import bisect_left
from datetime import date, datetime, time, timedelta, timezone
from statistics import mean, median

HORIZONS = (5, 20, 60)
VOL_BEFORE, VOL_AFTER = 20, 5  # 거래량 비교 창: 언급 전 20거래일 평균 vs 언급 뒤 5거래일(T0 포함) 평균

KST = timezone(timedelta(hours=9))
EST = timezone(timedelta(hours=-5))  # 서머타임(-4)을 무시해도 16:00 컷오프는 한 시간 안쪽 차이라 일별 판정에 거의 영향 없음


def event_day(published_utc: datetime, market: str) -> date:
    """게시 시각(UTC) → 수익률을 세기 시작할 날.
    KRX: 한국 15:30 전이면 그날, 뒤면 다음 날(다음 거래일은 forward_returns 가 찾는다).
    US: 미국 동부 16:00 기준 같은 규칙.  CRYPTO: 업비트 일봉은 09:00 KST 시작 → 그 캔들의 종가(다음 날 09:00)가 첫 체결 가능 가격이므로
    09:00 이후 게시는 그날 캔들, 09:00 전 게시는 전날 캔들."""
    pub = published_utc.replace(tzinfo=timezone.utc)
    if market == "US":
        local = pub.astimezone(EST)
        return local.date() if local.time() < time(16, 0) else local.date() + timedelta(days=1)
    local = pub.astimezone(KST)
    if market == "CRYPTO":
        return local.date() if local.time() >= time(9, 0) else local.date() - timedelta(days=1)
    return local.date() if local.time() < time(15, 30) else local.date() + timedelta(days=1)


def _empty() -> dict:
    return {"t0_date": None, "t0_close": None, "vol_ratio": None, **{f"r{h}": None for h in HORIZONS}}


def forward_returns(series: list, event_day_: date) -> dict:
    """반환: {"t0_date", "t0_close", "r5", "r20", "r60", "vol_ratio"} — 아직 n 거래일이 안 지났으면 해당 값은 None.
    vol_ratio = 언급 뒤 5거래일 평균 거래량 / 언급 전 20거래일 평균 거래량 (거래량이 없는 출처면 None)."""
    if not series:
        return _empty()
    dates = [row[0] for row in series]
    i0 = bisect_left(dates, event_day_)
    if i0 >= len(series) or (dates[i0] - event_day_).days > 7:  # 사건 후 일주일 안에 거래일이 없으면 시세 없음
        return _empty()
    t0_close = series[i0][1]
    out = {"t0_date": dates[i0], "t0_close": t0_close, "vol_ratio": None}
    for h in HORIZONS:
        j = i0 + h
        out[f"r{h}"] = (series[j][1] / t0_close - 1) if j < len(series) and t0_close else None
    before = [row[2] for row in series[max(0, i0 - VOL_BEFORE):i0] if len(row) > 2 and row[2]]
    after = [row[2] for row in series[i0:i0 + VOL_AFTER] if len(row) > 2 and row[2]]
    if len(before) >= 5 and len(after) >= VOL_AFTER:
        out["vol_ratio"] = round(mean(after) / mean(before), 4) if mean(before) else None
    return out


def summarize(rows: list[dict], horizon: int) -> dict:
    """rows: [{"r": float|None, "x": float|None, "v": float|None}] → 분포 요약. 표본 30 미만은 low_sample=True."""
    r = [x["r"] for x in rows if x["r"] is not None]
    x = [x["x"] for x in rows if x["x"] is not None]
    v = [x.get("v") for x in rows if x.get("v") is not None]
    d = [x.get("d") for x in rows if x.get("d") is not None]
    if not r:
        return {"horizon": horizon, "n": 0, "low_sample": True}
    buckets = [(-1, -0.2), (-0.2, -0.1), (-0.1, -0.05), (-0.05, 0), (0, 0.05), (0.05, 0.1), (0.1, 0.2), (0.2, 9)]
    hist = [{"from": a, "to": b, "n": sum(1 for val in r if a <= val < b)} for a, b in buckets]
    sr = sorted(r)
    return {"horizon": horizon, "n": len(r), "low_sample": len(r) < 30,
            "mean": round(mean(r), 4), "median": round(median(r), 4), "win_rate": round(sum(1 for val in r if val > 0) / len(r), 4),
            "excess_mean": round(mean(x), 4) if x else None, "excess_n": len(x),
            "excess_win_rate": round(sum(1 for val in x if val > 0) / len(x), 4) if x else None,
            "p10": round(sr[int(len(r) * 0.1)], 4), "p90": round(sr[min(len(r) - 1, int(len(r) * 0.9))], 4),
            "vol_ratio_median": round(median(v), 3) if v else None, "vol_up_rate": round(sum(1 for val in v if val > 1) / len(v), 4) if v else None,
            "vol_n": len(v),
            "disclosure_rate": round(sum(1 for val in d if val) / len(d), 4) if d else None, "disclosure_n": len(d),  # 사건일 ±3일 공시 동반 비율
            "histogram": hist}
