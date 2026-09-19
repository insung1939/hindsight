"""서비스 5개를 로컬(scripts/dev_up.sh)에 띄운 뒤 한 바퀴 돌려 보는 스모크 테스트 겸 데모 스크립트.

    python scripts/smoke.py            # 전체 흐름
    python scripts/smoke.py --no-sync  # 시세 수집 건너뜀 (이미 받아 둔 경우)

흐름: 시세 수집 → 포트폴리오·계좌·보유·규칙 → 평가(portfolio→market-data) → 지시서(plan→portfolio→market-data)
      → 실행 기록·준수 점수 → 타임머신(backtest→market-data) → 매수일 검증
"""
import sys

import httpx

BASE = {"market-data": "http://127.0.0.1:8001", "income": "http://127.0.0.1:8002", "portfolio": "http://127.0.0.1:8003",
        "plan": "http://127.0.0.1:8004", "backtest": "http://127.0.0.1:8005"}
c = httpx.Client(timeout=120)


def call(svc, method, path, **kw):
    r = c.request(method, BASE[svc] + path, **kw)
    if r.status_code >= 400:
        print(f"  !! {svc} {method} {path} -> {r.status_code} {r.text[:200]}")
        r.raise_for_status()
    return r.json() if r.content else None


def step(title):
    print(f"\n== {title}")


if "--no-sync" not in sys.argv:
    step("market-data 수집 (업비트·Yahoo — 키 없는 출처)")
    r = call("market-data", "POST", "/internal/sync", params={"days": 2000})
    print(f"  prices_upserted={r['prices_upserted']} skipped={len(r['skipped'])} (KRX·환율은 키 필요)")

step("portfolio 생성 · 계좌 · 보유 · 규칙")
pf = call("portfolio", "POST", "/v1/portfolios", json={"owner": "insung", "name": "인성 적립", "monthly_budget": 1_000_000, "buy_day": 5})
pid = pf["id"]
a_gen = call("portfolio", "POST", f"/v1/portfolios/{pid}/accounts", json={"name": "키움 일반", "account_type": "general", "broker": "키움"})["id"]
a_ex = call("portfolio", "POST", f"/v1/portfolios/{pid}/accounts", json={"name": "업비트", "account_type": "exchange", "broker": "업비트"})["id"]
call("portfolio", "POST", f"/v1/portfolios/{pid}/holdings", json={"account_id": a_gen, "asset_id": "US:SPY", "quantity": 10})
call("portfolio", "POST", f"/v1/portfolios/{pid}/holdings", json={"account_id": a_ex, "asset_id": "CRYPTO:KRW-BTC", "quantity": 0.05})
for asset, w, acc in (("US:SPY", 0.4, a_gen), ("US:QQQ", 0.3, a_gen), ("CRYPTO:KRW-BTC", 0.3, a_ex)):
    call("portfolio", "POST", f"/v1/portfolios/{pid}/rules", json={"account_id": acc, "asset_id": asset, "target_weight": w})
print(f"  portfolio_id={pid} accounts={a_gen},{a_ex} rules=3")

step("평가 (portfolio → market-data)")
r = c.get(BASE["portfolio"] + f"/v1/portfolios/{pid}/valuation", headers={"X-Request-ID": "smoke-valuation-1"})
v = r.json()
print(f"  X-Request-ID 응답 헤더: {r.headers.get('X-Request-ID')}")
print(f"  총 평가액 {v['total_value_krw']:,.0f}원 (경고 {len(v['warnings'])}건: {v['warnings'][:1]})")
for it in v["items"]:
    print(f"   - {it['asset_id']:16s} {it['quantity']:>8} × {it['price']:,.2f} {it['currency']} × fx {it['fx_rate']:,.1f} = {it['value_krw']:>14,.0f}원  비중 {it['weight']:.1%} / 목표 {it['target_weight']:.0%}")

step("이번 달 지시서 (plan → portfolio → market-data)")
ins = call("plan", "POST", "/v1/instructions", json={"portfolio_id": pid})
print(f"  instruction_id={ins['id']} month={ins['month']} 예산 {ins['budget_krw']:,.0f}원")
for it in ins["items"]:
    print(f"   - {it['asset_id']:16s} 현재 {it['current_weight']:.1%} → 목표 {it['target_weight']:.0%}: {it['amount_krw']:>10,.0f}원 ≈ {it['quantity']} 단위 @ {it['price']:,.2f} {it['currency']}")

step("실행 기록 · 준수 점수")
for it in ins["items"]:
    status = "skipped" if it["asset_id"] == "CRYPTO:KRW-BTC" else "done"
    call("portfolio", "POST", f"/v1/portfolios/{pid}/executions",
         json={"instruction_id": ins["id"], "asset_id": it["asset_id"], "executed_on": f"{ins['month']}-05",
               "status": status, "amount_krw": it["amount_krw"], "quantity": it["quantity"]})
comp = call("portfolio", "GET", f"/v1/portfolios/{pid}/compliance")
print(f"  done={comp['done']} skipped={comp['skipped']} score={comp['score']:.0f} streak={comp['streak_months']}")

step("타임머신 (backtest → market-data): 2021-04부터 월 100만원, SPY 40 / QQQ 30 / BTC 30")
run = call("backtest", "POST", "/v1/runs", json={"weights": {"US:SPY": 0.4, "US:QQQ": 0.3, "CRYPTO:KRW-BTC": 0.3},
                                                 "monthly_amount_krw": 1_000_000, "start": "2021-04-01", "buy_day": 5})
res = run["result"]
print(f"  투입 {res['invested_krw']:,}원 → 평가 {res['final_value_krw']:,}원  수익률 {res['return_pct']}%  최대낙폭 {res['max_drawdown_pct']}%  ({res['months']}개월)")
if res["warnings"]:
    print(f"  경고: {res['warnings'][0]}")

step("신화 검증 1 — 매수일이 중요한가 (SPY, 2021-04 ~)")
pd = call("backtest", "GET", "/v1/analyses/purchase-day", params={"asset_id": "US:SPY", "start": "2021-04-01"})
print("  " + "  ".join(f"{d['buy_day']}일:{d['return_pct']}%" for d in pd["by_day"]))
print(f"  최고 {pd['best_day']}일 / 최저 {pd['worst_day']}일, 차이 {pd['spread_pct']}%p → {pd['conclusion']}")

print("\n완료. 각 서비스 /docs 에서 같은 호출을 Swagger 로 확인할 수 있다.")
