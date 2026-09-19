# API 설명 문서

`contracts/*.yaml`(OpenAPI 3.1)에서 자동 생성. 자세한 요청·응답 형식은 각 서비스의 `/docs`(Swagger UI) 또는 명세 파일을 본다.

공통 규약: 경로 `/v1/…` kebab-case · 필드 snake_case · 목록은 `items`+`next_cursor` · 오류는 RFC 9457 `application/problem+json` · 요청 헤더 `X-Request-ID` 전파.

## market-data

자산 마스터 · 일별 시세 · 환율. 자산군별 수집 어댑터(공공데이터포털·Stooq·업비트·수출입은행)를 가진다.

- 소유: `team-market-data` · 호출하는 서비스: —
- 서버: `http://localhost:8001`, `https://routine-market-data.onrender.com`

| Method | Path | 기능 | 파라미터 | 요청 본문 | 응답 |
|---|---|---|---|---|---|
| GET | `/healthz` | 서비스 상태 | — | — | 200 json |
| GET | `/v1/assets` | 자산 목록 | market, asset_type | — | 200 ListAssets |
| GET | `/v1/assets/{asset_id}` | 자산 하나 | asset_id | — | 200 AssetOut |
| GET | `/v1/assets/{asset_id}/prices` | 일별 종가 이력 | asset_id, from, to, limit | — | 200 ListPrices |
| GET | `/v1/assets/{asset_id}/prices/latest` | 가장 최근 종가 | asset_id | — | 200 PriceOut |
| GET | `/v1/fx-rates` | 환율 이력 | base, quote, from, to | — | 200 ListFx |
| GET | `/v1/fx-rates/latest` | 최근 환율 | base, quote | — | 200 FxOut |
| POST | `/internal/sync` | 시세·환율 수집 (스케줄러가 호출) | days, X-Internal-Token | — | 200 SyncResult |

## income

배당·분배금 이력과 월별 현금흐름 합산. 출처: DART OpenAPI, ETF 운용사 페이지(크롤링), 수동 입력.

- 소유: `team-income` · 호출하는 서비스: market-data
- 서버: `http://localhost:8002`, `https://routine-income.onrender.com`

| Method | Path | 기능 | 파라미터 | 요청 본문 | 응답 |
|---|---|---|---|---|---|
| GET | `/healthz` | 서비스 상태 | — | — | 200 json |
| GET | `/v1/distributions` | 배당·분배금 이력 | asset_id, from, to | — | 200 ListOf |
| POST | `/v1/distributions` | 분배 이벤트 수동 등록 (수집기가 못 잡은 것) | — | DistributionIn | 201 DistributionOut |
| POST | `/v1/cashflow` | 보유 수량 기준 연간 월별 분배금 (원화 환산, market-data 호출) | — | CashflowIn | 200 CashflowOut |
| POST | `/internal/sync` | 분배금 수집 (5~6주차에 DART·운용사 크롤러 연결) | X-Internal-Token | — | 200 SyncResult |

## portfolio

포트폴리오 · 계좌 · 보유 · 적립 규칙 · 실행 기록. 평가액과 규칙 준수 점수를 계산한다.

- 소유: `team-portfolio` · 호출하는 서비스: market-data
- 서버: `http://localhost:8003`, `https://routine-portfolio.onrender.com`

| Method | Path | 기능 | 파라미터 | 요청 본문 | 응답 |
|---|---|---|---|---|---|
| GET | `/healthz` | 서비스 상태 | — | — | 200 json |
| POST | `/v1/portfolios` | 포트폴리오 생성 | — | PortfolioIn | 201 PortfolioOut |
| GET | `/v1/portfolios` | 포트폴리오 목록 | owner | — | 200 ListOf |
| GET | `/v1/portfolios/{portfolio_id}` | 포트폴리오 하나 | portfolio_id | — | 200 PortfolioOut |
| POST | `/v1/portfolios/{portfolio_id}/accounts` | 계좌 추가 | portfolio_id | AccountIn | 201 AccountOut |
| GET | `/v1/portfolios/{portfolio_id}/accounts` | 계좌 목록 | portfolio_id | — | 200 ListOf |
| POST | `/v1/portfolios/{portfolio_id}/holdings` | 보유 종목 추가 | portfolio_id | HoldingIn | 201 HoldingOut |
| GET | `/v1/portfolios/{portfolio_id}/holdings` | 보유 목록 | portfolio_id | — | 200 ListOf |
| PATCH | `/v1/portfolios/{portfolio_id}/holdings/{holding_id}` | 보유 수량·평단 수정 | portfolio_id, holding_id | HoldingPatch | 200 HoldingOut |
| DELETE | `/v1/portfolios/{portfolio_id}/holdings/{holding_id}` | 보유 삭제 | portfolio_id, holding_id | — | 204 |
| POST | `/v1/portfolios/{portfolio_id}/rules` | 적립 규칙 추가 | portfolio_id | RuleIn | 201 RuleOut |
| GET | `/v1/portfolios/{portfolio_id}/rules` | 적립 규칙 목록 | portfolio_id | — | 200 ListOf |
| DELETE | `/v1/portfolios/{portfolio_id}/rules/{rule_id}` | 규칙 삭제 | portfolio_id, rule_id | — | 204 |
| POST | `/v1/portfolios/{portfolio_id}/executions` | 실행 기록 (지시대로/건너뜀/추가/매도) | portfolio_id | ExecutionIn | 201 ExecutionOut |
| GET | `/v1/portfolios/{portfolio_id}/executions` | 실행 기록 목록 | portfolio_id, from, to | — | 200 ListOf |
| GET | `/v1/portfolios/{portfolio_id}/valuation` | 원화 환산 평가액과 비중 (market-data 호출) | portfolio_id | — | 200 Valuation |
| GET | `/v1/portfolios/{portfolio_id}/compliance` | 규칙 준수 점수 | portfolio_id, months | — | 200 Compliance |

## plan

월간 매수 지시서 생성. 목표 비중과 현재 비중 차이를 예산으로 메운다.

- 소유: `team-plan` · 호출하는 서비스: portfolio, market-data
- 서버: `http://localhost:8004`, `https://routine-plan.onrender.com`

| Method | Path | 기능 | 파라미터 | 요청 본문 | 응답 |
|---|---|---|---|---|---|
| GET | `/healthz` | 서비스 상태 | — | — | 200 json |
| POST | `/v1/instructions` | 이번 달 매수 지시서 생성 (portfolio · market-data 호출) | — | InstructionIn | 201 InstructionOut |
| GET | `/v1/instructions` | 지시서 목록 | portfolio_id, month | — | 200 ListOf |
| GET | `/v1/instructions/{instruction_id}` | 지시서 하나 | instruction_id | — | 200 InstructionOut |

## backtest

적립식 타임머신과 신화 검증(매수일 타이밍 등).

- 소유: `team-backtest` · 호출하는 서비스: market-data, income, portfolio
- 서버: `http://localhost:8005`, `https://routine-backtest.onrender.com`

| Method | Path | 기능 | 파라미터 | 요청 본문 | 응답 |
|---|---|---|---|---|---|
| GET | `/healthz` | 서비스 상태 | — | — | 200 json |
| POST | `/v1/runs` | 적립식 타임머신 (market-data 호출) | — | DcaIn | 201 RunOut |
| GET | `/v1/runs/{run_id}` | 실행 결과 하나 | run_id | — | 200 RunOut |
| GET | `/v1/analyses/purchase-day` | 신화 검증 1 — 매수일이 결과를 바꾸는가 | asset_id, start, end, monthly_amount_krw | — | 200 PurchaseDayOut |
