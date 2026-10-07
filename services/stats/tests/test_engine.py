"""이벤트 스터디 규칙 테스트 — 사건일(시장별 마감 기준), 수익률, 거래량 비율."""
from datetime import date, datetime, timedelta

from engine import event_day, forward_returns, summarize


def test_event_day_krx_cutoff_1530_kst():
    assert event_day(datetime(2026, 3, 2, 5, 0), "KRX") == date(2026, 3, 2)      # 14:00 KST → 그날
    assert event_day(datetime(2026, 3, 2, 7, 0), "KRX") == date(2026, 3, 3)      # 16:00 KST → 다음 날
    assert event_day(datetime(2026, 3, 2, 16, 0), "KRX") == date(2026, 3, 3)     # 01:00 KST(3일) → 3일


def test_event_day_us_cutoff_1600_est():
    assert event_day(datetime(2026, 3, 2, 20, 0), "US") == date(2026, 3, 2)      # 15:00 EST → 그날
    assert event_day(datetime(2026, 3, 2, 22, 0), "US") == date(2026, 3, 3)      # 17:00 EST → 다음 날


def test_event_day_crypto_0900_kst_candle():
    assert event_day(datetime(2026, 3, 2, 3, 0), "CRYPTO") == date(2026, 3, 2)   # 12:00 KST → 그날 캔들
    assert event_day(datetime(2026, 3, 1, 22, 0), "CRYPTO") == date(2026, 3, 1)  # 07:00 KST(2일) → 전날 캔들


def _series(n=90, start=date(2026, 1, 5), vol=1000.0):
    d, out = start, []
    while len(out) < n:
        if d.weekday() < 5:
            out.append((d, 100.0 + len(out), vol))
        d += timedelta(days=1)
    return out


def test_forward_returns_and_pending():
    s = _series()
    fr = forward_returns(s, date(2026, 1, 10))          # 토요일 → 다음 거래일 1/12 가 T0
    assert fr["t0_date"] == date(2026, 1, 12)
    assert round(fr["r5"], 4) == round(s[s.index((date(2026, 1, 12), fr["t0_close"], 1000.0)) + 5][1] / fr["t0_close"] - 1, 4)
    late = forward_returns(s, s[-3][0])
    assert late["r5"] is None and late["r60"] is None  # 아직 안 지남


def test_vol_ratio_after_vs_before():
    s = _series()
    i0 = 30
    for k in range(i0, i0 + 5):
        s[k] = (s[k][0], s[k][1], 3000.0)              # 언급 뒤 5일 거래량 3배
    fr = forward_returns(s, s[i0][0])
    assert fr["vol_ratio"] == 3.0
    no_vol = [(d, c, None) for d, c, _ in s]
    assert forward_returns(no_vol, s[i0][0])["vol_ratio"] is None


def test_summarize_includes_volume_and_excess_win_rate():
    rows = [{"r": 0.1, "x": 0.05, "v": 2.0}, {"r": -0.1, "x": -0.02, "v": 0.5}, {"r": 0.02, "x": 0.01, "v": None}]
    out = summarize(rows, 20)
    assert out["n"] == 3 and out["low_sample"] is True
    assert out["vol_n"] == 2 and out["vol_up_rate"] == 0.5 and out["vol_ratio_median"] == 1.25
    assert out["excess_win_rate"] == round(2 / 3, 4)


def test_summarize_disclosure_rate():
    rows = [{"r": 0.1, "x": 0.0, "d": True}, {"r": 0.0, "x": 0.0, "d": False}, {"r": 0.0, "x": 0.0, "d": None}]
    out = summarize(rows, 5)
    assert out["disclosure_n"] == 2 and out["disclosure_rate"] == 0.5
