"""market-data — "이 종목이 언제 얼마였나, 종목 사전은?" 에 답한다. 아무도 부르지 않는 최하층 서비스.
mentions 는 /v1/dictionary 로 사전을 받고, 새 종목이 언급되면 /v1/assets/{id}/track 으로 시세 수집을 켠다.
stats 는 /v1/prices 로 여러 종목의 시세를 한 번에 받는다."""
from datetime import date, datetime, timedelta

import threading

from fastapi import BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import collectors
from hs_common import InternalOnly, create_app, memo_ttl
from models import Asset, Disclosure, NewsDaily, Price, db
from seed import AMBIGUOUS_NAMES, seed_assets

app = create_app("market-data", "하인드사이트 market-data", "0.2.0",
                 "종목 사전(국내·미국·코인·지수 + 별칭) · 일별 시세. 출처: DART corpCode, 공공데이터포털, Yahoo Finance, 업비트.")


@app.on_event("startup")
def _startup():
    db.create_all()
    with db.SessionLocal() as s:
        if s.scalar(select(Asset).limit(1)) is None:
            s.add_all(Asset(**a) for a in seed_assets())
            s.commit()


# ── 스키마 ──────────────────────────────────────────────
class AssetOut(BaseModel):
    asset_id: str
    market: str
    symbol: str
    name: str
    aliases: list[str]
    currency: str
    asset_type: str
    benchmark_id: str | None = None
    tracked: bool
    model_config = {"from_attributes": True}


class DictionaryEntry(BaseModel):
    asset_id: str
    name: str
    aliases: list[str]
    market: str
    asset_type: str = "stock"  # theme 이면 업종·테마(대표 ETF 로 수익률을 잰다)
    ambiguous: bool  # 단독 매칭 금지
    curated: bool  # 시드(팀 확인) 종목이면 True. 자동 수집 코인은 문맥 규칙이 붙는다


class PriceOut(BaseModel):
    asset_id: str
    trade_date: date
    close: float
    volume: float | None = None
    currency: str
    model_config = {"from_attributes": True}


class ListAssets(BaseModel):
    items: list[AssetOut]
    next_cursor: str | None = None


class ListDictionary(BaseModel):
    items: list[DictionaryEntry]
    next_cursor: str | None = None
    ambiguous_names: list[str]


class ListPrices(BaseModel):
    items: list[PriceOut]
    next_cursor: str | None = None


class PriceSeries(BaseModel):
    asset_id: str
    currency: str
    points: list[list]  # [["2026-01-02", 71000.0, 12345678.0], ...] — [일자, 종가, 거래량(없으면 null)]


class BatchPrices(BaseModel):
    series: list[PriceSeries]
    missing: list[str]


class SyncResult(BaseModel):
    assets_added: int
    prices_upserted: int
    skipped: list[str]


class DisclosureOut(BaseModel):
    rcept_no: str
    asset_id: str
    rcept_dt: date
    report_nm: str
    kind: str
    model_config = {"from_attributes": True}


class ListDisclosures(BaseModel):
    items: list[DisclosureOut]
    next_cursor: str | None = None



class MarketCoverage(BaseModel):
    assets_by_market: dict[str, dict[str, int]]  # {KRX: {total, tracked, theme}, …}
    prices: int
    prices_with_volume: int
    last_trade_date: date | None
    disclosures: int
    disclosure_assets: int
    last_disclosure_date: date | None
    news_rows: int = 0
    news_assets: int = 0
    last_news_date: date | None = None


class NewsDailyOut(BaseModel):
    asset_id: str
    news_date: date
    count: int
    source: str
    model_config = {"from_attributes": True}


class ListNewsDaily(BaseModel):
    items: list[NewsDailyOut]
    next_cursor: str | None = None


class JobStatus(BaseModel):
    state: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    result: dict | None = None
    error: str | None = None


_job = {"state": "idle", "started_at": None, "finished_at": None, "result": None, "error": None}
_job_lock = threading.Lock()


