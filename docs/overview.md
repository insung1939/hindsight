# 하인드사이트 한눈에 — 검토 가이드

처음 보는 사람(팀원·교수님·미래의 나)이 30분 안에 전체를 파악하도록, **무엇을 어떤 순서로 보면 되는지** 정리했다. 각 항목은 문서 하나 또는 화면 하나를 가리킨다.

## 0. 주소 (2026-10-07)

| 구분 | 주소 |
|---|---|
| 서비스 | https://hindsight-web.vercel.app |
| Swagger (백엔드 전체) | https://hindsight-api-edab.onrender.com/docs |
| 발표 페이지 | https://hindsight-gold.vercel.app |
| 저장소 | https://github.com/insung1939/hindsight |

Render 무료 플랜은 15분 유휴 시 잠든다. 첫 요청이 30~60초 걸리면 정상이다(`/healthz` 를 먼저 한 번 부르면 깨어난다).

## 1. 기획 — 왜, 누구에게, 무엇을

| 보고 싶은 것 | 어디 |
|---|---|
| 교수님 요구사항·중간 피드백 원문, 우리 해석, 필수 항목 대응표 | [requirements.md](requirements.md) |
| 문제 정의 · 사용자 · 화면 · 차별점 · 비즈니스 모델 · 지켜야 할 선 | [PLAN.md](../PLAN.md) 1장 |
| 발표에서 말할 순서로 보고 싶다 | 발표 페이지 1~3장, 14장(BM) |

## 2. 데이터 — 무엇을 어디서 어떻게 가공해 무슨 질문에 답하나 (평가의 핵심)

| 보고 싶은 것 | 어디 |
|---|---|
| 질문 ↔ 데이터 ↔ 출처 ↔ 가공 한 장 | [data-plan.md](data-plan.md) |
| 출처 표 (명칭·기관·URL·수집 항목·갱신 주기) | [data-sources.md](data-sources.md) |
| 채널 51개를 어떤 기준으로 골랐나 (후보 547 → 측정 272 → 51, 임계값 표, 빠진 채널) | [channel-selection.md](channel-selection.md) |
| 매칭 규칙 (긴 표현 우선, 흔한 단어 제외, 한글·영문 단어 경계, 테마, 코인 문맥) | `services/mentions/matcher.py` 와 `tests/test_matcher.py` (규칙이 곧 테스트) |
| 수익률 계산 규칙 (T0, r_h, 초과수익, 거래량 비율, 공시 동반) | `services/stats/engine.py` 와 `tests/test_engine.py`, [db.md](db.md) 하단 |
| 지금 얼마나 쌓였나 (단계별 실건수) | 서비스 **데이터** 탭, 또는 Swagger 의 `*/v1/coverage` |

## 3. 구조 — 설계도·구성도·데이터 흐름

| 보고 싶은 것 | 어디 |
|---|---|
| 서비스 4개와 호출 방향, 하루 배치 순서 | [../README.md](../README.md) 구조 절, [PLAN.md](../PLAN.md) 5장 |
| 발표용 아키텍처 그림 (외부 API → Render → Supabase, Vercel, Actions) | 발표 페이지 7장 |
| 합본 배포가 어떻게 생겼나 (한 프로세스에 4개 마운트) | [../apps/api/README.md](../apps/api/README.md), `apps/api/single.py` |
| 테이블·컬럼·키·관계 | [db.md](db.md) |
| API 목록·요청·응답 | [api.md](api.md) (자동 생성), 계약 원본 `contracts/*.yaml` |

## 4. 기술 스택

| 계층 | 선택 | 이유 |
|---|---|---|
| 프론트 | React 18 + Vite, 순수 SVG 차트 | 수업 기본. 평가 제외라 라이브러리 최소 |
| 백엔드 | Python 3.12, FastAPI, Pydantic, SQLAlchemy 2, httpx | 수업 기본. 서비스별 폴더 분리 + 공통 라이브러리 `libs/hs-common` |
| DB | PostgreSQL (Supabase), 로컬은 SQLite | `DATABASE_URL` 하나로 전환. 서비스마다 스키마 하나 |
| 배포 | Vercel(프론트·발표) · Render(Docker 1개, 프로세스 1개) · GitHub Actions(매일 배치) | 수업 플랫폼. Render 무료(512MB·콜드스타트) 때문에 한 프로세스 합본 |
| 품질 | pytest 31개, OpenAPI 계약 + Spectral + oasdiff CI, problem+json, X-Request-ID | AI 생성 코드를 규칙·테스트로 검증 |

## 5. 배포·운영 방법

| 보고 싶은 것 | 어디 |
|---|---|
| 처음부터 배포하는 순서 (Supabase → Render Blueprint → 데이터 복사 → Vercel → Secrets) | [deploy.md](deploy.md) |
| 환경변수와 비밀값 자리 | 루트 `.env.example`, [requirements.md](requirements.md) 6장 |
| 키가 살아 있나 확인 | `.venv/bin/python scripts/check_keys.py` |
| 매일 수집이 어떻게 도나 | `.github/workflows/sync.yml` (07:10 KST, 수동 실행도 가능) |
| 로컬에서 돌려 보기 | `make up` → `make smoke` → `make web` ([../README.md](../README.md) 로컬 실행 절) |

## 6. 결과 — 숫자

| 보고 싶은 것 | 어디 |
|---|---|
| 전체·시장별·테마·종목별 분포 | 서비스 **언급 뒤에** 탭 |
| 채널별 성적 상·하위 3, 전체 랭킹 | 서비스 **채널** 탭 (`GET /stats/v1/channels/ranking`) |
| 종목 하나의 언급 시점과 주가, 공시 | 서비스 **종목 타임라인** 탭 |
| 발표용 요약과 "발견" 문장 | 발표 페이지 11~13장 (숫자는 `apps/team-page/data/snapshot.json`, API 가 깨어 있으면 실시간) |

## 7. 진행 상태와 남은 일

[checklist.md](checklist.md) — 요구조건 대조표, 결정 사항, 할 일, 일정. 새 세션은 이 파일부터.
