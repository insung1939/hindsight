# apps/api — 합본 배포 (Render 웹 서비스 1개, 프로세스 1개)

서비스 4개의 코드(`services/*`)는 그대로 두고, `single.py` 가 네 FastAPI 앱을 **한 프로세스**에 경로 접두사로 마운트한다.
처음엔 프로세스 5개(서비스 4 + 게이트웨이)로 띄웠는데 라이브러리를 다섯 번 올려 기본 메모리만 350MB 라 Render 무료 512MB 에서 배치 중 OOM 이 났다(2026-10-07). 한 프로세스로 합쳐 기본 메모리를 크게 줄였다.

| 주소 | 내용 |
|---|---|
| `/docs` · `/openapi.json` | 네 서비스를 합친 Swagger 하나 (발표 자료에 넣는 주소) |
| `/healthz` | 네 서비스 상태 묶음 |
| `/market-data/…` `/youtube/…` `/mentions/…` `/stats/…` | 각 서비스 앱. `/<service>/docs` 는 서비스별 Swagger |

서비스 간 호출은 여전히 REST(자기 자신 `http://127.0.0.1:$PORT/<svc>`)라 분리 배포(k8s·APISIX, `platform/`)로 돌아갈 수 있다.

로컬: `cd apps/api && ../../.venv/bin/uvicorn single:app --port 8000` (SQLite 파일은 cwd 에 생긴다. `make up` 의 분리 실행과는 DB 가 다르다.)

Docker: `docker build -f apps/api/Dockerfile -t hindsight/api . && docker run -m 512m -p 8000:8000 --env-file .env hindsight/api`

환경변수: `DATABASE_URL`(Supabase Session pooler, 네 서비스가 스키마만 달리 씀) · `INTERNAL_TOKEN` · `ALLOWED_ORIGINS` · `YOUTUBE_API_KEY` · `DART_KEY` · `DATA_GO_KR_KEY`