class AttentionSyncResult(BaseModel):
    disclosures_added: int
    news_rows_upserted: int = 0
    assets_scanned: int
    skipped: list[str]


# ── 사전 · 자산 ─────────────────────────────────────────
@app.get("/v1/dictionary", response_model=ListDictionary, tags=["dictionary"], operation_id="get_dictionary",
         summary="종목 사전 전체 (이름·별칭 → asset_id). mentions 서비스가 매칭에 쓴다")
def get_dictionary(market: str | None = None, s: Session = Depends(db.session)):
    q = select(Asset).where(Asset.asset_type != "index")
    if market:
        q = q.where(Asset.market == market)
    rows = s.scalars(q).all()
    return {"items": [{"asset_id": a.asset_id, "name": a.name, "aliases": a.aliases or [], "market": a.market,
                       "asset_type": a.asset_type, "ambiguous": a.name in AMBIGUOUS_NAMES, "curated": bool(a.curated)} for a in rows],
            "next_cursor": None, "ambiguous_names": sorted(AMBIGUOUS_NAMES)}


@app.get("/v1/assets", response_model=ListAssets, tags=["assets"], operation_id="list_assets", summary="자산 목록")
def list_assets(market: str | None = None, tracked: bool | None = None, q: str | None = Query(default=None, description="이름·별칭 검색"),
                limit: int = Query(default=200, le=5000), s: Session = Depends(db.session)):
    stmt = select(Asset)
    if market:
        stmt = stmt.where(Asset.market == market)
    if tracked is not None:
        stmt = stmt.where(Asset.tracked == tracked)
    rows = s.scalars(stmt.order_by(Asset.asset_id)).all()
    if q:
        ql = q.lower()
        rows = [a for a in rows if ql in a.name.lower() or any(ql in al.lower() for al in (a.aliases or [])) or ql in a.symbol.lower()]
    return {"items": rows[:limit], "next_cursor": None}


class AssetName(BaseModel):
    asset_id: str
    name: str
    market: str
    symbol: str
    asset_type: str
    benchmark_id: str | None = None
    aliases: list[str] = []


class ListAssetNames(BaseModel):
    items: list[AssetName]
    next_cursor: str | None = None


@app.get("/v1/assets/names", response_model=ListAssetNames, tags=["assets"], operation_id="list_asset_names",
         summary="화면용 가벼운 사전 — 언급된 적 있는(tracked) 종목·테마·지수의 이름·별칭만")
def list_asset_names(all: bool = Query(default=False, description="true 면 사전 전체(4천여 개)"), s: Session = Depends(db.session)):
    q = select(Asset.asset_id, Asset.name, Asset.market, Asset.symbol, Asset.asset_type, Asset.benchmark_id, Asset.aliases)
    if not all:
        q = q.where(Asset.tracked == True)  # noqa: E712
    rows = s.execute(q.order_by(Asset.asset_id)).all()
    return {"items": [{"asset_id": a, "name": n, "market": m, "symbol": sym, "asset_type": t, "benchmark_id": b, "aliases": al or []} for a, n, m, sym, t, b, al in rows], "next_cursor": None}


@app.get("/v1/assets/{asset_id}", response_model=AssetOut, tags=["assets"], operation_id="get_asset", summary="자산 하나")
def get_asset(asset_id: str, s: Session = Depends(db.session)):
    a = s.get(Asset, asset_id)
    if not a:
        raise HTTPException(404, f"자산 {asset_id} 없음")
    return a


@app.post("/v1/assets/{asset_id}/track", response_model=AssetOut, tags=["assets"], operation_id="track_asset",
          summary="시세 수집 대상으로 켠다 (mentions 가 새 종목을 발견했을 때 호출)")
def track_asset(asset_id: str, s: Session = Depends(db.session)):
    a = s.get(Asset, asset_id)
    if not a:
        raise HTTPException(404, f"자산 {asset_id} 없음")
    if not a.tracked:
        a.tracked = True
        a.updated_at = datetime.utcnow()
        s.commit(); s.refresh(a)
    return a


