"""market-data — "이 종목이 언제 얼마였나, 종목 사전은?" 에 답한다. 아무도 부르지 않는 최하층 서비스.
mentions 는 /v1/dictionary 로 사전을 받고, 새 종목이 언급되면 /v1/assets/{id}/track 으로 시세 수집을 켠다.
stats 는 /v1/prices 로 여러 종목의 시세를 한 번에 받는다."""
from datetime import date, datetime, timedelta

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

import collectors
from hs_common import InternalOnly, create_app
from models import Asset, Price, db
from seed import AMBIGUOUS_NAMES, seed_assets

app = create_app("market-data", "힌드사이트 market-data", "0.2.0",
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
    ambiguous: bool  # 단독 매칭 금지
    curated: bool  # 시드(팀 확인) 종목이면 True. 자동 수집 코인은 문맥 규칙이 붙는다


class PriceOut(BaseModel):
    asset_id: str
    trade_date: date
    close: float
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
    points: list[list]  # [["2026-01-02", 71000.0], ...] — 여러 종목을 한 번에 줄 때 가볍게


class BatchPrices(BaseModel):
    series: list[PriceSeries]
    missing: list[str]


class SyncResult(BaseModel):
    assets_added: int
    prices_upserted: int
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
                       "ambiguous": a.name in AMBIGUOUS_NAMES, "curated": bool(a.curated)} for a in rows],
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
        by[p.asset_id].append([str(p.trade_date), p.close])
        cur[p.asset_id] = p.currency
    return {"series": [{"asset_id": i, "currency": cur.get(i, ""), "points": pts} for i, pts in by.items() if pts],
            "missing": [i for i, pts in by.items() if not pts]}


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
            skipped.append(f"{asset.asset_id}: {e}")
            continue
        upserted += _upsert_prices(s, asset, rows)
    s.commit()
    return {"assets_added": added, "prices_upserted": upserted, "skipped": skipped[:50]}


def _fetch_prices(asset: Asset, since: date, days: int):
    years = max(1, days // 365 + 1)
    if asset.source == "upbit":
        return collectors.upbit_daily(asset.symbol, days=days)
    if asset.source == "yahoo":
        return [r for r in collectors.yahoo_daily(asset.symbol, years) if r[0] >= since]
    if asset.source == "datagokr":
        rows = collectors.datagokr_krx_daily(asset.name, since, date.today())
        if rows:
            return rows
        if asset.yahoo_symbol:  # 키가 없거나 결과가 없으면 Yahoo 국내 심볼로 대체
            return [r for r in collectors.yahoo_daily(asset.yahoo_symbol, years) if r[0] >= since]
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
                        benchmark_id="INDEX:KOSPI", tracked=False))
            existing.add(aid); added += 1
    except Exception as e:
        skipped.append(f"dart: {e}")
    s.flush()
    return added


def _upsert_prices(s: Session, asset: Asset, rows) -> int:
    existing = {d for (d,) in s.execute(select(Price.trade_date).where(Price.asset_id == asset.asset_id)).all()}
    n = 0
    for d, close in rows:
        if d in existing:
            continue
        s.add(Price(asset_id=asset.asset_id, trade_date=d, close=close, currency=asset.currency))
        existing.add(d); n += 1
    return n
