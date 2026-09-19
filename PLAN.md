# 루틴(가칭) — 다자산 적립식 투자자의 운영 시스템

KAIST 디지털금융MBA 〈클라우드컴퓨팅실습〉 팀 프로젝트 계획서 · 2026-09-19 작성

이 문서는 두 가지 목표를 동시에 만족하도록 짜였다.

1. **수업 제출물**: 8주차(10/21) 발표 — `퀴즈_및_팀프로젝트_안내.pdf`의 필수 항목 전부.
2. **사내 세미나**: "MSA 환경에서 REST API를 효율적으로 관리하는 방법" — 같은 코드로 Before/After 데모.

원칙 하나. **팀 진도가 우선이고, 관리 툴 레이어는 개인 트랙이다.** 팀원이 세미나 트랙에 의존하는 순간 팀 리스크가 되므로, 팀원에게 요구하는 건 "명세 먼저 쓰고 CI를 통과시킨다"까지로 제한한다.

---

## 1. 남은 일정

| 주차 | 날짜 | 수업 주제 | 팀 프로젝트 이벤트 |
|---|---|---|---|
| 4 | 9/23 (수) | 데이터베이스 (SQLite → PostgreSQL·Supabase) | 추석 직전, 휴강·보강 가능성 있음(OT 공지). 팀 확정·규약 합의 |
| 5 | 9/30 (수) | 웹 크롤링 | **팀 페이지 완성 · 아이디어 공유 발표 2~3분 · 기초 개념 퀴즈** |
| 6 | 10/7 (수) | 공공 Open API (법제처 등) | 수집기 완성, 데이터가 차기 시작 |
| 7 | 10/14 (수) | OpenSearch · AWS | 통합, 분석 페이지, 문서 |
| 8 | 10/21 (수) | 기말 발표 | **팀 발표** |

실질 개발 기간은 4주 반이다. 범위는 아래 "MVP"로 못 박고, 나머지는 "구상"으로 발표한다.

---

## 2. 서비스 정의

### 2.1 한 줄

여러 자산(비트코인 · 미국 지수 ETF · 커버드콜 ETF · 국내 주식 · 항셍테크 ETF)에 여러 계좌(일반 · ISA · 연금 · 거래소)로 적립하는 사람에게, **매달 "무엇을 얼마 사라"는 지시서를 만들어 주고, 실행을 기록하고, 규칙을 지켰는지와 그 결과를 보여주는** 서비스.

### 2.2 해결하는 문제 (기획 시나리오)

- 자산군·통화·계좌가 섞이면 매달 매수 금액 계산이 귀찮아서 대충 하게 된다.
- 장기 적립의 성패는 종목이 아니라 **규칙 준수**인데, 어떤 앱도 "규칙을 지켰는가"를 기록하지 않는다.
- 하락장에 계속 사려면 "내 규칙이 과거에 어땠는가"라는 확신이 필요하다.
- 커버드콜·배당 분배금이 통화별로 흩어져 월 현금흐름을 한눈에 모른다.

대상 사용자: 다자산 적립식 투자자. 사용자 1호는 팀원 본인들.

### 2.3 기능

| 구분 | 기능 | 설명 | 담당 서비스 |
|---|---|---|---|
| MVP | 자산·계좌·규칙 등록 | 목표 비중, 월 적립액, 계좌별 배분, 매수일 | portfolio, plan |
| MVP | 이번 달 매수 지시서 | 목표 비중·평가액·환율·가격으로 자산별 매수 금액 산출 | plan |
| MVP | 실행 기록 · 준수 점수 | 지시서 대비 실제 실행 체크. 건너뜀·초과·매도 기록, 연속 준수 개월 | portfolio |
| MVP | 적립식 타임머신 | 내 규칙으로 과거 N년 했다면 지금 얼마, 최대 낙폭 | backtest |
| MVP | 현금흐름 | 배당·분배금을 원화 기준 월별 합산 | income |
| MVP | 신화 검증 페이지(분석 필수) | 매수일 타이밍 효과 · 환율 타이밍 효과 · 커버드콜 분배금 원금잠식 여부 | backtest |
| 2순위 | 규칙 어긴 비용 | 건너뛴 달·판 날을 규칙대로 했을 때와 비교 | backtest |
| 2순위 | 리밸런싱 알림 | 목표 비중 이탈 시 알림 | plan |
| 구상 | 보유 자산 뉴스 | 네이버 뉴스 API | (news) |
| 구상 | 세금 경고 | 금융소득 2천만 원, 해외주식 양도세 250만 원 | plan |
| 구상 | 공시 요약 LLM | 후속 과목 | — |