# ── 시세 ────────────────────────────────────────────────
@app.get("/v1/assets/{asset_id}/prices", response_model=ListPrices, tags=["prices"], operation_id="list_prices",
         summary="일별 종가 이력")
def list_prices(asset_id: str, from_date: date | None = Query(default=None, alias="from"),
                to_date: date | None = Query(default=None, alias="to"), limit: int = Query(default=500, le=5000),
                s: Session = Depends(db.session)):
    if not s.get(Asset, asset_id):
        raise HTTPException(404, f"자산 {asset_id} 없음")
    q = select(Price).where(Price.asset_id == asset_id)
    if from_date:
        q = q.where(Price.trade_date >= from_date)
    if to_date:
        q = q.where(Price.trade_date <= to_date)
    return {"items": s.scalars(q.order_by(Price.trade_date).limit(limit)).all(), "next_cursor": None}


@app.get("/v1/prices", response_model=BatchPrices, tags=["prices"], operation_id="batch_prices",
         summary="여러 종목 시세를 한 번에 (stats 서비스용). asset_ids 는 쉼표 구분")
def batch_prices(asset_ids: str, from_date: date | None = Query(default=None, alias="from"),
                 to_date: date | None = Query(default=None, alias="to"), s: Session = Depends(db.session)):
    ids = [x.strip() for x in asset_ids.split(",") if x.strip()][:200]
    q = select(Price).where(Price.asset_id.in_(ids))
    if from_date:
        q = q.where(Price.trade_date >= from_date)
    if to_date:
        q = q.where(Price.trade_date <= to_date)
    by = {i: [] for i in ids}
    cur = {}
    for p in s.scalars(q.order_by(Price.trade_date)).all():
        by[p.asset_id].append([str(p.trade_date), p.close, p.volume])
        cur[p.asset_id] = p.currency
    return {"series": [{"asset_id": i, "currency": cur.get(i, ""), "points": pts} for i, pts in by.items() if pts],
            "missing": [i for i, pts in by.items() if not pts]}


# ── 관심 데이터: 공시 · 뉴스 ─────────────────────────────
@app.get("/v1/disclosures", response_model=ListDisclosures, tags=["attention"], operation_id="list_disclosures",
         summary="DART 공시 (asset_ids 쉼표 구분, 기간). stats 가 '언급 전후 공시 여부' 에, 타임라인이 표시에 쓴다")
def list_disclosures(asset_ids: str, from_date: date | None = Query(default=None, alias="from"),
                     to_date: date | None = Query(default=None, alias="to"), kind: str | None = None,
                     limit: int = Query(default=2000, le=20000), s: Session = Depends(db.session)):
    ids = [x.strip() for x in asset_ids.split(",") if x.strip()][:500]
    q = select(Disclosure).where(Disclosure.asset_id.in_(ids))
    if from_date:
        q = q.where(Disclosure.rcept_dt >= from_date)
    if to_date:
        q = q.where(Disclosure.rcept_dt <= to_date)
    if kind:
        q = q.where(Disclosure.kind == kind)
    return {"items": s.scalars(q.order_by(Disclosure.rcept_dt).limit(limit)).all(), "next_cursor": None}



@app.get("/v1/coverage", response_model=MarketCoverage, tags=["ops"], operation_id="get_market_coverage",
         summary="수집 현황 (데이터 페이지용): 사전·시세·거래량·공시·뉴스 건수")
def market_coverage(s: Session = Depends(db.session)):
    return _market_coverage_cached()


