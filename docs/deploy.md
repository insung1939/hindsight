# 배포 절차 (수업 제출: Vercel · Render · Supabase · GitHub Actions)

2026-10-07 결정: 백엔드는 **Render 웹 서비스 1개**(`apps/api`, 서비스 4개 + 게이트웨이를 한 컨테이너에). Swagger 주소도 하나다. 분리 배포(k8s·APISIX)는 세미나용으로 `platform/` 에 남겨 둔다.

```
① Supabase 프로젝트 → DATABASE_URL (Session pooler)
② Render Blueprint → hindsight-api  (render.yaml 이 읽힘, 환경변수 6개 입력)
③ 로컬 SQLite 데이터를 Supabase 로 복사 (scripts/migrate_sqlite_to_pg.py) — 유튜브 쿼터를 다시 쓰지 않기 위해
④ Vercel 에 apps/web 배포 (VITE_API_URL = ②의 주소) → ②의 ALLOWED_ORIGINS 에 Vercel 주소 추가
⑤ GitHub Secrets (API_URL · INTERNAL_TOKEN) → sync 워크플로 수동 실행 → 매일 07:10 자동
```

## ① Supabase (사용자)

1. supabase.com → New project `hindsight`. 무료 플랜은 활성 프로젝트 2개까지라 기존 것 하나를 Pause.
2. Connect → **Session pooler** 문자열(`postgresql://postgres.<ref>:[PASSWORD]@…pooler.supabase.com:5432/postgres`). Render 는 IPv4 라 Direct 는 안 된다. 비밀번호 특수문자는 URL 인코딩(`@`→`%40`).
3. 스키마 4개(`market` `yt` `mentions` `stats`)는 서비스가 첫 기동 때 `CREATE SCHEMA IF NOT EXISTS` 로 만든다.
4. 문자열은 저장소 루트 `.env`(gitignore 됨)에 `DATABASE_URL=` 로 넣어 두면 ③에서 쓴다.

키·접속 확인: `.venv/bin/python scripts/check_keys.py` (YouTube · DART · 공공데이터포털 · Supabase 를 실제 호출해 OK/FAIL 만 출력, 값은 출력하지 않는다).

## ② Render (사용자 클릭 + 조인성 안내)

Render 는 "프로젝트 추가"가 아니라 **GitHub 저장소를 연결한 웹 서비스**를 만드는 것이다. 계정만 있으면 된다(무료).

1. dashboard.render.com → New → **Blueprint** → GitHub 연결 → `insung1939/hindsight` 선택. `render.yaml` 을 읽어 `hindsight-api` 하나를 만든다.
2. `sync: false` 환경변수를 묻는다:

| 변수 | 값 |
|---|---|
| `DATABASE_URL` | ①의 Session pooler 문자열 |
| `INTERNAL_TOKEN` | `openssl rand -hex 24` 결과 (⑤의 Secret 과 같은 값) |
| `ALLOWED_ORIGINS` | 일단 `http://localhost:5173`, ④ 뒤에 `https://<vercel>.vercel.app,http://localhost:5173` 로 수정 |
| `YOUTUBE_API_KEY` `DART_KEY` `DATA_GO_KR_KEY` | 있는 것만. 없으면 비움 |

3. Apply. Docker 빌드 5~8분. Live 가 되면 `/healthz` 가 네 서비스 전부 ok 여야 한다. Swagger: `/docs`.
4. **주의**: `hindsight-api.onrender.com` 은 다른 사람이 쓰고 있어 Render 가 접미사를 붙인다. 실제 배포 주소는 **https://hindsight-api-edab.onrender.com** (2026-10-07). 게이트웨이는 요청 호스트로 주소를 만들므로 설정을 바꿀 필요는 없고, 프론트(`VITE_API_URL`)·발표 페이지(`deck.js`)·GitHub Secret(`API_URL`)에 이 주소를 쓴다.

## ③ 데이터 옮기기 (조인성)

```bash
DATABASE_URL=postgresql://… .venv/bin/python scripts/migrate_sqlite_to_pg.py        # 네 서비스의 SQLite → Supabase 스키마별 복사
```
이후 증분은 ⑤의 배치가 채운다. 백필을 Render 에서 다시 돌리면 유튜브 쿼터를 하루치(약 1,500 유닛) 더 쓰므로 복사가 낫다.

## ④ Vercel 프론트

```bash
cd apps/web
npx vercel link --yes --project hindsight-web
npx vercel env add VITE_API_URL production      # https://hindsight-api-edab.onrender.com
npx vercel --prod
```
주소가 나오면 Render 의 `ALLOWED_ORIGINS` 에 넣고 재배포(환경변수 저장 시 자동).

## ⑤ 매일 수집

```bash
gh secret set API_URL --body https://hindsight-api-edab.onrender.com
gh secret set INTERNAL_TOKEN           # 프롬프트에 ②의 값
gh workflow run sync && gh run watch   # 최초는 inputs 로 youtube_days=365, price_days=420 가능
```

## 확인

- `/healthz` 네 서비스 ok → `/docs` 에서 `GET /stats/v1/summary` Try it out → 프론트 네 화면이 실데이터로 뜨는지.
- Render 무료 플랜은 15분 유휴 시 잠든다. 첫 요청 30~60초. **발표 직전 `/healthz` 를 한 번 호출**해 깨운다(워크플로도 매일 깨운다).

## 자주 막히는 것

| 증상 | 원인 · 조치 |
|---|---|
| 빌드 실패 `COPY libs/...` | Blueprint 의 `dockerContext: .` 누락. render.yaml 그대로면 없다 |
| `/healthz` 가 degraded | 자식 서비스 하나가 안 떴다. Render Logs 에서 `[launcher]` 줄 확인(대개 DATABASE_URL 오타) |
| 프론트 `blocked by CORS policy` | `ALLOWED_ORIGINS` 에 Vercel 주소가 정확히(https, `/` 없이) 있는지 |
| `no route to host` / `ENOTFOUND` | Direct 대신 Session pooler, 사용자명 `postgres.<ref>` |
| `/internal/sync` 401 | `X-Internal-Token` 이 Render 의 `INTERNAL_TOKEN` 과 다름 |
| 메모리 초과로 재시작 (502 뒤 잠깐 HTML 오류 페이지) | 무료 512MB. 프로세스 5개 기본 약 310MB. DART 상장사 목록 갱신(`dictionary=true`)이 가장 무거워 **일요일에만** 돌린다(sync.yml). 2026-10-07 OTel 지연 import·iterparse 로 최대 약 340MB 로 낮춤. 로컬 재현: `docker run -m 512m …` |
