# HINDSIGHT — 유튜버가 오른다고 한 종목, 정말 올랐을까?

**배포 주소 (2026-10-07)** · 서비스 https://hindsight-web.vercel.app · Swagger https://hindsight-api-edab.onrender.com/docs · 발표 페이지 https://hindsight-gold.vercel.app · 저장소 https://github.com/insung1939/hindsight

KAIST 디지털금융MBA 〈클라우드컴퓨팅실습〉 팀 프로젝트. 주식·코인 유튜브 채널이 영상 제목에서 언급한 종목을 모아, **언급 뒤 5·20·60 거래일 동안 주가가 실제로 어떻게 움직였는지** 통계로 보여준다. 채널 실명과 채널별 성적(상·하위)을 보여주되 학습용 통계임을 고지하고, 종목 추천 문구는 없다.

**처음 보면 [docs/overview.md](docs/overview.md)(검토 가이드) 부터.** 교수님 요구사항·중간 피드백·디자인 원칙은 [docs/requirements.md](docs/requirements.md), 현재 상태와 10/21 까지의 할 일은 [docs/checklist.md](docs/checklist.md). 기획·역할은 [PLAN.md](PLAN.md), API 설명은 [docs/api.md](docs/api.md), 테이블은 [docs/db.md](docs/db.md), 데이터 출처는 [docs/data-sources.md](docs/data-sources.md), 배포는 [docs/deploy.md](docs/deploy.md), 세미나 데모는 [docs/seminar-demo.md](docs/seminar-demo.md).

> 평가 포인트(교수 피드백): **어떤 소스에서 데이터를 가져와 어떻게 가공해 무슨 가치를 주는가.** UI 가 아니라 데이터와 API 호출이 중심. 발표의 절반은 파이프라인(소스 → 수집 → 매칭 → 계산 → 결과)에 실제 건수를 붙여 설명한다.

## 구조 — 서비스 4개 (데이터 소유권 기준)

| 서비스 | 담당 질문 | 소유 데이터 | 호출하는 서비스 | 로컬 포트 |
|---|---|---|---|---|
| `market-data` | 이 종목이 언제 얼마였나, 종목 사전은 | 자산 마스터+별칭, 일별 시세, 지수 | — | 8001 |
| `youtube` | 어떤 채널이 언제 무슨 영상을 올렸나 | 채널(실명·핸들·구독자), 영상 메타 | — | 8002 |
| `mentions` | 이 영상이 어떤 종목을 말했나 | 언급, 못 잡은 제목 | youtube, market-data | 8003 |
| `stats` | 언급 뒤 주가는 어땠나 | 언급별 수익률, 요약 캐시 | mentions, market-data | 8004 |

```
              apps/web (Vercel)
        ┌────────┴────────┬──────────────┐
        ▼                 ▼              ▼
      stats           mentions      market-data (타임라인·사전 읽기)
      │   ╲            │    ╲
      ▼    ╲           ▼     ╲
   mentions ╲       youtube   ╲
             ╲▶ market-data ◀──┘
```

- 각 서비스는 자기 스키마만 읽고 쓴다. 남의 데이터는 REST 로만. 순환 호출 없음.
- 수집은 소유 서비스 안의 `/internal/sync`. 매일 순서: market-data → youtube → mentions → market-data(새 종목) → stats.
- `X-Request-ID` 전파, 오류는 RFC 9457 `application/problem+json`, 명세는 `contracts/` 가 기준.

**매칭 규칙** (`services/mentions/matcher.py`): 사전(이름·별칭)을 긴 표현부터 정확 문자열 매칭, 잡힌 구간은 지워 중복 방지, 흔한 단어(KT·삼성·현대 …)는 단독 매칭 금지, 영문은 단어 경계로만. 못 잡은 제목은 버리지 않고 남겨 성공률을 화면에 그대로 보여준다.

```
hindsight/
├── contracts/          OpenAPI 3.1 명세 4개 — 단일 진실 공급원. .spectral.yaml 이 스타일 규칙
├── libs/hs-common      앱 골격 · 오류 포맷 · 요청 ID · DB · 서비스 간 클라이언트 · .env 로더
├── services/<svc>/     FastAPI + SQLAlchemy, Dockerfile, tests/(계약 드리프트 + 매칭 규칙)
├── apps/web/           React (Vite) — 이번 주 언급 · 언급 뒤에(분석) · 종목 타임라인 · 데이터
├── apps/api/           합본 배포(Render 1개): 서비스 4개를 한 프로세스에 마운트(/docs 하나) — single.py · Dockerfile
├── apps/team-page/     발표 페이지(정적)
├── platform/           compose(서비스+게이트웨이+관측) · gateway(APISIX) · k8s(kustomize) · backstage
├── docs/               requirements · checklist · data-plan · channel-selection · api · db · data-sources · deploy · seminar-demo
├── scripts/            dev_up/down · smoke.py · discover_channels.py(채널 선정) · register_channels.py · migrate_sqlite_to_pg.py · export_contracts.py · gen_api_docs.py
└── .github/workflows/  contracts(Spectral·oasdiff) · services(pytest·GHCR 이미지) · sync(매일 수집)
```