@memo_ttl(300)
def _market_coverage_cached():
    with db.SessionLocal() as s:
        by: dict[str, dict[str, int]] = {}
        for market, asset_type, tracked, n in s.execute(select(Asset.market, Asset.asset_type, Asset.tracked, func.count()).group_by(Asset.market, Asset.asset_type, Asset.tracked)).all():
            d_ = by.setdefault(market, {"total": 0, "tracked": 0, "theme": 0})
            d_["total"] += n
            if tracked:
                d_["tracked"] += n
            if asset_type == "theme":
                d_["theme"] += n
        return {"assets_by_market": by,
                "prices": s.scalar(select(func.count()).select_from(Price)) or 0,
                "prices_with_volume": s.scalar(select(func.count()).select_from(Price).where(Price.volume.is_not(None))) or 0,
                "last_trade_date": s.scalar(select(func.max(Price.trade_date))),
                "disclosures": s.scalar(select(func.count()).select_from(Disclosure)) or 0,
                "disclosure_assets": s.scalar(select(func.count(func.distinct(Disclosure.asset_id)))) or 0,
                "last_disclosure_date": s.scalar(select(func.max(Disclosure.rcept_dt))),
                "news_rows": s.scalar(select(func.count()).select_from(NewsDaily)) or 0,
                "news_assets": s.scalar(select(func.count(func.distinct(NewsDaily.asset_id)))) or 0,
                "last_news_date": s.scalar(select(func.max(NewsDaily.news_date)))}


@app.get("/v1/news-daily", response_model=ListNewsDaily, tags=["attention"], operation_id="list_news_daily",
         summary="종목별 일별 뉴스 기사 수 (네이버 금융 크롤링). asset_ids 쉼표 구분, 기간")
def list_news_daily(asset_ids: str, from_date: date | None = Query(default=None, alias="from"),
                    to_date: date | None = Query(default=None, alias="to"), limit: int = Query(default=5000, le=50000), s: Session = Depends(db.session)):
    ids = [x.strip() for x in asset_ids.split(",") if x.strip()][:500]
    q = select(NewsDaily).where(NewsDaily.asset_id.in_(ids))
    if from_date:
        q = q.where(NewsDaily.news_date >= from_date)
    if to_date:
        q = q.where(NewsDaily.news_date <= to_date)
    return {"items": s.scalars(q.order_by(NewsDaily.news_date).limit(limit)).all(), "next_cursor": None}


@app.post("/internal/sync-attention", response_model=AttentionSyncResult, tags=["ops"], operation_id="sync_attention",
          summary="tracked 국내 종목의 DART 공시(days 소급) + 네이버 증권 뉴스 크롤링(news_days, 0 이면 건너뜀). background=true 면 즉시 응답, /internal/sync-attention-status 로 확인", dependencies=[InternalOnly])
def sync_attention(background_tasks: BackgroundTasks, days: int = Query(default=7, le=800), news_days: int = Query(default=7, le=30, description="뉴스 크롤링 소급 일수. 0 이면 안 함"),
                   news_limit: int = Query(default=100, le=2000, description="크롤링할 종목 수 상한(국내 추적 종목 순)"),
                   background: bool = Query(default=False, description="true 면 백그라운드 (Render 는 15분 넘는 요청을 끊는다)")):
    if background:
        with _job_lock:
            if _job["state"] == "running":
                return {"disclosures_added": 0, "news_rows_upserted": 0, "assets_scanned": 0, "skipped": ["이미 실행 중"]}
            _job.update({"state": "running", "started_at": datetime.utcnow(), "finished_at": None, "result": None, "error": None})
        def run():
            try:
                with db.SessionLocal() as s2:
                    res = _sync_attention(s2, days, news_days, news_limit)
                _job.update({"state": "done", "finished_at": datetime.utcnow(), "result": res})
            except Exception as e:  # noqa: BLE001
                _job.update({"state": "failed", "finished_at": datetime.utcnow(), "error": str(e)[:300]})
        background_tasks.add_task(run)
        return {"disclosures_added": 0, "news_rows_upserted": 0, "assets_scanned": 0, "skipped": ["백그라운드 시작"]}
    with db.SessionLocal() as s:
        return _sync_attention(s, days, news_days, news_limit)


