"""시세·환율 수집 어댑터. 어댑터 하나 = 출처 하나. 키가 없는 출처(업비트·Stooq)는 바로 동작하고,
키가 필요한 출처(공공데이터포털·수출입은행)는 환경변수가 없으면 건너뛴다."""
from datetime import date, datetime, timedelta

import httpx

from routine_common.settings import env

UA = {"User-Agent": "routine-market-data/0.1 (+https://github.com/insung1939/routine)"}


def upbit_daily(symbol: str, days: int = 200) -> list[tuple[date, float]]:
    """업비트 일봉. 키 불필요. 한 번에 200개까지라 `to` 로 거슬러 올라가며 days 만큼 모은다.
    출처: https://docs.upbit.com (Open API)."""
    out, to = [], None
    while len(out) < days:
        params = {"market": symbol, "count": min(200, days - len(out))}
        if to:
            params["to"] = to
        r = httpx.get("https://api.upbit.com/v1/candles/days", params=params, headers=UA, timeout=15)
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        out += [(datetime.fromisoformat(c["candle_date_time_kst"]).date(), float(c["trade_price"])) for c in batch]
        to = batch[-1]["candle_date_time_utc"] + "Z"
    return out


def yahoo_daily(symbol: str, years: int = 10) -> list[tuple[date, float]]:
    """Yahoo Finance chart API. 키 불필요. 심볼 예: SPY, QQQ, 3067.HK. 출처: https://finance.yahoo.com
    (Stooq 는 2026년 현재 JS 검증을 요구해 스크립트로 못 받는다.)"""
    r = httpx.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
                  params={"range": f"{years}y", "interval": "1d"},
                  headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    closes = res["indicators"]["quote"][0]["close"]
    out = []
    for ts, c in zip(res["timestamp"], closes):
        if c is None:
            continue
        out.append((datetime.utcfromtimestamp(ts).date(), float(c)))
    return out


def datagokr_krx_daily(item_name: str, begin: date, end: date) -> list[tuple[date, float]]:
    """공공데이터포털 「금융위원회_주식시세정보」. DATA_GO_KR_KEY 필요. 종목명으로 조회한다."""
    key = env("DATA_GO_KR_KEY")
    if not key:
        return []
    url = "https://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo"
    params = {"serviceKey": key, "resultType": "json", "numOfRows": 400, "pageNo": 1,
              "itmsNm": item_name, "beginBasDt": begin.strftime("%Y%m%d"), "endBasDt": end.strftime("%Y%m%d")}
    r = httpx.get(url, params=params, headers=UA, timeout=20)
    r.raise_for_status()
    items = r.json().get("response", {}).get("body", {}).get("items", {}).get("item", [])
    return [(datetime.strptime(i["basDt"], "%Y%m%d").date(), float(i["clpr"])) for i in items]


def koreaexim_fx(day: date) -> dict[str, float]:
    """한국수출입은행 환율 Open API. KOREAEXIM_KEY 필요. 반환: {'USD': 1350.5, 'HKD': 173.2, ...}"""
    key = env("KOREAEXIM_KEY")
    if not key:
        return {}
    r = httpx.get("https://www.koreaexim.go.kr/site/program/financial/exchangeJSON",
                  params={"authkey": key, "searchdate": day.strftime("%Y%m%d"), "data": "AP01"},
                  headers=UA, timeout=20)
    r.raise_for_status()
    out = {}
    for row in r.json() or []:
        unit = row.get("cur_unit", "")
        rate = float(str(row.get("deal_bas_r", "0")).replace(",", ""))
        if unit.startswith("JPY"):  # JPY(100) 표기
            out["JPY"] = rate / 100
        elif len(unit) == 3:
            out[unit] = rate
    return out


def recent_business_days(n: int) -> list[date]:
    days, d = [], date.today()
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d -= timedelta(days=1)
    return days