### 2.4 화면

| 화면 | 내용 | 호출 서비스 |
|---|---|---|
| 이번 달 | 매수 지시서, 실행 체크박스, 준수 점수 | plan, portfolio |
| 자산 현황 | 자산·계좌별 평가액(원화 환산), 목표 vs 현재 비중 | portfolio |
| 타임머신 | 규칙 백테스트 결과 그래프, 최대 낙폭 | backtest |
| 현금흐름 | 월별 분배금 달력 | income |
| 신화 검증 | 세 가지 분석 결과 표·그래프 | backtest |
| 데이터 | 수집 데이터 설명·출처·기초 통계 (**수업 필수 페이지**) | market-data, income |

### 2.5 차별점

기존 앱(더리치 · 뱅크샐러드 · 증권사 앱)은 "지금 얼마 있나"에서 끝난다. 루틴은 "이번 달 뭘 하나"와 "규칙을 지켰나"를 다룬다. 계좌·자산군·통화가 섞인 적립식을 한 화면에서 지시하는 서비스는 없다.

### 2.6 비즈니스 모델

- 구독: 타임머신 · 규칙 위반 비용 · 리밸런싱 알림.
- 증권사 제휴: 지시서에서 ISA·연금 계좌 개설 유도, 매수 링크.
- B2B: 자산운용사 대상 "적립식 투자자 행동 데이터".

---

## 3. 데이터 출처 (발표 필수: 명칭·기관·URL)

| 데이터 | 출처 | 방식 | 갱신 | 서비스 |
|---|---|---|---|---|
| 국내 주식·ETF 일별 시세 | 공공데이터포털 「금융위원회_주식시세정보」 | Open API (인증키) | 일 1회 | market-data |
| 미국·홍콩 ETF 일별 시세 · 환율 이력 | Yahoo Finance chart API (Stooq 는 JS 검증으로 불가) | HTTP JSON (키 불필요) | 일 1회 | market-data |
| 비트코인 | 업비트 Open API (docs.upbit.com) | Open API (키 불필요) | 일 1회 + 조회 시 | market-data |
| 환율 (USD·HKD) | 한국수출입은행 환율 Open API | Open API (인증키) | 일 1회 | market-data |
| 국내 배당 결정 | DART OpenAPI (opendart.fss.or.kr) | Open API (인증키) | 일 1회 | income |
| 국내 ETF 분배금 | ETF 운용사 페이지 (TIGER·KODEX 등) | 크롤링 (5주차 실습) | 월 1회 | income |
| 미국 ETF 분배금 | 운용사 분배 내역 페이지 | 크롤링 | 월 1회 | income |

인증키 3개(공공데이터포털 · 수출입은행 · DART)는 승인에 시간이 걸리므로 **4주차 전에 각자 발급**한다. 키는 `.env`로만 다루고 저장소·프롬프트에 넣지 않는다.

---

## 4. 아키텍처

### 4.1 서비스 5개 (데이터 소유권 기준)

| 서비스 | 담당 질문 | 소유 테이블 (스키마) | 호출하는 서비스 |
|---|---|---|---|
| market-data | 이 자산이 지금·과거에 얼마였나, 환율은 | `market.assets`, `market.prices`(일별), `market.fx_rates` | 없음 |
| income | 이 자산이 언제 얼마를 분배했나 | `income.distributions`, `income.dividend_events` | market-data |
| portfolio | 내가 뭘 얼마나 갖고 있고 뭘 실행했나 | `portfolio.users`, `accounts`, `holdings`, `executions`, `rules` | market-data |
| plan | 이번 달 뭘 얼마 사야 하나 | `plan.instructions`, `plan.instruction_items` | portfolio, market-data |
| backtest | 이 규칙으로 과거에 했으면, 규칙 어긴 비용은 | `backtest.runs`, `backtest.results` | market-data, income, portfolio |

수집기는 별도 서비스가 아니다. 시세 수집은 market-data 안에, 분배금 수집은 income 안에 둔다(장부 주인이 수집한다).

### 4.2 호출 그래프

```
            apps/web (Vercel)
                 │  plan · portfolio · backtest · income 만 호출
     ┌───────────┼──────────────┬──────────────┐
     ▼           ▼              ▼              ▼
   plan      portfolio       backtest        income
     │  ╲        │           ╱   │   ╲          │
     │   ╲       │          ╱    │    ╲         │
     ▼    ╲      ▼         ╱     ▼     ╲        ▼
 portfolio ╲ market-data ◀┘   income    ╲▶ market-data
            ╲▶ market-data
```

