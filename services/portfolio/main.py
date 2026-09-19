"""portfolio — "내가 뭘 얼마나 갖고 있고 뭘 실행했나?" 에 답한다. 평가액 계산 때만 market-data 를 부른다."""
from datetime import date, datetime, timedelta

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import Account, Execution, Holding, Portfolio, Rule, db
from routine_common import ServiceClient, create_app

app = create_app("portfolio", "루틴 portfolio", "0.1.0",
                 "포트폴리오 · 계좌 · 보유 · 적립 규칙 · 실행 기록. 평가액과 규칙 준수 점수를 계산한다.")
market = ServiceClient("market-data")


@app.on_event("startup")
def _startup():
    db.create_all()


# ── 스키마 ──────────────────────────────────────────────
class PortfolioIn(BaseModel):
    owner: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    base_currency: str = "KRW"
    monthly_budget: float = Field(ge=0, default=0)
    buy_day: int = Field(ge=1, le=28, default=1)


class PortfolioOut(PortfolioIn):
    id: int
    created_at: datetime
    model_config = {"from_attributes": True}


class AccountIn(BaseModel):
    name: str
    account_type: str = Field(pattern="^(general|isa|pension|exchange)$")
    broker: str | None = None


class AccountOut(AccountIn):
    id: int
    portfolio_id: int
    model_config = {"from_attributes": True}


class HoldingIn(BaseModel):
    account_id: int
    asset_id: str
    quantity: float = Field(ge=0)
    avg_cost: float | None = None


class HoldingPatch(BaseModel):
    quantity: float | None = Field(default=None, ge=0)
    avg_cost: float | None = None


class HoldingOut(HoldingIn):
    id: int
    portfolio_id: int
    model_config = {"from_attributes": True}


class RuleIn(BaseModel):
    account_id: int
    asset_id: str
    target_weight: float = Field(gt=0, le=1)


class RuleOut(RuleIn):
    id: int
    portfolio_id: int
    model_config = {"from_attributes": True}


class ExecutionIn(BaseModel):
    instruction_id: int | None = None
    asset_id: str
    executed_on: date
    status: str = Field(pattern="^(done|skipped|extra|sell)$")
    amount_krw: float = 0
    quantity: float = 0
    note: str | None = Field(default=None, max_length=200)


class ExecutionOut(ExecutionIn):
    id: int
    portfolio_id: int
    model_config = {"from_attributes": True}


class ValuationItem(BaseModel):
    holding_id: int
    account_id: int
    asset_id: str
    quantity: float
    price: float
    currency: str
    price_date: date
    fx_rate: float
    value_krw: float
    weight: float
    target_weight: float


class Valuation(BaseModel):
    portfolio_id: int
    as_of: date
    total_value_krw: float
    items: list[ValuationItem]
    warnings: list[str]


class Compliance(BaseModel):
    portfolio_id: int
    months: int
    done: int
    skipped: int
    extra: int
    sell: int
    score: float  # 0~100
    streak_months: int


class ListOf(BaseModel):
    items: list
    next_cursor: str | None = None


# ── 헬퍼 ────────────────────────────────────────────────
def _get_portfolio(pid: int, s: Session) -> Portfolio:
    p = s.get(Portfolio, pid)
    if not p:
        raise HTTPException(404, f"포트폴리오 {pid} 없음")
    return p


# ── 포트폴리오 ──────────────────────────────────────────
@app.post("/v1/portfolios", response_model=PortfolioOut, status_code=201, tags=["portfolios"],
          operation_id="create_portfolio", summary="포트폴리오 생성")
def create_portfolio(body: PortfolioIn, s: Session = Depends(db.session)):
    p = Portfolio(**body.model_dump())
    s.add(p); s.commit(); s.refresh(p)
    return p


@app.get("/v1/portfolios", response_model=ListOf, tags=["portfolios"], operation_id="list_portfolios",
         summary="포트폴리오 목록")
def list_portfolios(owner: str | None = None, s: Session = Depends(db.session)):
    q = select(Portfolio)
    if owner:
        q = q.where(Portfolio.owner == owner)
    return {"items": [PortfolioOut.model_validate(p) for p in s.scalars(q).all()]}


@app.get("/v1/portfolios/{portfolio_id}", response_model=PortfolioOut, tags=["portfolios"],
         operation_id="get_portfolio", summary="포트폴리오 하나")
def get_portfolio(portfolio_id: int, s: Session = Depends(db.session)):
    return _get_portfolio(portfolio_id, s)


# ── 계좌 ────────────────────────────────────────────────
@app.post("/v1/portfolios/{portfolio_id}/accounts", response_model=AccountOut, status_code=201, tags=["accounts"],
          operation_id="create_account", summary="계좌 추가")
def create_account(portfolio_id: int, body: AccountIn, s: Session = Depends(db.session)):
    _get_portfolio(portfolio_id, s)
    a = Account(portfolio_id=portfolio_id, **body.model_dump())
    s.add(a); s.commit(); s.refresh(a)
    return a


