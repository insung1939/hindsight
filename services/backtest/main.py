"""backtest — "이 규칙으로 과거에 했으면?", "매수일이 중요한가?" 에 답한다. market-data 에서 이력을 받아 계산한다.
income(분배금 재투자)·portfolio(규칙 위반 비용) 연동은 7주차."""
from datetime import date

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import engine
from models import Run, db
from routine_common import ServiceClient, create_app
from routine_common.settings import env

app = create_app("backtest", "루틴 backtest", "0.1.0", "적립식 타임머신과 신화 검증(매수일 타이밍 등).")
market = ServiceClient("market-data")


@app.on_event("startup")
def _startup():
    db.create_all()


class DcaIn(BaseModel):
    weights: dict[str, float] = Field(description="asset_id → 비중, 합이 1", examples=[{"US:SPY": 0.6, "CRYPTO:KRW-BTC": 0.4}])
    monthly_amount_krw: float = Field(gt=0)
    start: date
    end: date | None = None
    buy_day: int = Field(default=1, ge=1, le=28)


class RunOut(BaseModel):
    id: int
    kind: str
    params: dict
    result: dict
    model_config = {"from_attributes": True}


class PurchaseDayOut(BaseModel):
    asset_id: str
    start: date
    end: date
    monthly_amount_krw: float
    by_day: list[dict]
    best_day: int
    worst_day: int
    spread_pct: float
    conclusion: str


def _load(asset_ids: list[str], start: date, end: date):
    prices, currencies, fx = {}, {}, {}
    for a in asset_ids:
        rows = market.get(f"/v1/assets/{a}/prices", **{"from": str(start), "to": str(end), "limit": 5000})["items"]
        if not rows:
            raise HTTPException(409, f"{a}: 기간 내 시세 없음. market-data /internal/sync 먼저 실행")
        prices[a] = {date.fromisoformat(r["trade_date"]): r["close"] for r in rows}
        currencies[a] = rows[0]["currency"]
    for cur in set(currencies.values()) - {"KRW"}:
        rows = market.get("/v1/fx-rates", base=cur, quote="KRW", **{"from": str(start), "to": str(end)})["items"]
        fx[cur] = {date.fromisoformat(r["rate_date"]): r["rate"] for r in rows}
        if not rows:
            fx.setdefault("__fallback__", {})[cur] = float(env(f"FX_FALLBACK_{cur}KRW", "1350") or 1350)
    return prices, currencies, fx


@app.post("/v1/runs", response_model=RunOut, status_code=201, tags=["runs"], operation_id="create_run",
          summary="적립식 타임머신 (market-data 호출)")
def create_run(body: DcaIn, s: Session = Depends(db.session)):
    if abs(sum(body.weights.values()) - 1) > 0.001:
        raise HTTPException(422, "weights 합은 1이어야 합니다")
    end = body.end or date.today()
    prices, currencies, fx = _load(list(body.weights), body.start, end)
    result = engine.simulate_dca(body.weights, body.monthly_amount_krw, body.start, end, body.buy_day,
                                 prices, currencies, fx)
    run = Run(kind="dca", params=body.model_dump(mode="json"), result=result)
    s.add(run); s.commit(); s.refresh(run)
    return run


@app.get("/v1/runs/{run_id}", response_model=RunOut, tags=["runs"], operation_id="get_run", summary="실행 결과 하나")
def get_run(run_id: int, s: Session = Depends(db.session)):
    run = s.get(Run, run_id)
    if not run:
        raise HTTPException(404, f"실행 {run_id} 없음")
    return run


@app.get("/v1/analyses/purchase-day", response_model=PurchaseDayOut, tags=["analyses"],
         operation_id="analyze_purchase_day", summary="신화 검증 1 — 매수일이 결과를 바꾸는가")
def analyze_purchase_day(asset_id: str, start: date, end: date | None = None,
                         monthly_amount_krw: float = Query(default=100_000, gt=0)):
    end = end or date.today()
    prices, currencies, fx = _load([asset_id], start, end)
    by_day = []
    for d in (1, 5, 10, 15, 20, 25, 28):
        r = engine.simulate_dca({asset_id: 1.0}, monthly_amount_krw, start, end, d, prices, currencies, fx)
        by_day.append({"buy_day": d, "final_value_krw": r["final_value_krw"], "return_pct": r["return_pct"]})
    best = max(by_day, key=lambda x: x["return_pct"])
    worst = min(by_day, key=lambda x: x["return_pct"])
    spread = round(best["return_pct"] - worst["return_pct"], 2)
    conclusion = ("매수일에 따른 차이가 작습니다. 날짜를 고르느라 고민할 이유가 없습니다." if spread < 3
                  else "이 기간에는 매수일 차이가 눈에 띕니다. 표본 기간을 늘려 다시 확인하세요.")
    return {"asset_id": asset_id, "start": start, "end": end, "monthly_amount_krw": monthly_amount_krw,
            "by_day": by_day, "best_day": best["buy_day"], "worst_day": worst["buy_day"],
            "spread_pct": spread, "conclusion": conclusion}
