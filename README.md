# 루틴 — 다자산 적립식 투자자의 운영 시스템

KAIST 디지털금융MBA 〈클라우드컴퓨팅실습〉 팀 프로젝트. 여러 자산(비트코인 · 미국 지수 ETF · 커버드콜 ETF · 국내 주식 · 항셍테크)에 여러 계좌로 적립하는 사람에게 **매달 "무엇을 얼마 사라"는 지시서를 만들어 주고, 실행을 기록하고, 규칙을 지켰는지와 그 결과를 보여준다.**

전체 기획·일정·역할은 [PLAN.md](PLAN.md), API 설명은 [docs/api.md](docs/api.md), 테이블은 [docs/db.md](docs/db.md), 데이터 출처는 [docs/data-sources.md](docs/data-sources.md).

## 구조 — 서비스 5개 (데이터 소유권 기준)

| 서비스 | 담당 질문 | 호출하는 서비스 | 로컬 포트 |
|---|---|---|---|
| `market-data` | 이 자산이 지금·과거에 얼마였나, 환율은 | — | 8001 |
| `income` | 이 자산이 언제 얼마를 분배했나 | market-data | 8002 |
| `portfolio` | 내가 뭘 얼마나 갖고 있고 뭘 실행했나 | market-data | 8003 |
| `plan` | 이번 달 뭘 얼마 사야 하나 | portfolio, market-data | 8004 |
| `backtest` | 이 규칙으로 과거에 했으면, 매수일이 중요한가 | market-data, income, portfolio | 8005 |

```
            apps/web (Vercel)
                 │  plan · portfolio · backtest · income 호출 ('데이터' 페이지만 market-data 읽기)
     ┌───────────┼──────────────┬──────────────┐
     ▼           ▼              ▼              ▼
   plan      portfolio       backtest        income
     │  ╲        │           ╱   │   ╲          │
     ▼    ╲      ▼         ╱     ▼     ╲        ▼
 portfolio ╲ market-data ◀┘   income    ╲▶ market-data
            ╲▶ market-data
```

- 각 서비스는 자기 테이블(Supabase 스키마 하나)만 읽고 쓴다. 남의 데이터는 REST 로만 본다. 순환 호출 없음.
- 수집기는 별도 서비스가 아니라 장부 주인 안에 있다 (`/internal/sync`).
- 통신은 동기 REST/JSON. `X-Request-ID` 를 전파하고 오류는 RFC 9457 `application/problem+json`.

```
routine/
├── contracts/          OpenAPI 3.1 명세 5개 — 단일 진실 공급원. .spectral.yaml 이 스타일 규칙
├── libs/routine-common 앱 골격 · 오류 포맷 · 요청 ID · DB · 서비스 간 클라이언트
├── services/<svc>/     FastAPI + SQLAlchemy, Dockerfile, tests/(계약 드리프트 검사)
├── apps/web/           React (Vite) — 화면 5개 (이번 달·자산·타임머신·신화 검증·데이터)
├── platform/           compose(서비스+게이트웨이+관측) · gateway(APISIX) · k8s(kustomize) · backstage(카탈로그)
├── docs/               api.md · db.md · data-sources.md (발표 필수) · seminar-demo.md (세미나 런북)
├── scripts/            dev_up/down · smoke.py · export_contracts.py · gen_api_docs.py
└── .github/workflows/  contracts(Spectral·oasdiff) · services(pytest·이미지) · sync(수집 스케줄)
```

## 로컬 실행 (5분)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e libs/routine-common "fastapi[standard]" sqlalchemy httpx pyyaml pytest
./scripts/dev_up.sh            # 5개 서비스 → http://127.0.0.1:800{1..5}/docs
python scripts/smoke.py        # 시세 수집 → 포트폴리오 → 지시서 → 타임머신까지 한 바퀴
./scripts/dev_down.sh
```

키 없이도 돈다(업비트 · Yahoo). 국내 시세는 `DATA_GO_KR_KEY`, 공식 환율은 `KOREAEXIM_KEY`, 배당 공시는 `DART_KEY` 를 `.env` 에 넣으면 붙는다. 키는 저장소·프롬프트에 넣지 않는다.

프론트: `cd apps/web && npm install && npm run dev` → http://localhost:5173 (이번 달 · 자산 현황 · 타임머신 · 신화 검증 · 데이터).

Docker 로 한 번에: `make compose` (서비스 5개) · `make compose-all` (+ APISIX 게이트웨이 9080, Grafana 3000, Prometheus 9090, Tempo 3200). 명령 목록은 `make help`.

세미나 데모 순서와 명령은 [docs/seminar-demo.md](docs/seminar-demo.md).

## 개발 규칙 (팀원 전원) — API-First

1. **명세 먼저.** `contracts/<service>.yaml` 에 엔드포인트를 쓰고, 호출하는 쪽 팀원이 리뷰한다.
2. **PR 은 CI 를 통과해야 한다.** Spectral(스타일) · oasdiff(하위 호환) · pytest(구현이 명세와 같은지).
3. **그다음 구현.** `python scripts/export_contracts.py <service>` 로 명세를 갱신하면 그 diff 가 리뷰 대상.
4. **상대 서비스가 없어도 개발한다.** `npx @stoplight/prism-cli mock contracts/market-data.yaml` 로 Mock 서버.

스타일: 경로 `/v1/` kebab-case · 필드 snake_case · 목록은 `items`+`next_cursor` · 오류는 problem+json · 바뀌는 값은 환경변수.

## 배포

| 계층 | 팀 운영 (수업 제출) | 세미나 실험실 |
|---|---|---|
| 프론트 | Vercel (`apps/web`) | 동일 |
| 백엔드 | Render ×5 — [render.yaml](render.yaml) Blueprint | kind → EC2 k3s (`platform/k8s`) + APISIX |
| DB | Supabase (스키마 5개) | 동일 |
| 관측 | OTel → Grafana Cloud | OTel → Prometheus · Tempo · Grafana |
| 수집 | GitHub Actions `sync.yml` | k8s CronJob |

환경변수: `DATABASE_URL`, `ALLOWED_ORIGINS`, `INTERNAL_TOKEN`, `<SERVICE>_URL`(서비스 간 주소), 출처 키 3종.

## 데이터 출처

| 데이터 | 출처 | 키 |
|---|---|---|
| 국내 주식·ETF 시세 | 공공데이터포털 「금융위원회_주식시세정보」 | 필요 |
| 미국 ETF 시세 · 환율 이력 | Yahoo Finance chart API | 불필요 |
| 비트코인 | 업비트 Open API | 불필요 |
| 공식 고시환율 | 한국수출입은행 환율 Open API | 필요 |
| 배당 결정 | DART OpenAPI | 필요 |
| ETF 분배금 | 운용사 페이지 크롤링 (5주차) | — |

## AI 활용

구조와 코드는 Claude Code 와 함께 작성했고, 생성된 코드는 로컬에서 실행해 `scripts/smoke.py` 와 Swagger 로 확인한 뒤 반영했다.
