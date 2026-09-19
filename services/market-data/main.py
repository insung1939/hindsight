"""market-data — "이 자산이 지금·과거에 얼마였나, 환율은?" 에 답한다. 아무도 부르지 않는 최하층 서비스."""
from datetime import date, timedelta

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

import collectors
from models import Asset, FxRate, Price, db
from routine_common import InternalOnly, create_app
from seed import SEED_ASSETS

app = create_app("market-data", "루틴 market-data", "0.1.0",
                 "자산 마스터 · 일별 시세 · 환율. 자산군별 수집 어댑터(공공데이터포털·Stooq·업비트·수출입은행)를 가진다.")


@app.on_event("startup")
def _startup():
    db.create_all()
    with db.SessionLocal() as s:
        if s.scalar(select(Asset).limit(1)) is None:
            s.add_all(Asset(**a) for a in SEED_ASSETS)
            s.commit()


# ── 스키마 ──────────────────────────────────────────────
class AssetOut(BaseModel):
    asset_id: str
    market: str
    symbol: str
    name: str
    currency: str
    asset_type: str
    expense_ratio: float | None = None
    model_config = {"from_attributes": True}


class PriceOut(BaseModel):
    asset_id: str
    trade_date: date
    close: float
    currency: str
    model_config = {"from_attributes": True}


class FxOut(BaseModel):
    base: str
    quote: str
    rate_date: date
    rate: float
    model_config = {"from_attributes": True}


class ListAssets(BaseModel):
    items: list[AssetOut]
    next_cursor: str | None = None


class ListPrices(BaseModel):
    items: list[PriceOut]
    next_cursor: str | None = None


class ListFx(BaseModel):
    items: list[FxOut]
    next_cursor: str | None = None


class SyncResult(BaseModel):
    prices_upserted: int
    fx_upserted: int
    skipped: list[str]


# ── 엔드포인트 ──────────────────────────────────────────
@app.get("/v1/assets", response_model=ListAssets, tags=["assets"], operation_id="list_assets", summary="자산 목록")
def list_assets(market: str | None = None, asset_type: str | None = None, s: Session = Depends(db.session)):
    q = select(Asset)
    if market:
        q = q.where(Asset.market == market)
    if asset_type:
        q = q.where(Asset.asset_type == asset_type)
    return {"items": s.scalars(q.order_by(Asset.asset_id)).all(), "next_cursor": None}


@app.get("/v1/assets/{asset_id}", response_model=AssetOut, tags=["assets"], operation_id="get_asset", summary="자산 하나")
def get_asset(asset_id: str, s: Session = Depends(db.session)):
    a = s.get(Asset, asset_id)
    if not a:
        raise HTTPException(404, f"자산 {asset_id} 없음")
    return a


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
    rows = s.scalars(q.order_by(Price.trade_date).limit(limit)).all()
    return {"items": rows, "next_cursor": None}


@app.get("/v1/assets/{asset_id}/prices/latest", response_model=PriceOut, tags=["prices"], operation_id="latest_price",
         summary="가장 최근 종가")
def latest_price(asset_id: str, s: Session = Depends(db.session)):
    row = s.scalar(select(Price).where(Price.asset_id == asset_id).order_by(Price.trade_date.desc()).limit(1))
    if not row:
        raise HTTPException(404, f"자산 {asset_id} 의 시세가 아직 없음. /internal/sync 를 먼저 실행")
    return row


@app.get("/v1/fx-rates", response_model=ListFx, tags=["fx"], operation_id="list_fx_rates", summary="환율 이력")
def list_fx_rates(base: str = "USD", quote: str = "KRW", from_date: date | None = Query(default=None, alias="from"),
                  to_date: date | None = Query(default=None, alias="to"), s: Session = Depends(db.session)):
    q = select(FxRate).where(FxRate.base == base, FxRate.quote == quote)
    if from_date:
        q = q.where(FxRate.rate_date >= from_date)
    if to_date:
        q = q.where(FxRate.rate_date <= to_date)
    return {"items": s.scalars(q.order_by(FxRate.rate_date)).all(), "next_cursor": None}