- market-data는 아무도 부르지 않고 답만 한다(최하층).
- 순환 호출 없음. 장애는 아래에서 위로만 번진다.
- 서비스 간 통신은 동기 REST/JSON만 쓴다. 이벤트·큐는 구상으로만 발표.

### 4.3 데이터 흐름 (한 달)

1. 매일 새벽: market-data 수집 잡이 시세·환율을 받아 `market.prices`에 쌓는다. income 수집 잡은 월 1회 분배금을 받는다.
2. 월초(매수일 D-1): plan이 portfolio에서 보유·규칙을 읽고 market-data에서 가격·환율을 읽어 지시서를 만든다.
3. 사용자가 "이번 달" 화면에서 실행을 체크하면 portfolio가 `executions`에 기록한다.
4. 월말: backtest가 준수 점수·규칙 위반 비용을 계산하고, income이 월 현금흐름을 합산한다.

### 4.4 DB

Supabase 프로젝트 하나, 스키마 5개(`market`, `income`, `portfolio`, `plan`, `backtest`). 서비스마다 자기 스키마만 권한이 있는 Postgres 역할을 만들어 접속한다. 비용 없이 소유권을 강제하는 방법이며 세미나의 "강결합 방지" 사례가 된다. 로컬은 SQLite(2주차 방식, `DATABASE_URL` 전환).

### 4.5 배포 환경 두 벌 (같은 Docker 이미지)

| | 팀 운영 (수업 제출) | 세미나 실험실 |
|---|---|---|
| 프론트 | Vercel | Vercel (동일) |
| 백엔드 5개 | Render Web Service ×5 (모노레포 Root Directory) | 로컬 kind → 7주차 EC2 k3s |
| DB | Supabase | Supabase (동일) |
| 게이트웨이 | 없음 (프론트가 직접 호출) | APISIX |
| 관측 | OTel → Grafana Cloud 무료 | OTel → Prometheus · Tempo · Grafana |
| 스케줄 잡 | GitHub Actions cron → `/internal/sync` 호출 | k8s CronJob |

Render 무료 플랜은 서비스마다 콜드 스타트(30~60초)가 있다. 발표 전에 미리 깨우고, 프론트에 "서버 깨우는 중" 안내를 둔다(개인 과제에서 이미 만든 패턴).

---

## 5. 저장소와 공통 규약

### 5.1 모노레포 `routine`

수업이 GitHub 주소 하나를 요구하므로 모노레포로 간다. `contracts/`가 세미나에서 말하는 api-contracts 중앙 저장소 역할을 한다.

```
routine/
├── contracts/                 # OpenAPI 명세 — 단일 진실 공급원 (구현보다 먼저 쓴다)
│   ├── market-data.yaml
│   ├── income.yaml
│   ├── portfolio.yaml
│   ├── plan.yaml
│   ├── backtest.yaml
│   └── .spectral.yaml         # 전사 스타일 규칙
├── services/
│   ├── market-data/           # FastAPI · Dockerfile · tests/
│   ├── income/
│   ├── portfolio/
│   ├── plan/
│   └── backtest/
├── apps/web/                  # React (Vite) — 팀 페이지 겸 서비스 화면
├── platform/
│   ├── compose/               # 로컬 통합 실행
│   ├── k8s/                   # kind·k3s 매니페스트, APISIX, OTel Collector
│   └── backstage/             # catalog-info.yaml
├── docs/
│   ├── api.md                 # 발표 필수 문서 1 (contracts에서 자동 생성)
│   ├── db.md                  # 발표 필수 문서 2 (테이블·컬럼·PK/FK·관계)
│   └── data-sources.md        # 출처 표
└── .github/workflows/
    ├── contracts.yml          # Spectral 린트 + oasdiff 하위호환 검사
    ├── services.yml           # 테스트 + 명세 드리프트 검사 + 이미지 빌드(GHCR)
    ├── pact.yml               # 계약 테스트 (6주차)
    └── sync.yml               # 수집 스케줄
```

### 5.2 API 스타일 가이드 (Spectral 규칙으로 강제)