@app.get("/internal/sync-attention-status", response_model=JobStatus, tags=["ops"], operation_id="attention_sync_status",
         summary="비동기 공시·뉴스 수집 상태", dependencies=[InternalOnly])
def sync_attention_status():
    return _job


def _sync_attention(s: Session, days: int, news_days: int, news_limit: int) -> dict:
    skipped, d_added, n_upserted, scanned = [], 0, 0, 0
    tracked = s.scalars(select(Asset).where(Asset.tracked == True, Asset.asset_type.in_(["stock", "crypto"]))).all()  # noqa: E712
    # DART: corp_code 가 비어 있으면 corpCode 목록으로 채운다(월 1회면 충분하지만 가볍다)
    krx = [a for a in tracked if a.market == "KRX"]
    if krx and any(a.corp_code is None for a in krx):
        try:
            by_code = {c["stock_code"]: c["corp_code"] for c in collectors.dart_listed_companies()}
            for a in krx:
                if a.corp_code is None and a.symbol in by_code:
                    a.corp_code = by_code[a.symbol]
            s.flush()
        except Exception as e:
            skipped.append(f"dart corpCode: {e}")
    if not collectors.env("DART_KEY"):
        skipped.append("dart: DART_KEY 없음 — 공시 건너뜀")
    else:
        begin = date.today() - timedelta(days=days)
        existing = {r for (r,) in s.execute(select(Disclosure.rcept_no).where(Disclosure.rcept_dt >= begin)).all()}
        for a in krx:
            if not a.corp_code:
                continue
            try:
                for d_ in collectors.dart_disclosures(a.corp_code, begin, date.today()):
                    if d_["rcept_no"] in existing:
                        continue
                    s.add(Disclosure(asset_id=a.asset_id, **{k: d_[k] for k in ("rcept_no", "rcept_dt", "report_nm", "kind")}))
                    existing.add(d_["rcept_no"]); d_added += 1
                scanned += 1
            except Exception as e:
                skipped.append(f"dart {a.asset_id}: {e}")
    # 네이버 금융 뉴스 크롤링 — 국내 종목만, 최근 언급 많은 순으로 news_limit 개
    if news_days > 0:
        for a in krx[:news_limit]:
            try:
                counts = collectors.naver_finance_news(a.symbol, days=news_days)
            except Exception as e:
                skipped.append(f"news {a.asset_id}: {_safe(e)}"); continue
            for d_, n in counts.items():
                row = s.scalar(select(NewsDaily).where(NewsDaily.asset_id == a.asset_id, NewsDaily.news_date == d_))
                if row:
                    if n > row.count:
                        row.count = n; row.collected_at = datetime.utcnow()
                else:
                    s.add(NewsDaily(asset_id=a.asset_id, news_date=d_, count=n))
                n_upserted += 1
    s.commit()
    return {"disclosures_added": d_added, "news_rows_upserted": n_upserted, "assets_scanned": scanned, "skipped": skipped[:50]}


# ── 수집 ────────────────────────────────────────────────
@app.post("/internal/sync", response_model=SyncResult, tags=["ops"], operation_id="sync_market_data",
          summary="사전 갱신(DART·업비트) + tracked 종목 시세 수집", dependencies=[InternalOnly])
def sync(days: int = Query(default=400, le=5000), dictionary: bool = True, s: Session = Depends(db.session)):
    added, upserted, skipped = 0, 0, []
    if dictionary:
        added += _sync_dictionary(s, skipped)
    since = date.today() - timedelta(days=days)
    for asset in s.scalars(select(Asset).where(Asset.tracked == True)).all():  # noqa: E712
        try:
            rows = _fetch_prices(asset, since, days)
            if rows is None:
                skipped.append(f"{asset.asset_id}: 출처 없음")
                continue
        except Exception as e:
            skipped.append(f"{asset.asset_id}: {_safe(e)}")
            continue
        upserted += _upsert_prices(s, asset, rows)
    s.commit()
    memo_ttl.clear()
    return {"assets_added": added, "prices_upserted": upserted, "skipped": skipped[:50]}


