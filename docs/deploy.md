# 배포 절차 (팀 운영 환경: Vercel · Render · Supabase)

순서가 중요하다. 프론트 주소가 있어야 백엔드 CORS 를 넣고, 백엔드 주소가 있어야 프론트 환경변수를 넣는다.

```
① Supabase 프로젝트 → DATABASE_URL
② Vercel 프론트 1차 배포 → https://<프로젝트>.vercel.app  (API 주소는 임시)
③ Render Blueprint → 서비스 4개 (ALLOWED_ORIGINS = ②의 주소, DATABASE_URL = ①)
④ Vercel 환경변수에 ③의 주소 5개 → 재배포
⑤ GitHub Secrets (MARKET_DATA_URL · YOUTUBE_URL · MENTIONS_URL · STATS_URL · INTERNAL_TOKEN) → sync 워크플로 수동 실행 → 데이터 채움
```

## ① Supabase

1. supabase.com → New project. 이름 `routine`, Region 가까운 곳, **Database Password 기록**.
2. Connect → **Session pooler** 문자열 복사 (`postgresql://postgres.<ref>:[PASSWORD]@…pooler.supabase.com:5432/postgres`). Render 는 IPv4 라 Direct 는 안 된다.
3. `[PASSWORD]` 를 실제 비밀번호로 바꾼다. 특수문자는 URL 인코딩(`@`→`%40`, `#`→`%23`).
4. 스키마 5개(`market` `income` `portfolio` `plan` `backtest`)는 각 서비스가 첫 기동 때 `CREATE SCHEMA IF NOT EXISTS` 로 만든다. 따로 만들 필요 없음. (서비스별 권한 분리 계정은 7주차 세미나용 선택 사항)

## ② Vercel 프론트

CLI 로 한다 (대시보드로 해도 된다: Import → 저장소 → Root Directory `apps/web`).

```bash
cd apps/web
npx vercel login
npx vercel link --yes --project routine      # 프로젝트 생성·연결
npx vercel --prod                            # 1차 배포 → 주소 확인
```

## ③ Render Blueprint

1. dashboard.render.com → New → **Blueprint** → `insung1939/hindsight` 선택. `render.yaml` 을 읽어 서비스 4개를 만든다.
2. `sync: false` 항목을 묻는다. 값:

| 변수 | 값 | 어디에 |
|---|---|---|
| `DATABASE_URL` | ①의 Session pooler 문자열 | 5개 전부 같은 값 |
| `ALLOWED_ORIGINS` | ②의 Vercel 주소 (끝에 `/` 없이). 로컬도 쓰려면 `https://….vercel.app,http://localhost:5173` | 5개 전부 |
| `INTERNAL_TOKEN` | `openssl rand -hex 24` 로 만든 값 | 4개 전부 같은 값 |
| `YOUTUBE_API_KEY` | Google Cloud 콘솔에서 발급 | youtube |
| `DATA_GO_KR_KEY` `DART_KEY` | 있으면 넣고 없으면 비움 | market-data |

3. Apply. 첫 빌드는 Docker 라 5~8분. 상태가 Live 가 되면 `https://hindsight-stats.onrender.com/docs` 로 확인.
4. 서비스 간 주소(`MARKET_DATA_URL` 등)는 Blueprint 의 `fromService` 가 자동으로 넣는다.

## ④ Vercel 환경변수 → 재배포

```bash
cd apps/web
for s in STATS MENTIONS MARKET_DATA YOUTUBE; do
  npx vercel env add VITE_${s}_URL production      # 값: https://hindsight-<service>.onrender.com
done
npx vercel --prod
```

## ⑤ 데이터 채우기

```bash
gh secret set MARKET_DATA_URL --body https://hindsight-market-data.onrender.com
gh secret set YOUTUBE_URL     --body https://hindsight-youtube.onrender.com
gh secret set MENTIONS_URL    --body https://hindsight-mentions.onrender.com
gh secret set STATS_URL       --body https://hindsight-stats.onrender.com
gh secret set INTERNAL_TOKEN  # 프롬프트에 ③의 값
gh workflow run sync && gh run watch
```

또는 브라우저에서 `https://hindsight-market-data.onrender.com/docs` → `POST /internal/sync` (헤더 `X-Internal-Token`) → `days=2000`.

## 확인

- `https://<프로젝트>.vercel.app` 에서 "시작하기" → 포트폴리오 생성 → 이번 달 지시서.
- 첫 요청은 Render 콜드 스타트로 30~60초. 다섯 서비스가 각각 깨어나야 하므로 발표 전 `/healthz` 5개를 미리 호출한다.

## 자주 막히는 것

| 증상 | 원인 · 조치 |
|---|---|
| Render 빌드 실패 `COPY libs/...` | Blueprint 의 `dockerContext: .` 가 빠짐. render.yaml 그대로 쓰면 없다 |
| 프론트 콘솔 `blocked by CORS policy` | `ALLOWED_ORIGINS` 에 Vercel 주소가 정확히(https, `/` 없이) 있는지 |
| plan 502 `market-data 호출 실패` | market-data 가 아직 슬립. 30초 뒤 재시도 |
| `no route to host` / `ENOTFOUND tenant` | Direct 대신 Session pooler, 사용자명 `postgres.<ref>` |
| `/internal/sync` 401 | `X-Internal-Token` 헤더가 Render 의 `INTERNAL_TOKEN` 과 다름 |
