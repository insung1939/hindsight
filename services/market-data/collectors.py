"""수집 어댑터. 어댑터 하나 = 출처 하나. 키가 없는 출처(업비트·Yahoo)는 바로 동작하고,
키가 필요한 출처(공공데이터포털·DART)는 환경변수가 없으면 건너뛴다."""
import io
import re
import zipfile
from datetime import date, datetime
from xml.etree import ElementTree

import httpx

from hs_common.settings import env

UA = {"User-Agent": "hindsight-market-data/0.1 (+https://github.com/insung1939/hindsight)"}
BROWSER = {"User-Agent": "Mozilla/5.0"}


def upbit_daily(symbol: str, days: int = 200) -> list[tuple[date, float]]:
    """업비트 일봉. 한 번에 200개까지라 `to` 로 거슬러 올라간다. 출처: https://docs.upbit.com"""
    out, to = [], None
    while len(out) < days:
        params = {"market": symbol, "count": min(200, days - len(out))}
        if to:
            params["to"] = to
        r = _get_retry("https://api.upbit.com/v1/candles/days", params)  # 업비트는 초당 10회 제한 → 429 면 잠깐 쉬고 재시도
        batch = r.json()
        if not batch:
            break
        out += [(datetime.fromisoformat(c["candle_date_time_kst"]).date(), float(c["trade_price"])) for c in batch]
        to = batch[-1]["candle_date_time_utc"] + "Z"
    return out


def _get_retry(url: str, params: dict, tries: int = 4) -> httpx.Response:
    import time
    for i in range(tries):
        r = httpx.get(url, params=params, headers=UA, timeout=15)
        if r.status_code != 429:
            r.raise_for_status()
            return r
        time.sleep(0.5 * (i + 1))
    r.raise_for_status()
    return r


def upbit_markets() -> list[dict]:
    """업비트 KRW 마켓 목록(한글명 포함). 코인 사전을 자동으로 채운다."""
    r = httpx.get("https://api.upbit.com/v1/market/all", params={"is_details": "false"}, headers=UA, timeout=15)
    r.raise_for_status()
    return [m for m in r.json() if m["market"].startswith("KRW-")]


def yahoo_daily(symbol: str, years: int = 5) -> list[tuple[date, float]]:
    """Yahoo Finance chart API. 미국 티커, 지수(^KS11), 국내 대체 심볼(005930.KS) 모두 된다."""
    r = httpx.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
                  params={"range": f"{years}y", "interval": "1d"}, headers=BROWSER, timeout=20)
    r.raise_for_status()
    result = r.json()["chart"].get("result")
    if not result:
        return []
    res = result[0]
    closes = res["indicators"]["quote"][0]["close"]
    return [(datetime.utcfromtimestamp(ts).date(), float(c)) for ts, c in zip(res["timestamp"], closes) if c is not None]


def datagokr_krx_daily(item_name: str, begin: date, end: date) -> list[tuple[date, float]]:
    """공공데이터포털 「금융위원회_주식시세정보」. DATA_GO_KR_KEY 필요. 종목명으로 조회."""
    key = env("DATA_GO_KR_KEY")
    if not key:
        return []
    url = "https://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo"
    params = {"serviceKey": key, "resultType": "json", "numOfRows": 400, "pageNo": 1, "itmsNm": item_name,
              "beginBasDt": begin.strftime("%Y%m%d"), "endBasDt": end.strftime("%Y%m%d")}
    r = httpx.get(url, params=params, headers=UA, timeout=20)
    r.raise_for_status()
    items = r.json().get("response", {}).get("body", {}).get("items", {}).get("item", [])
    return [(datetime.strptime(i["basDt"], "%Y%m%d").date(), float(i["clpr"])) for i in items]


def dart_listed_companies() -> list[dict]:
    """DART corpCode.xml — 전 회사 목록 중 stock_code 가 있는(상장) 회사만. DART_KEY 필요.
    출처: https://opendart.fss.or.kr (개발가이드 › 고유번호). 월 1회면 충분하다."""
    key = env("DART_KEY")
    if not key:
        return []
    r = httpx.get("https://opendart.fss.or.kr/api/corpCode.xml", params={"crtfc_key": key}, headers=UA, timeout=60)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        xml = z.read(z.namelist()[0])
    out = []
    for el in ElementTree.fromstring(xml).iter("list"):
        code = (el.findtext("stock_code") or "").strip()
        if not code:
            continue
        out.append({"stock_code": code, "corp_name": (el.findtext("corp_name") or "").strip(),
                    "corp_code": (el.findtext("corp_code") or "").strip()})
    return out


_SUFFIX = re.compile(r"(주식회사|\(주\)|㈜)")


def normalize_corp_name(name: str) -> str:
    return _SUFFIX.sub("", name).strip()
