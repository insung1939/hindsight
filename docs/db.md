# DB 테이블 문서

Supabase(PostgreSQL) 프로젝트 하나에 **서비스마다 스키마 하나**. 각 서비스는 자기 스키마만 권한이 있는 계정으로 접속한다(서비스 간 강결합 방지). 로컬은 SQLite 파일(스키마 없음). 테이블은 서비스 시작 시 `create_all` 로 만든다(4주차에 마이그레이션 도구로 교체 검토).

서비스 간에는 **외래키를 걸지 않는다.** 다른 서비스의 id(예: `asset_id`, `portfolio_id`)는 문자열·정수로만 보관하고 REST 로 조회한다.

## market (market-data)

| 테이블 | 컬럼 | 키 |
|---|---|---|
| `assets` | asset_id(`시장:심볼`), market, symbol, name, currency, asset_type, expense_ratio, source | PK asset_id |
| `prices` | id, asset_id, trade_date, close, currency, collected_at | PK id · UQ(asset_id, trade_date) |
| `fx_rates` | id, base, quote, rate_date, rate, source | PK id · UQ(base, quote, rate_date) |

`prices` 는 "현재가"가 아니라 **일별 이력**이다. backtest 가 이걸 쓴다.

## income

| 테이블 | 컬럼 | 키 |
|---|---|---|
| `distributions` | id, asset_id, ex_date, pay_date, amount_per_unit, currency, kind(cash·stock), source | PK id · UQ(asset_id, ex_date) |

## portfolio

| 테이블 | 컬럼 | 키 |
|---|---|---|
| `portfolios` | id, owner, name, base_currency, monthly_budget, buy_day, created_at | PK id |
| `accounts` | id, portfolio_id, name, account_type(general·isa·pension·exchange), broker | PK id · FK portfolio_id |
| `holdings` | id, portfolio_id, account_id, asset_id, quantity, avg_cost | PK id · FK portfolio_id, account_id |
| `rules` | id, portfolio_id, account_id, asset_id, target_weight | PK id · FK portfolio_id, account_id |
| `executions` | id, portfolio_id, instruction_id, asset_id, executed_on, status(done·skipped·extra·sell), amount_krw, quantity, note | PK id · FK portfolio_id |

`executions.instruction_id` 는 plan 서비스의 지시서 id (FK 없음).

## plan

| 테이블 | 컬럼 | 키 |
|---|---|---|
| `instructions` | id, portfolio_id, month(YYYY-MM), budget_krw, total_value_krw, created_at | PK id |
| `instruction_items` | id, instruction_id, asset_id, account_id, target_weight, current_weight, amount_krw, price, currency, fx_rate, quantity | PK id · FK instruction_id |

## backtest

| 테이블 | 컬럼 | 키 |
|---|---|---|
| `runs` | id, kind(dca·purchase-day), params(JSON), result(JSON), created_at | PK id |

## 관계 요약

```
market.assets 1 ─ n market.prices
market.assets 1 ─ n income.distributions        (asset_id 문자열, FK 없음)
portfolio.portfolios 1 ─ n accounts / holdings / rules / executions
plan.instructions 1 ─ n plan.instruction_items
plan.instructions 1 ─ n portfolio.executions    (instruction_id, FK 없음)
```