@app.get("/v1/portfolios/{portfolio_id}/accounts", response_model=ListOf, tags=["accounts"],
         operation_id="list_accounts", summary="계좌 목록")
def list_accounts(portfolio_id: int, s: Session = Depends(db.session)):
    _get_portfolio(portfolio_id, s)
    rows = s.scalars(select(Account).where(Account.portfolio_id == portfolio_id)).all()
    return {"items": [AccountOut.model_validate(r) for r in rows]}


# ── 보유 ────────────────────────────────────────────────
@app.post("/v1/portfolios/{portfolio_id}/holdings", response_model=HoldingOut, status_code=201, tags=["holdings"],
          operation_id="create_holding", summary="보유 종목 추가")
def create_holding(portfolio_id: int, body: HoldingIn, s: Session = Depends(db.session)):
    _get_portfolio(portfolio_id, s)
    if not s.get(Account, body.account_id):
        raise HTTPException(404, f"계좌 {body.account_id} 없음")
    h = Holding(portfolio_id=portfolio_id, **body.model_dump())
    s.add(h); s.commit(); s.refresh(h)
    return h


@app.get("/v1/portfolios/{portfolio_id}/holdings", response_model=ListOf, tags=["holdings"],
         operation_id="list_holdings", summary="보유 목록")
def list_holdings(portfolio_id: int, s: Session = Depends(db.session)):
    _get_portfolio(portfolio_id, s)
    rows = s.scalars(select(Holding).where(Holding.portfolio_id == portfolio_id)).all()
    return {"items": [HoldingOut.model_validate(r) for r in rows]}


@app.patch("/v1/portfolios/{portfolio_id}/holdings/{holding_id}", response_model=HoldingOut, tags=["holdings"],
           operation_id="update_holding", summary="보유 수량·평단 수정")
def update_holding(portfolio_id: int, holding_id: int, body: HoldingPatch, s: Session = Depends(db.session)):
    h = s.get(Holding, holding_id)
    if not h or h.portfolio_id != portfolio_id:
        raise HTTPException(404, f"보유 {holding_id} 없음")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(h, k, v)
    s.commit(); s.refresh(h)
    return h


@app.delete("/v1/portfolios/{portfolio_id}/holdings/{holding_id}", status_code=204, tags=["holdings"],
            operation_id="delete_holding", summary="보유 삭제")
def delete_holding(portfolio_id: int, holding_id: int, s: Session = Depends(db.session)):
    h = s.get(Holding, holding_id)
    if not h or h.portfolio_id != portfolio_id:
        raise HTTPException(404, f"보유 {holding_id} 없음")
    s.delete(h); s.commit()
    return None


# ── 규칙 ────────────────────────────────────────────────
@app.post("/v1/portfolios/{portfolio_id}/rules", response_model=RuleOut, status_code=201, tags=["rules"],
          operation_id="create_rule", summary="적립 규칙 추가")
def create_rule(portfolio_id: int, body: RuleIn, s: Session = Depends(db.session)):
    _get_portfolio(portfolio_id, s)
    total = s.scalar(select(func.coalesce(func.sum(Rule.target_weight), 0)).where(Rule.portfolio_id == portfolio_id))
    if total + body.target_weight > 1.0001:
        raise HTTPException(409, f"목표 비중 합이 1을 넘습니다 (현재 {total:.2f})")
    r = Rule(portfolio_id=portfolio_id, **body.model_dump())
    s.add(r); s.commit(); s.refresh(r)
    return r


@app.get("/v1/portfolios/{portfolio_id}/rules", response_model=ListOf, tags=["rules"], operation_id="list_rules",
         summary="적립 규칙 목록")
def list_rules(portfolio_id: int, s: Session = Depends(db.session)):
    _get_portfolio(portfolio_id, s)
    rows = s.scalars(select(Rule).where(Rule.portfolio_id == portfolio_id)).all()
    return {"items": [RuleOut.model_validate(r) for r in rows]}


@app.delete("/v1/portfolios/{portfolio_id}/rules/{rule_id}", status_code=204, tags=["rules"],
            operation_id="delete_rule", summary="규칙 삭제")
def delete_rule(portfolio_id: int, rule_id: int, s: Session = Depends(db.session)):
    r = s.get(Rule, rule_id)
    if not r or r.portfolio_id != portfolio_id:
        raise HTTPException(404, f"규칙 {rule_id} 없음")
    s.delete(r); s.commit()
    return None


# ── 실행 기록 ───────────────────────────────────────────
@app.post("/v1/portfolios/{portfolio_id}/executions", response_model=ExecutionOut, status_code=201,
          tags=["executions"], operation_id="create_execution", summary="실행 기록 (지시대로/건너뜀/추가/매도)")
