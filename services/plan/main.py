"""plan — "이번 달 뭘 얼마 사야 하나?" 에 답한다. portfolio(규칙·평가액)와 market-data(가격·환율)를 부른다.

알고리즘(프로토타입): 목표 비중 w_i, 현재 평가액 V_i, 총액 V, 이번 달 예산 B 일 때
  목표액_i = (V + B) · w_i,  부족분_i = max(0, 목표액_i − V_i),  매수액_i = B · 부족분_i / Σ부족분
부족분이 전혀 없으면(모두 목표 초과) 목표 비중대로 B 를 나눈다. 비중이 벌어진 자산에 더 사서 리밸런싱 효과를 낸다."""
from datetime import date, datetime

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Instruction, InstructionItem, db
from routine_common import ServiceClient, create_app

app = create_app("plan", "루틴 plan", "0.1.0", "월간 매수 지시서 생성. 목표 비중과 현재 비중 차이를 예산으로 메운다.")
portfolio = ServiceClient("portfolio")
market = ServiceClient("market-data")


@app.on_event("startup")
def _startup():
    db.create_all()


class InstructionIn(BaseModel):
    portfolio_id: int
    month: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$", description="기본값: 이번 달")
    budget_krw: float | None = Field(default=None, ge=0, description="기본값: 포트폴리오의 monthly_budget")


class ItemOut(BaseModel):
    asset_id: str
    account_id: int
    target_weight: float
    current_weight: float
    amount_krw: float
    price: float
    currency: str
    fx_rate: float
    quantity: float
    model_config = {"from_attributes": True}


class InstructionOut(BaseModel):
    id: int
    portfolio_id: int
    month: str
    budget_krw: float
    total_value_krw: float
    created_at: datetime
    items: list[ItemOut]
    model_config = {"from_attributes": True}


class ListOf(BaseModel):
    items: list[InstructionOut]
    next_cursor: str | None = None


def _out(s: Session, ins: Instruction) -> dict:
    items = s.scalars(select(InstructionItem).where(InstructionItem.instruction_id == ins.id)).all()
    return {**{c: getattr(ins, c) for c in ("id", "portfolio_id", "month", "budget_krw", "total_value_krw", "created_at")},
            "items": items}


@app.post("/v1/instructions", response_model=InstructionOut, status_code=201, tags=["instructions"],
          operation_id="create_instruction", summary="이번 달 매수 지시서 생성 (portfolio · market-data 호출)")
def create_instruction(body: InstructionIn, s: Session = Depends(db.session)):
    month = body.month or date.today().strftime("%Y-%m")
    pf = portfolio.get(f"/v1/portfolios/{body.portfolio_id}")
    budget = body.budget_krw if body.budget_krw is not None else pf["monthly_budget"]
    rules = portfolio.get(f"/v1/portfolios/{body.portfolio_id}/rules")["items"]
    if not rules:
        raise HTTPException(409, "적립 규칙이 없습니다. portfolio 에 규칙을 먼저 등록하세요")
    valuation = portfolio.get(f"/v1/portfolios/{body.portfolio_id}/valuation")
    total = valuation["total_value_krw"]
    current = {}
    for it in valuation["items"]:
        current[it["asset_id"]] = current.get(it["asset_id"], 0.0) + it["value_krw"]

    shortfalls = {r["asset_id"]: max(0.0, (total + budget) * r["target_weight"] - current.get(r["asset_id"], 0.0))
                  for r in rules}
    denom = sum(shortfalls.values())
    ins = Instruction(portfolio_id=body.portfolio_id, month=month, budget_krw=budget, total_value_krw=total)
    s.add(ins); s.flush()
    for r in rules:
        share = (shortfalls[r["asset_id"]] / denom) if denom else r["target_weight"]
        amount = budget * share
        price = market.get(f"/v1/assets/{r['asset_id']}/prices/latest")
        fx = 1.0 if price["currency"] == "KRW" else market.get("/v1/fx-rates/latest", base=price["currency"],
                                                                quote="KRW")["rate"]
        unit_krw = price["close"] * fx
        s.add(InstructionItem(instruction_id=ins.id, asset_id=r["asset_id"], account_id=r["account_id"],
                              target_weight=r["target_weight"],
                              current_weight=(current.get(r["asset_id"], 0.0) / total) if total else 0.0,
                              amount_krw=round(amount), price=price["close"], currency=price["currency"],
                              fx_rate=fx, quantity=round(amount / unit_krw, 6) if unit_krw else 0.0))
    s.commit(); s.refresh(ins)
    return _out(s, ins)


@app.get("/v1/instructions", response_model=ListOf, tags=["instructions"], operation_id="list_instructions",
         summary="지시서 목록")
def list_instructions(portfolio_id: int, month: str | None = None, s: Session = Depends(db.session)):
    q = select(Instruction).where(Instruction.portfolio_id == portfolio_id)
    if month:
        q = q.where(Instruction.month == month)
    rows = s.scalars(q.order_by(Instruction.created_at.desc())).all()
    return {"items": [_out(s, r) for r in rows], "next_cursor": None}


@app.get("/v1/instructions/{instruction_id}", response_model=InstructionOut, tags=["instructions"],
         operation_id="get_instruction", summary="지시서 하나")
def get_instruction(instruction_id: int, s: Session = Depends(db.session)):
    ins = s.get(Instruction, instruction_id)
    if not ins:
        raise HTTPException(404, f"지시서 {instruction_id} 없음")
    return _out(s, ins)