## 로컬 실행 (5분)

```bash
make setup                     # venv + 의존성 + npm install (최초 1회)
make up                        # 서비스 4개 → http://127.0.0.1:800{1..4}/docs
make smoke                     # 사전·시세 → 샘플 영상 → 매칭 → 수익률 한 바퀴
cd apps/web && npm run dev     # http://localhost:5173
make down
```

키 없이도 샘플 영상으로 전 과정이 돈다. 실제 채널을 쓰려면 `services/youtube/.env` 에 `YOUTUBE_API_KEY=` 를 넣고 채널을 등록한다.

```bash
curl -X POST localhost:8002/v1/channels -H 'Content-Type: application/json' -d '{"handle":"@채널핸들","category":"stock"}'
python scripts/smoke.py --real          # 최근 30일 영상 수집 → 매칭 → 수익률
```

선택 키: `DART_KEY`(국내 전 상장사 사전), `DATA_GO_KR_KEY`(국내 시세, 없으면 Yahoo 국내 심볼로 대체). 키는 `.env` 로만, 저장소·프롬프트에 넣지 않는다.

Docker: `make compose` (서비스 4개) · `make compose-all` (+ APISIX 9080 · Grafana 3000 · Prometheus 9090 · Tempo 3200). 명령 목록 `make help`.

## 개발 규칙 (팀원 전원) — API-First

1. **명세 먼저.** `contracts/<service>.yaml` 에 엔드포인트를 쓰고, 호출하는 쪽 팀원이 리뷰한다.
2. **PR 은 CI 를 통과해야 한다.** Spectral(스타일) · oasdiff(하위 호환) · pytest(구현이 명세와 같은지).
3. **그다음 구현.** `python scripts/export_contracts.py <service>` 로 명세를 갱신하면 그 diff 가 리뷰 대상.
4. **상대 서비스가 없어도 개발한다.** `npx @stoplight/prism-cli mock contracts/market-data.yaml`.

## 배포

| 계층 | 팀 운영 (수업 제출) | 세미나 실험실 |
|---|---|---|
| 프론트 | Vercel (`apps/web`) | 동일 |
| 백엔드 | Render 웹 서비스 **1개** — [render.yaml](render.yaml) → `apps/api`(서비스 4개 + 게이트웨이, Swagger 하나) | kind/minikube → EC2 k3s (`platform/k8s`) + APISIX, 서비스별 컨테이너 |
| DB | Supabase (스키마 `market` `yt` `mentions` `stats`) | 동일 |
| 관측 | OTel → Grafana Cloud | OTel → Prometheus · Tempo · Grafana |
| 수집 | GitHub Actions `sync.yml` 매일 07:10 | k8s CronJob |

## 데이터 출처

| 데이터 | 출처 | 키 |
|---|---|---|
| 채널·영상 메타(제목·설명·게시일·조회수) | YouTube Data API v3 (수업 제공) | 필요 |
| 상장사 이름·종목코드 | DART OpenAPI corpCode (수업 제공) | 필요 (없으면 시드 57개) |
| 국내 시세 | 공공데이터포털 금융위원회_주식시세정보 | 필요 (없으면 Yahoo 대체) |
| 미국 시세 · 코스피/S&P500 지수 · 국내 대체 | Yahoo Finance chart API | 불필요 |
| 코인 마켓 목록 · 일봉 | 업비트 Open API | 불필요 |

자막·댓글은 수집하지 않는다. 채널은 실명으로 보여주되(2026-10-07 팀 결정) 학습용 통계이며 추천이 아님을 화면에 고정 고지한다.

피드백 반영으로 추가한 것: 거래량(Yahoo·업비트 응답에 포함) · 업종·테마 사전 20개(반도체·2차전지 등 → 대표 ETF 시세) · DART 공시(언급 전후 공시 여부, 키 대기). 네이버 뉴스 API 는 소급 불가·과금 우려로 제외. 상세는 [docs/data-plan.md](docs/data-plan.md).

## AI 활용

구조와 코드는 Claude Code 와 함께 작성했고, 생성된 코드는 로컬에서 실행해 `scripts/smoke.py`, 매칭 규칙 테스트, 브라우저로 확인한 뒤 반영했다.