def create_execution(portfolio_id: int, body: ExecutionIn, s: Session = Depends(db.session)):
    _get_portfolio(portfolio_id, s)
    e = Execution(portfolio_id=portfolio_id, **body.model_dump())
    s.add(e)
    # done/extra 는 보유 수량에 반영, sell 은 차감. 계좌는 규칙의 계좌를 따른다.
    if body.status in ("done", "extra", "sell") and body.quantity:
        rule = s.scalar(select(Rule).where(Rule.portfolio_id == portfolio_id, Rule.asset_id == body.asset_id))
        h = s.scalar(select(Holding).where(Holding.portfolio_id == portfolio_id, Holding.asset_id == body.asset_id))
        delta = -body.quantity if body.status == "sell" else body.quantity
        if h:
            h.quantity = max(0.0, h.quantity + delta)
        elif rule and delta > 0:
            s.add(Holding(portfolio_id=portfolio_id, account_id=rule.account_id, asset_id=body.asset_id,
                          quantity=delta))
    s.commit(); s.refresh(e)
    return e


@app.get("/v1/portfolios/{portfolio_id}/executions", response_model=ListOf, tags=["executions"],
         operation_id="list_executions", summary="실행 기록 목록")
def list_executions(portfolio_id: int, from_date: date | None = Query(default=None, alias="from"),
                    to_date: date | None = Query(default=None, alias="to"), s: Session = Depends(db.session)):
    _get_portfolio(portfolio_id, s)
    q = select(Execution).where(Execution.portfolio_id == portfolio_id)
    if from_date:
        q = q.where(Execution.executed_on >= from_date)
    if to_date:
        q = q.where(Execution.executed_on <= to_date)
    rows = s.scalars(q.order_by(Execution.executed_on.desc())).all()
    return {"items": [ExecutionOut.model_validate(r) for r in rows]}


# ── 평가 · 준수 ─────────────────────────────────────────
@app.get("/v1/portfolios/{portfolio_id}/valuation", response_model=Valuation, tags=["analysis"],
         operation_id="get_valuation", summary="원화 환산 평가액과 비중 (market-data 호출)")
def get_valuation(portfolio_id: int, s: Session = Depends(db.session)):
    _get_portfolio(portfolio_id, s)
    holdings = s.scalars(select(Holding).where(Holding.portfolio_id == portfolio_id)).all()
    targets = {r.asset_id: r.target_weight for r in s.scalars(select(Rule).where(Rule.portfolio_id == portfolio_id))}
    items, warnings, fx_cache = [], [], {}
    for h in holdings:
        try:
            price = market.get(f"/v1/assets/{h.asset_id}/prices/latest")
        except HTTPException as e:
            warnings.append(f"{h.asset_id}: {e.detail}")
            continue
        cur = price["currency"]
        if cur not in fx_cache:
            try:
                fx_cache[cur] = market.get("/v1/fx-rates/latest", base=cur, quote="KRW")["rate"]
            except HTTPException as e:
                warnings.append(f"{cur}/KRW 환율 없음, 1.0 으로 계산: {e.detail}")
                fx_cache[cur] = 1.0
        fx = fx_cache[cur]
        items.append(dict(holding_id=h.id, account_id=h.account_id, asset_id=h.asset_id, quantity=h.quantity,
                          price=price["close"], currency=cur, price_date=price["trade_date"], fx_rate=fx,
                          value_krw=h.quantity * price["close"] * fx, weight=0.0,
                          target_weight=targets.get(h.asset_id, 0.0)))
    total = sum(i["value_krw"] for i in items)
    for i in items:
        i["weight"] = (i["value_krw"] / total) if total else 0.0
    return {"portfolio_id": portfolio_id, "as_of": date.today(), "total_value_krw": total,
            "items": items, "warnings": warnings}


@app.get("/v1/portfolios/{portfolio_id}/compliance", response_model=Compliance, tags=["analysis"],
         operation_id="get_compliance", summary="규칙 준수 점수")
def get_compliance(portfolio_id: int, months: int = Query(default=12, ge=1, le=120), s: Session = Depends(db.session)):
    _get_portfolio(portfolio_id, s)
    since = date.today() - timedelta(days=31 * months)
    rows = s.scalars(select(Execution).where(Execution.portfolio_id == portfolio_id,
                                             Execution.executed_on >= since)).all()
    counts = {k: sum(1 for r in rows if r.status == k) for k in ("done", "skipped", "extra", "sell")}
    planned = counts["done"] + counts["skipped"]
    # 지시대로 실행한 비율에서 임의 매매(extra·sell)마다 5점씩 감점
    score = (counts["done"] / planned * 100 if planned else 0.0) - 5 * (counts["extra"] + counts["sell"])
    streak, seen = 0, set()
    for r in sorted(rows, key=lambda r: r.executed_on, reverse=True):
        key = (r.executed_on.year, r.executed_on.month)
        if r.status == "done" and key not in seen:
            seen.add(key); streak += 1
        elif r.status == "skipped":
            break
    return {"portfolio_id": portfolio_id, "months": months, **counts,
            "score": max(0.0, min(100.0, score)), "streak_months": streak}
