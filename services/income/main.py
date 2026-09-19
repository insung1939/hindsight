"""income — "이 자산이 언제 얼마를 분배했나?" 에 답한다. 원화 환산 때만 market-data 를 부른다.
수집기(DART 배당 결정 · 운용사 분배금 크롤링)는 5~6주차에 collectors 로 붙인다."""
from datetime import date

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Distribution, db
from routine_common import InternalOnly, ServiceClient, create_app

app = create_app("income", "루틴 income", "0.1.0",
                 "배당·분배금 이력과 월별 현금흐름 합산. 출처: DART OpenAPI, ETF 운용사 페이지(크롤링), 수동 입력.")
market = ServiceClient("market-data")


@app.on_event("startup")
def _startup():
    db.create_all()


class DistributionIn(BaseModel):
    asset_id: str
    ex_date: date
    pay_date: date | None = None
    amount_per_unit: float = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    kind: str = Field(default="cash", pattern="^(cash|stock)$")
    source: str = "manual"


class DistributionOut(DistributionIn):
    id: int
    model_config = {"from_attributes": True}


class ListOf(BaseModel):
    items: list[DistributionOut]
    next_cursor: str | None = None


class HoldingRef(BaseModel):
    asset_id: str
    quantity: float = Field(ge=0)


class CashflowIn(BaseModel):
    holdings: list[HoldingRef]
    year: int = Field(ge=2000, le=2100)


class CashflowMonth(BaseModel):
    month: str  # YYYY-MM
    amount_krw: float
    items: list[dict]


class CashflowOut(BaseModel):
    year: int
    total_krw: float
    months: list[CashflowMonth]
    warnings: list[str]


class SyncResult(BaseModel):
    upserted: int
    skipped: list[str]


@app.get("/v1/distributions", response_model=ListOf, tags=["distributions"], operation_id="list_distributions",
         summary="배당·분배금 이력")
def list_distributions(asset_id: str | None = None, from_date: date | None = Query(default=None, alias="from"),
                       to_date: date | None = Query(default=None, alias="to"), s: Session = Depends(db.session)):
    q = select(Distribution)
    if asset_id:
        q = q.where(Distribution.asset_id == asset_id)
    if from_date:
        q = q.where(Distribution.ex_date >= from_date)
    if to_date:
        q = q.where(Distribution.ex_date <= to_date)
    return {"items": s.scalars(q.order_by(Distribution.ex_date.desc())).all(), "next_cursor": None}


@app.post("/v1/distributions", response_model=DistributionOut, status_code=201, tags=["distributions"],
          operation_id="create_distribution", summary="분배 이벤트 수동 등록 (수집기가 못 잡은 것)")
def create_distribution(body: DistributionIn, s: Session = Depends(db.session)):
    dup = s.scalar(select(Distribution).where(Distribution.asset_id == body.asset_id,
                                              Distribution.ex_date == body.ex_date))
    if dup:
        raise HTTPException(409, "같은 자산·배당락일 이벤트가 이미 있습니다")
    d = Distribution(**body.model_dump())
    s.add(d); s.commit(); s.refresh(d)
    return d


@app.post("/v1/cashflow", response_model=CashflowOut, tags=["cashflow"], operation_id="calc_cashflow",
          summary="보유 수량 기준 연간 월별 분배금 (원화 환산, market-data 호출)")
def calc_cashflow(body: CashflowIn, s: Session = Depends(db.session)):
    months = {f"{body.year}-{m:02d}": {"amount_krw": 0.0, "items": []} for m in range(1, 13)}
    warnings, fx_cache = [], {}
    for h in body.holdings:
        rows = s.scalars(select(Distribution).where(Distribution.asset_id == h.asset_id,
                                                    Distribution.ex_date >= date(body.year, 1, 1),
                                                    Distribution.ex_date <= date(body.year, 12, 31))).all()
        if not rows:
            warnings.append(f"{h.asset_id}: {body.year}년 분배 이력 없음")
        for d in rows:
            if d.currency not in fx_cache:
                try:
                    fx_cache[d.currency] = market.get("/v1/fx-rates/latest", base=d.currency, quote="KRW")["rate"]
                except HTTPException as e:
                    warnings.append(f"{d.currency}/KRW 환율 없음, 1.0 으로 계산: {e.detail}")
                    fx_cache[d.currency] = 1.0
            when = d.pay_date or d.ex_date
            key = f"{when.year}-{when.month:02d}"
            if key not in months:
                continue
            amount = h.quantity * d.amount_per_unit * fx_cache[d.currency]
            months[key]["amount_krw"] += amount
            months[key]["items"].append({"asset_id": d.asset_id, "pay_date": str(when),
                                         "amount_per_unit": d.amount_per_unit, "currency": d.currency,
                                         "amount_krw": round(amount)})
    out = [{"month": k, **v} for k, v in months.items()]
    return {"year": body.year, "total_krw": sum(m["amount_krw"] for m in out), "months": out, "warnings": warnings}


@app.post("/internal/sync", response_model=SyncResult, tags=["ops"], operation_id="sync_income",
          summary="분배금 수집 (5~6주차에 DART·운용사 크롤러 연결)", dependencies=[InternalOnly])
def sync():
    # TODO(5주차): 운용사 분배금 크롤러, TODO(6주차): DART 배당 결정 공시
    return {"upserted": 0, "skipped": ["수집기 미구현 — POST /v1/distributions 로 수동 입력"]}