| 항목 | 규칙 |
|---|---|
| 경로 | `/v1/` 접두사, kebab-case, 복수 명사. 예: `/v1/fx-rates`, `/v1/instructions/{id}` |
| 메서드 | 조회 GET, 생성 POST, 수정 PATCH, 삭제 DELETE |
| 응답 | JSON, 필드는 snake_case, 날짜는 ISO 8601, 통화 필드 필수(`currency`) |
| 목록 | `?cursor=&limit=` 페이지네이션, 응답에 `items`와 `next_cursor` |
| 오류 | RFC 9457 Problem Details (`application/problem+json`): `type`, `title`, `status`, `detail`, `instance` |
| 헤더 | 요청 `X-Request-ID` 전파 필수(트레이스 연결) |
| 공통 엔드포인트 | `GET /healthz`, `GET /openapi.json`, `POST /internal/sync`(수집 트리거, 내부 토큰) |
| 버전 파괴 | 필드 삭제·타입 변경·필수화는 `/v2`로. oasdiff가 PR에서 차단 |

### 5.3 API-First 개발 순서 (팀원 전원)

1. `contracts/<service>.yaml`에 엔드포인트를 먼저 쓴다. 호출하는 쪽 팀원이 리뷰한다.
2. PR → Spectral 린트 통과, oasdiff가 main 대비 Breaking Change 없음 확인.
3. 구현. FastAPI가 만드는 `/openapi.json`을 CI가 contracts와 비교해 드리프트를 잡는다.
4. 호출하는 쪽은 contracts로 Mock 서버(Prism)를 띄워 상대 서비스가 없어도 개발한다. **이게 5명이 병렬로 일할 수 있는 이유다.**

---

## 6. 세미나 트랙 — 문제와 툴 대응

| 문제 | 툴 | 어디에 | 언제 (주차) | 데모 Before/After |
|---|---|---|---|---|
| 문서 파편화 | OpenAPI 3.1 + `contracts/` | 저장소 | 4 | 서비스마다 다른 /docs → 한 폴더 |
| 규칙 불일치 | Spectral | GitHub Actions | 4 | camelCase 필드 PR이 CI에서 실패 |
| Breaking Change | oasdiff | GitHub Actions | 4 | 필드 삭제 PR이 차단됨 |
| 소비자 계약 | Pact (pact-python) | plan→market-data, backtest→income | 6 | market-data 응답 변경 시 plan 계약 테스트 실패 |
| 인증·Rate Limit·라우팅 | APISIX (standalone) | k8s | 7 | 프론트가 5개 주소 → 게이트웨이 1개, 키 없는 호출 401 |
| 장애 추적 | OpenTelemetry + Tempo/Jaeger, Prometheus, Grafana | 5(Grafana Cloud) → 7(자체 구축) | 지시서 한 요청이 plan→portfolio→market-data를 거치는 트레이스 |
| 담당자·위치 파악 | Backstage (catalog-info.yaml) | 로컬/k8s | 세미나 직전 | 서비스 5개·오너·OpenAPI·의존성 한 화면 |
| 배포·확장·복구 | Kubernetes (kind → k3s on EC2) | 7 | Pod 죽이면 되살아남, replica 2 |
| 서비스 메시 | Istio | 언급만 | — | 단일 노드에선 실익 없음을 설명 |
| 상용 대안 | Datadog | 슬라이드 | — | 통합 vs 비용 |

세미나 데모 순서: **OpenAPI → Spectral → oasdiff → Pact → APISIX → OTel/Grafana → Backstage**. "Render 환경 = Before, k8s 환경 = After"로 보여준다.

---

## 7. 주차별 실행 계획

### 4주차 (9/23 전후) — 규약 확정, 뼈대

팀
- 팀 확정, 서비스 담당 배정, 인증키 3종 발급 확인.
- 5.2 스타일 가이드 합의(30분 회의). 이걸 안 하면 이후 전부 다시 한다.
- 모노레포 생성, 서비스 5개 FastAPI 뼈대(`/healthz`, `/openapi.json`), Supabase 프로젝트·스키마 5개.
- `contracts/*.yaml` 초안: 서비스당 엔드포인트 3~5개.
- 산출물: 저장소, Render 5개 배포(뼈대), Vercel 팀 페이지 초안.

개인(세미나)
- `contracts.yml`: Spectral + oasdiff.
- `service-ci.yml`: 테스트 + 명세 드리프트 + GHCR 이미지 빌드.

### 5주차 (9/30) — 발표·퀴즈·수집기 1

팀
- **아이디어 공유 발표(2~3분)**: 2.1~2.6을 팀 페이지 한 화면으로. 슬라이드 대신 페이지.
- market-data: 국내 시세·환율·업비트 수집기 + `GET /v1/assets`, `GET /v1/prices`.
- portfolio: 사용자·계좌·보유·규칙 CRUD.
- income: 운용사 분배금 크롤러(수업 실습과 동일 주제).

개인
- OTel 자동 계측(FastAPI·requests) + Grafana Cloud 무료 티어로 트레이스 확인.