@app.get("/v1/fx-rates/latest", response_model=FxOut, tags=["fx"], operation_id="latest_fx_rate", summary="최근 환율")
def latest_fx_rate(base: str = "USD", quote: str = "KRW", s: Session = Depends(db.session)):
    if base == quote:
        return {"base": base, "quote": quote, "rate_date": date.today(), "rate": 1.0}
    row = s.scalar(select(FxRate).where(FxRate.base == base, FxRate.quote == quote)
                   .order_by(FxRate.rate_date.desc()).limit(1))
    if not row:
        raise HTTPException(404, f"{base}/{quote} 환율이 아직 없음. KOREAEXIM_KEY 설정 후 /internal/sync")
    return row


@app.post("/internal/sync", response_model=SyncResult, tags=["ops"], operation_id="sync_market_data",
          summary="시세·환율 수집 (스케줄러가 호출)", dependencies=[InternalOnly])
def sync(days: int = Query(default=200, le=5000), s: Session = Depends(db.session)):
    upserted, skipped = 0, []
    since = date.today() - timedelta(days=days)
    for asset in s.scalars(select(Asset)).all():
        try:
            if asset.source == "upbit":
                rows = collectors.upbit_daily(asset.symbol, days=days)
            elif asset.source == "yahoo":
                rows = [r for r in collectors.yahoo_daily(asset.symbol, years=max(1, days // 365 + 1)) if r[0] >= since]
            elif asset.source == "datagokr":
                rows = collectors.datagokr_krx_daily(asset.name, since, date.today())
                if not rows:
                    skipped.append(f"{asset.asset_id}: DATA_GO_KR_KEY 없음 또는 결과 없음")
            else:
                rows = []
        except Exception as e:  # 한 출처가 죽어도 나머지는 수집한다
            skipped.append(f"{asset.asset_id}: {e}")
            continue
        upserted += _upsert_prices(s, asset, rows)
    fx_upserted = 0
    # 1) 수출입은행 고시환율 (공식, 키 필요, 하루 단위) — 최근 5영업일
    for day in collectors.recent_business_days(5):
        try:
            rates = collectors.koreaexim_fx(day)
        except Exception as e:
            skipped.append(f"fx {day}: {e}")
            continue
        if not rates:
            skipped.append("fx: KOREAEXIM_KEY 없음 (Yahoo 환율로 대체)")
            break
        for cur, rate in rates.items():
            if cur in ("USD", "HKD", "CNH", "JPY", "EUR"):
                fx_upserted += _upsert_fx(s, cur, day, rate, "koreaexim")
    # 2) Yahoo 환율 이력 (키 불필요) — 백테스트용 과거 구간을 채운다. 이미 있는 날짜는 건너뛴다.
    for cur in ("USD", "HKD"):
        try:
            rows = collectors.yahoo_daily(f"{cur}KRW=X", years=max(1, days // 365 + 1))
        except Exception as e:
            skipped.append(f"fx {cur} yahoo: {e}")
            continue
        for d, rate in rows:
            if d >= since:
                fx_upserted += _upsert_fx(s, cur, d, rate, "yahoo")
    s.commit()
    return {"prices_upserted": upserted, "fx_upserted": fx_upserted, "skipped": skipped}


def _upsert_prices(s: Session, asset: Asset, rows) -> int:
    existing = {d for (d,) in s.execute(select(Price.trade_date).where(Price.asset_id == asset.asset_id)).all()}
    n = 0
    for d, close in rows:
        if d in existing:
            continue
        s.add(Price(asset_id=asset.asset_id, trade_date=d, close=close, currency=asset.currency))
        n += 1
    return n


_fx_seen: set[tuple[str, date]] = set()


def _upsert_fx(s: Session, cur: str, day: date, rate: float, source: str) -> int:
    if (cur, day) in _fx_seen:
        return 0
    exists = s.scalar(select(FxRate).where(FxRate.base == cur, FxRate.quote == "KRW", FxRate.rate_date == day))
    _fx_seen.add((cur, day))
    if exists:
        return 0
    s.add(FxRate(base=cur, quote="KRW", rate_date=day, rate=rate, source=source))
    return 1
