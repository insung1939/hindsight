"""적립식(DCA) 시뮬레이션 엔진. 순수 함수라 테스트하기 쉽고, 데이터는 밖에서 넣는다.

prices: {asset_id: {date: close}}  (자산 통화 기준)
fx:     {currency: {date: rate_to_krw}}  KRW 는 항상 1.0
"""
from bisect import bisect_left
from datetime import date


def _lookup(series: dict[date, float], keys: list[date], day: date) -> tuple[date, float] | None:
    """day 이후(같은 날 포함) 첫 거래일의 값. 휴장일이면 다음 거래일에 산다."""
    i = bisect_left(keys, day)
    if i >= len(keys):
        return None
    return keys[i], series[keys[i]]


def month_iter(start: date, end: date, buy_day: int):
    y, m = start.year, start.month
    while True:
        d = date(y, m, min(buy_day, 28))
        if d > end:
            return
        if d >= start:
            yield d
        m += 1
        if m > 12:
            y, m = y + 1, 1


def simulate_dca(weights: dict[str, float], monthly_amount_krw: float, start: date, end: date, buy_day: int,
                 prices: dict[str, dict[date, float]], currencies: dict[str, str],
                 fx: dict[str, dict[date, float]]) -> dict:
    keys = {a: sorted(p) for a, p in prices.items()}
    fx_keys = {c: sorted(s) for c, s in fx.items()}
    units = {a: 0.0 for a in weights}
    invested, series, warnings = 0.0, [], []
    for d in month_iter(start, end, buy_day):
        bought_any = False
        for a, w in weights.items():
            hit = _lookup(prices[a], keys[a], d)
            if not hit:
                continue
            _, px = hit
            cur = currencies[a]
            rate = 1.0
            if cur != "KRW":
                fhit = _lookup(fx.get(cur, {}), fx_keys.get(cur, []), d) if fx.get(cur) else None
                if fhit:
                    rate = fhit[1]
                else:
                    warnings.append(f"{d}: {cur} 환율 없음, 폴백 사용")
                    rate = fx.get("__fallback__", {}).get(cur, 1.0)
            units[a] += (monthly_amount_krw * w) / (px * rate)
            invested += monthly_amount_krw * w
            bought_any = True
        if bought_any:
            series.append({"date": str(d), "invested_krw": round(invested),
                           "value_krw": round(_value(units, d, prices, keys, currencies, fx, fx_keys))})
    if not series:
        return {"final_value_krw": 0, "invested_krw": 0, "return_pct": 0, "max_drawdown_pct": 0,
                "months": 0, "series": [], "warnings": warnings + ["기간 내 시세 없음"]}
    final = series[-1]["value_krw"]
    peak, mdd = 0.0, 0.0
    for p in series:
        peak = max(peak, p["value_krw"])
        if peak:
            mdd = min(mdd, (p["value_krw"] - peak) / peak)
    return {"final_value_krw": final, "invested_krw": round(invested),
            "return_pct": round((final / invested - 1) * 100, 2) if invested else 0.0,
            "max_drawdown_pct": round(mdd * 100, 2), "months": len(series), "series": series,
            "warnings": sorted(set(warnings))[:10]}


def _value(units, d, prices, keys, currencies, fx, fx_keys) -> float:
    total = 0.0
    for a, u in units.items():
        if not u:
            continue
        i = bisect_left(keys[a], d)
        i = min(i, len(keys[a]) - 1)
        if keys[a][i] > d and i > 0:
            i -= 1
        px = prices[a][keys[a][i]]
        cur = currencies[a]
        rate = 1.0
        if cur != "KRW":
            fk = fx_keys.get(cur, [])
            if fk:
                j = min(bisect_left(fk, d), len(fk) - 1)
                if fk[j] > d and j > 0:
                    j -= 1
                rate = fx[cur][fk[j]]
            else:
                rate = fx.get("__fallback__", {}).get(cur, 1.0)
        total += u * px * rate
    return total