### 6주차 (10/7) — 수집기 2, 계산

팀
- market-data: 미국·홍콩 시세(Yahoo) 백필 5년.
- income: DART 배당 결정 수집.
- plan: 지시서 생성 로직 + `POST /v1/instructions`.
- backtest: 타임머신 v1(월 적립, 비중 고정).
- 프론트: 이번 달 · 자산 현황 화면.
- `sync.yml` 스케줄 가동 → 데이터가 매일 쌓이기 시작.

개인
- Pact: plan→market-data, backtest→income 계약 테스트.

### 7주차 (10/14) — 통합, 분석, 문서

팀
- backtest: 신화 검증 3종, 규칙 위반 비용.
- income: 월 현금흐름 합산.
- 프론트: 타임머신 · 현금흐름 · 신화 검증 · **데이터 페이지**.
- `docs/api.md`(contracts에서 생성), `docs/db.md`, `docs/data-sources.md`.
- 발표 리허설 1회. Render 콜드 스타트 대응 확인.

개인
- kind에 5개 서비스 + APISIX + OTel Collector + Prometheus/Tempo/Grafana.
- 여력 있으면 EC2 k3s 배포(수업 AWS 주와 겹침). 없으면 kind로 세미나 데모.

### 8주차 (10/21) — 발표

발표 필수 항목 대응:

| 필수 항목 | 이 문서 |
|---|---|
| 서비스 아키텍처 | 4.1~4.3 그림 |
| 사용 데이터 및 출처 | 3 |
| 데이터 활용 기획 시나리오 | 2.2 |
| 비즈니스 모델 | 2.6 |
| 주요 페이지 및 기능 | 2.3, 2.4 |
| 데이터 분석·정리 결과 | 신화 검증 페이지 + 데이터 페이지 |
| 주소 3개 | GitHub 모노레포 · Vercel · Render `plan` 서비스의 `/docs` (나머지 4개도 링크) |
| 문서 2개 | `docs/api.md`, `docs/db.md` |

---

## 8. 팀 역할 (5명 기준)

| 역할 | 담당 | 비고 |
|---|---|---|
| market-data | 팀원 A | 수집기 가장 많음. 6주차 Open API 실습과 직결 |
| income | 팀원 B | 5주차 크롤링 실습과 직결 |
| portfolio + 프론트 | 팀원 C | 화면이 portfolio를 가장 많이 씀 |
| backtest + 데이터 페이지 | 팀원 D | 분석 페이지 담당 |
| plan + 플랫폼 (contracts·CI·배포·관측) | 조인성 | 세미나 트랙 겸임 |

4명이면 plan을 portfolio 담당이 겸하고, 팀 페이지는 backtest 담당이 겸한다. 각자 자기 서비스의 OpenAPI 명세 · 테이블 문서 · 실습 기록을 책임진다.

---

## 9. 리스크와 대응

| 리스크 | 대응 |
|---|---|
| 9/23 휴강으로 4주차 회의 못 함 | 규약 합의는 온라인 문서 코멘트로. 뼈대는 조인성이 먼저 만들어 배포 |
| 인증키 승인 지연 | 4주차 전 발급. 지연 시 Yahoo·업비트(키 불필요)부터 |
| 팀원이 서비스 간 의존 때문에 막힘 | contracts 기반 Prism Mock으로 상대 서비스 없이 개발 |
| Render 콜드 스타트로 발표 중 지연 | 발표 10분 전 전 서비스 깨우기, 프론트 안내 문구 |
| 세미나 트랙이 팀 시간을 잠식 | 세미나 툴은 전부 CI·개인 환경에만. 팀원 요구사항은 5.3 네 줄뿐 |
| 범위 초과 | 2.3의 MVP 밖은 전부 "구상"으로 발표. 실패한 실험도 원인·과정 기록하면 평가 반영(강의계획서) |
| 무료 플랜 한도 | Supabase 1주 미사용 시 일시정지 → sync 잡이 매일 접속하므로 회피. EC2는 사용 후 즉시 정리 |

---

## 10. 진행 상태

- [x] 2026-09-19 모노레포 · 서비스 5개 프로토타입 · contracts · Spectral/oasdiff/pytest CI · compose · render.yaml · Backstage 카탈로그 · 문서 (조인성)
- [ ] 팀원에게 공유, 서비스 담당 정하기
- [ ] 각자 인증키 3종 발급 (공공데이터포털 · 수출입은행 · DART)
- [ ] Supabase 프로젝트 · 스키마 5개 · Render Blueprint 배포 · Vercel 팀 페이지 (4주차)
