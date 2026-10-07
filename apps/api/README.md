# apps/api — 합본 배포 (Render 웹 서비스 1개)

서비스 4개의 코드는 그대로 두고, 한 컨테이너 안에서 각자 포트로 띄운 뒤 게이트웨이가 접두사로 넘긴다.

| 주소 | 내용 |
|---|---|
| `/docs` · `/openapi.json` | 네 서비스를 합친 Swagger 하나 (발표 자료에 넣는 주소) |
| `/healthz` | 네 서비스 상태 묶음 |
| `/market-data/…` `/youtube/…` `/mentions/…` `/stats/…` | 각 서비스로 프록시. `/<service>/docs` 는 서비스별 Swagger |

로컬: `make up` 뒤 `cd apps/api && PUBLIC_URL=http://127.0.0.1:8000 ../../.venv/bin/uvicorn gateway:app --port 8000`
(launcher 없이 게이트웨이만 띄우면 이미 떠 있는 8001~8004 를 쓴다.)

Docker: `docker build -f apps/api/Dockerfile -t hindsight/api . && docker run -p 8000:8000 --env-file .env hindsight/api`

환경변수: `DATABASE_URL`(Supabase Session pooler, 네 서비스가 스키마만 달리 씀) · `INTERNAL_TOKEN` · `ALLOWED_ORIGINS` · `YOUTUBE_API_KEY` · `DART_KEY` · `DATA_GO_KR_KEY` · `PUBLIC_URL`
