"""수집 어댑터. 어댑터 하나 = 출처 하나. 키가 없는 출처(업비트·Yahoo)는 바로 동작하고,
키가 필요한 출처(공공데이터포털·DART)는 환경변수가 없으면 건너뛴다."""
import io
import re
import zipfile
from datetime import date, datetime, timedelta
from xml.etree import ElementTree

import httpx

from hs_common.settings import env

UA = {"User-Agent": "hindsight-market-data/0.1 (+https://github.com/insung1939/hindsight)"}
BROWSER = {"User-Agent": "Mozilla/5.0"}


def upbit_daily(symbol: str, days: int = 200) -> list[tuple[date, float, float | None]]:
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
        out += [(datetime.fromisoformat(c["candle_date_time_kst"]).date(), float(c["trade_price"]), float(c.get("candle_acc_trade_volume") or 0) or None)
                for c in batch]
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


def yahoo_daily(symbol: str, years: int = 5) -> list[tuple[date, float, float | None]]:
    """Yahoo Finance chart API. 미국 티커, 지수(^KS11), 국내 대체 심볼(005930.KS) 모두 된다."""
    r = httpx.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
                  params={"range": f"{years}y", "interval": "1d"}, headers=BROWSER, timeout=20)
    r.raise_for_status()
    result = r.json()["chart"].get("result")
    if not result:
        return []
    res = result[0]
    quote = res["indicators"]["quote"][0]
    closes = quote["close"]
    vols = quote.get("volume") or [None] * len(closes)
    return [(datetime.utcfromtimestamp(ts).date(), float(c), float(v) if v else None)
            for ts, c, v in zip(res["timestamp"], closes, vols) if c is not None]


def datagokr_krx_daily(item_name: str, begin: date, end: date) -> list[tuple[date, float, float | None]]:
    """공공데이터포털 「금융위원회_주식시세정보」. DATA_GO_KR_KEY 필요. 종목명으로 조회."""
    key = env("DATA_GO_KR_KEY")
    if not key:
        return []
    url = "https://apis.data.go.kr/1160100/GetStockSecuritiesInfoService_V2/getStockPriceInfo_V2"
    params = {"serviceKey": key, "resultType": "json", "numOfRows": 400, "pageNo": 1, "itmsNm": item_name,
              "beginBasDt": begin.strftime("%Y%m%d"), "endBasDt": end.strftime("%Y%m%d")}
    r = httpx.get(url, params=params, headers=UA, timeout=20)
    if r.status_code >= 400:  # 키 미승인 등. URL(키 포함)을 예외 메시지에 싣지 않는다
        raise RuntimeError(f"data.go.kr HTTP {r.status_code}")
    items = r.json().get("response", {}).get("body", {}).get("items", {}).get("item", [])
    return [(datetime.strptime(i["basDt"], "%Y%m%d").date(), float(i["clpr"]), float(i.get("trqu") or 0) or None) for i in items]


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


# ── 관심(attention) 데이터: 공시 — "언급이 공시를 따라가는가" 에 답한다 (docs/data-plan.md D3) ──
def dart_disclosures(corp_code: str, begin: date, end: date, max_pages: int = 5) -> list[dict]:
    """DART 공시검색 `list.json`. 기간 안의 공시 전부(소급 가능). DART_KEY 필요. 출처: https://opendart.fss.or.kr (공시정보 › 공시검색)"""
    key = env("DART_KEY")
    if not key:
        return []
    out, page = [], 1
    while page <= max_pages:
        r = httpx.get("https://opendart.fss.or.kr/api/list.json", headers=UA, timeout=30,
                      params={"crtfc_key": key, "corp_code": corp_code, "bgn_de": begin.strftime("%Y%m%d"), "end_de": end.strftime("%Y%m%d"),
                              "page_no": page, "page_count": 100})
        r.raise_for_status()
        data = r.json()
        if data.get("status") not in ("000", "013"):  # 013 = 조회된 데이터 없음
            raise RuntimeError(f"DART {data.get('status')}: {data.get('message')}")
        for it in data.get("list", []):
            out.append({"rcept_no": it["rcept_no"], "rcept_dt": datetime.strptime(it["rcept_dt"], "%Y%m%d").date(),
                        "report_nm": it["report_nm"].strip(), "corp_cls": it.get("corp_cls", ""), "kind": classify_report(it["report_nm"])})
        if page >= int(data.get("total_page", 1) or 1):
            break
        page += 1
    return out


_REPORT_KINDS = [
    ("실적", ("사업보고서", "분기보고서", "반기보고서", "영업(잠정)실적", "영업실적", "매출액또는손익구조")),
    ("계약", ("단일판매", "공급계약",)),
    ("자금조달", ("유상증자", "전환사채", "신주인수권부사채", "교환사채", "무상증자")),
    ("주요사항", ("주요사항보고서", "타법인주식", "자기주식", "합병", "분할", "영업양수", "영업양도", "최대주주변경")),
    ("지분", ("주식등의대량보유", "임원ㆍ주요주주특정증권", "임원·주요주주")),
]


def classify_report(report_nm: str) -> str:
    """공시명 → 종류. 발표에서는 '실적·주요사항 공시 전후에 언급이 몰리나' 를 본다."""
    for kind, words in _REPORT_KINDS:
        if any(w in report_nm for w in words):
            return kind
    return "기타"