def _safe(e: Exception) -> str:
    """오류 문자열에서 URL 쿼리(키가 들어 있을 수 있다)를 지운다."""
    import re
    return re.sub(r"\?[^'\s]*", "?…", str(e))[:200]


def _fetch_prices(asset: Asset, since: date, days: int):
    years = max(1, days // 365 + 1)
    if asset.source == "upbit":
        return collectors.upbit_daily(asset.symbol, days=days)
    if asset.source == "yahoo":
        return [r for r in collectors.yahoo_daily(asset.symbol, years) if r[0] >= since]
    if asset.source == "datagokr":
        try:
            rows = collectors.datagokr_krx_daily(asset.name, since, date.today())
        except Exception:  # 키 미승인(403)·장애 → 조용히 Yahoo 대체. 출처는 데이터 페이지에 Yahoo 로 표시된다
            rows = []
        if rows:
            return rows
        if asset.yahoo_symbol:  # 키가 없거나 결과가 없으면 Yahoo 국내 심볼로 대체. DART 는 거래소를 안 알려줘 .KS 가 비면 .KQ(코스닥)
            rows = [r for r in collectors.yahoo_daily(asset.yahoo_symbol, years) if r[0] >= since]
            if not rows and asset.yahoo_symbol.endswith(".KS"):
                rows = [r for r in collectors.yahoo_daily(asset.yahoo_symbol[:-3] + ".KQ", years) if r[0] >= since]
            return rows
        return None
    return None


def _sync_dictionary(s: Session, skipped: list[str]) -> int:
    added = 0
    existing = {a.asset_id for a in s.scalars(select(Asset.asset_id)).all()} if False else {r for (r,) in s.execute(select(Asset.asset_id)).all()}
    # 업비트 KRW 마켓 전부 (키 불필요)
    try:
        for m in collectors.upbit_markets():
            aid = f"CRYPTO:{m['market']}"
            if aid in existing:
                continue
            ticker = m["market"].split("-")[1]
            # 사전에만 넣는다(tracked=False). 언급되면 mentions 가 track 을 켠다 — 300개 마켓을 매일 긁지 않기 위해
            s.add(Asset(asset_id=aid, market="CRYPTO", symbol=m["market"], name=m["korean_name"], aliases=[ticker],
                        currency="KRW", asset_type="crypto", source="upbit", benchmark_id="CRYPTO:KRW-BTC", tracked=False))
            existing.add(aid); added += 1
    except Exception as e:
        skipped.append(f"upbit markets: {e}")
    # DART 상장사 전체 (키 필요). 사전에만 넣고 tracked=False — 언급되면 mentions 가 track 을 켠다.
    try:
        companies = collectors.dart_listed_companies()
        if not companies:
            skipped.append("dart: DART_KEY 없음 — 시드 종목만 사용")
        for c in companies:
            aid = f"KRX:{c['stock_code']}"
            if aid in existing:
                continue
            name = collectors.normalize_corp_name(c["corp_name"])
            s.add(Asset(asset_id=aid, market="KRX", symbol=c["stock_code"], name=name, aliases=[], currency="KRW",
                        asset_type="stock", source="datagokr", yahoo_symbol=f"{c['stock_code']}.KS",
                        benchmark_id="INDEX:KOSPI", tracked=False, corp_code=c.get("corp_code")))
            existing.add(aid); added += 1
    except Exception as e:
        skipped.append(f"dart: {e}")
    s.flush()
    return added


def _upsert_prices(s: Session, asset: Asset, rows) -> int:
    existing = {d for (d,) in s.execute(select(Price.trade_date).where(Price.asset_id == asset.asset_id)).all()}
    n = 0
    for d, close, *rest in rows:
        if d in existing:
            continue
        s.add(Price(asset_id=asset.asset_id, trade_date=d, close=close, volume=(rest[0] if rest else None), currency=asset.currency))
        existing.add(d); n += 1
    return n
