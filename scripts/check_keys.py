"""키·접속 정보가 실제로 동작하는지 확인한다 (값은 출력하지 않는다).
    .venv/bin/python scripts/check_keys.py
읽는 곳: services/youtube/.env(YOUTUBE_API_KEY) · services/market-data/.env(DART_KEY, DATA_GO_KR_KEY) · 루트 .env(DATABASE_URL)"""
import sys
from datetime import date, timedelta
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def load(p: Path) -> dict:
    out = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1); out[k.strip()] = v.strip().strip('"').strip("'")
    return out


env = {**load(ROOT / ".env"), **load(ROOT / "services" / "market-data" / ".env"), **load(ROOT / "services" / "youtube" / ".env")}
ok_all = True


def report(name, ok, detail=""):
    global ok_all
    ok_all &= bool(ok)
    print(f"{'OK ' if ok else 'FAIL'}  {name:<16} {detail}")


# YouTube
k = env.get("YOUTUBE_API_KEY")
if not k:
    report("YOUTUBE_API_KEY", False, "services/youtube/.env 에 없음")
else:
    r = httpx.get("https://www.googleapis.com/youtube/v3/channels", params={"part": "id", "forHandle": "@3protv", "key": k}, timeout=20)
    report("YOUTUBE_API_KEY", r.status_code == 200, f"HTTP {r.status_code}" + ("" if r.status_code == 200 else " " + r.text[:120].replace(k, "***")))

# DART
k = env.get("DART_KEY")
if not k:
    report("DART_KEY", False, "services/market-data/.env 에 없음")
else:
    r = httpx.get("https://opendart.fss.or.kr/api/list.json", params={"crtfc_key": k, "corp_code": "00126380", "bgn_de": (date.today() - timedelta(days=30)).strftime("%Y%m%d"),
                                                                     "end_de": date.today().strftime("%Y%m%d"), "page_count": 3}, timeout=30)
    j = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    report("DART_KEY", j.get("status") in ("000", "013"), f"status={j.get('status')} {j.get('message','')} (삼성전자 최근 30일 공시 {len(j.get('list', []))}건 샘플)")

# 공공데이터포털 주식시세
k = env.get("DATA_GO_KR_KEY")
if not k:
    report("DATA_GO_KR_KEY", False, "services/market-data/.env 에 없음")
else:
    r = httpx.get("https://apis.data.go.kr/1160100/GetStockSecuritiesInfoService_V2/getStockPriceInfo_V2",
                  params={"serviceKey": k, "resultType": "json", "numOfRows": 3, "pageNo": 1, "itmsNm": "삼성전자",
                          "beginBasDt": (date.today() - timedelta(days=10)).strftime("%Y%m%d"), "endBasDt": date.today().strftime("%Y%m%d")}, timeout=30)
    try:
        body = r.json().get("response", {})
        hdr = body.get("header", {}); items = body.get("body", {}).get("items", {}).get("item", [])
        report("DATA_GO_KR_KEY", hdr.get("resultCode") == "00" and len(items) > 0, f"resultCode={hdr.get('resultCode')} {hdr.get('resultMsg','')} · 삼성전자 최근 {len(items)}행" +
               (f" (마지막 {items[0]['basDt']} 종가 {items[0]['clpr']} 거래량 {items[0].get('trqu')})" if items else " — 승인 직후엔 반영까지 1~2시간 걸릴 수 있음"))
    except Exception:
        report("DATA_GO_KR_KEY", False, f"HTTP {r.status_code} {r.text[:160]}")

# Supabase
url = env.get("DATABASE_URL")
if not url:
    report("DATABASE_URL", False, "루트 .env 에 없음")
elif not url.startswith("postgres"):
    report("DATABASE_URL", False, "postgresql:// 로 시작해야 함")
else:
    try:
        from sqlalchemy import create_engine, text
        sys.path.insert(0, str(ROOT / "libs" / "hs-common"))
        from hs_common.db import normalize_url
        with create_engine(normalize_url(url), pool_pre_ping=True, connect_args={"connect_timeout": 15}).connect() as c:
            ver = c.execute(text("select version()")).scalar()
            schemas = [r[0] for r in c.execute(text("select schema_name from information_schema.schemata where schema_name in ('market','yt','mentions','stats')"))]
        host = url.split("@")[-1].split("/")[0]
        report("DATABASE_URL", True, f"{host} · {ver.split(',')[0]} · 스키마 {schemas or '아직 없음(첫 기동 때 생성)'}")
    except Exception as e:
        report("DATABASE_URL", False, str(e).split("\n")[0][:200].replace(url, "***"))

sys.exit(0 if ok_all else 1)
