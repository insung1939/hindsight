# API 설명 문서

`contracts/*.yaml`(OpenAPI 3.1)에서 자동 생성. 자세한 요청·응답 형식은 각 서비스의 `/docs`(Swagger UI) 또는 명세 파일을 본다.

공통 규약: 경로 `/v1/…` kebab-case · 필드 snake_case · 목록은 `items`+`next_cursor` · 오류는 RFC 9457 `application/problem+json` · 요청 헤더 `X-Request-ID` 전파.

## market-data

종목 사전(국내·미국·코인·지수 + 별칭) · 일별 시세. 출처: DART corpCode, 공공데이터포털, Yahoo Finance, 업비트.

- 소유: `team-market-data` · 호출하는 서비스: —
- 서버: `http://localhost:8001`, `https://hindsight-market-data.onrender.com`

| Method | Path | 기능 | 파라미터 | 요청 본문 | 응답 |
|---|---|---|---|---|---|
| GET | `/healthz` | 서비스 상태 | — | — | 200 json |
| GET | `/v1/dictionary` | 종목 사전 전체 (이름·별칭 → asset_id). mentions 서비스가 매칭에 쓴다 | market | — | 200 ListDictionary |
| GET | `/v1/assets` | 자산 목록 | market, tracked, q, limit | — | 200 ListAssets |
| GET | `/v1/assets/names` | 화면용 가벼운 사전 — 언급된 적 있는(tracked) 종목·테마·지수의 이름·별칭만 | all | — | 200 ListAssetNames |
| GET | `/v1/assets/{asset_id}` | 자산 하나 | asset_id | — | 200 AssetOut |
| POST | `/v1/assets/{asset_id}/track` | 시세 수집 대상으로 켠다 (mentions 가 새 종목을 발견했을 때 호출) | asset_id | — | 200 AssetOut |
| GET | `/v1/assets/{asset_id}/prices` | 일별 종가 이력 | asset_id, from, to, limit | — | 200 ListPrices |
| GET | `/v1/prices` | 여러 종목 시세를 한 번에 (stats 서비스용). asset_ids 는 쉼표 구분 | asset_ids, from, to | — | 200 BatchPrices |
| GET | `/v1/disclosures` | DART 공시 (asset_ids 쉼표 구분, 기간). stats 가 '언급 전후 공시 여부' 에, 타임라인이 표시에 쓴다 | asset_ids, from, to, kind, limit | — | 200 ListDisclosures |
| GET | `/v1/coverage` | 수집 현황 (데이터 페이지용): 사전·시세·거래량·공시·뉴스 건수 | — | — | 200 MarketCoverage |
| POST | `/internal/sync-attention` | tracked 국내 종목의 DART 공시 수집 (days 소급). DART_KEY 없으면 건너뜀 | days, X-Internal-Token | — | 200 AttentionSyncResult |
| POST | `/internal/sync` | 사전 갱신(DART·업비트) + tracked 종목 시세 수집 | days, dictionary, X-Internal-Token | — | 200 SyncResult |

## youtube

추적 채널과 영상 메타데이터(제목·설명·게시일·조회수). 출처: YouTube Data API v3.

- 소유: `team-youtube` · 호출하는 서비스: —
- 서버: `http://localhost:8002`, `https://hindsight-youtube.onrender.com`

| Method | Path | 기능 | 파라미터 | 요청 본문 | 응답 |
|---|---|---|---|---|---|
| GET | `/healthz` | 서비스 상태 | — | — | 200 json |
| GET | `/v1/channels` | 채널 목록 (실명·핸들·구독자) | — | — | 200 ListChannels |
| POST | `/v1/channels` | 채널 등록 (핸들 → YouTube API 로 id 조회) | — | ChannelIn | 201 ChannelOut |
| GET | `/v1/videos` | 영상 목록 (since 이후, 게시일 오름차순). mentions 가 매일 새 영상을 받아간다 | since, channel_id, cursor, limit | — | 200 ListVideos |
| GET | `/v1/videos/{video_id}` | 영상 하나 | video_id | — | 200 VideoOut |
| GET | `/v1/coverage` | 수집 현황 (데이터 페이지용) | — | — | 200 Coverage |
| POST | `/internal/sync` | 추적 채널의 새 영상 수집 (days 만큼 거슬러; 최초 백필은 days=365) | days, X-Internal-Token | — | 200 SyncResult |
| POST | `/internal/load-fixture` | 키 없이 개발할 때 쓰는 샘플 데이터 (fixtures/sample.json). 실제 채널·영상이 아니다 | X-Internal-Token | — | 200 SyncResult |

## mentions

영상 제목·설명에서 종목을 찾아 언급 사실을 저장한다. 사전은 market-data, 영상은 youtube 에서 받는다.

- 소유: `team-mentions` · 호출하는 서비스: youtube, market-data
- 서버: `http://localhost:8003`, `https://hindsight-mentions.onrender.com`

| Method | Path | 기능 | 파라미터 | 요청 본문 | 응답 |
|---|---|---|---|---|---|
| GET | `/healthz` | 서비스 상태 | — | — | 200 json |
| GET | `/v1/mentions` | 언급 목록 | asset_id, channel_id, since, after_id, limit | — | 200 ListMentions |
| GET | `/v1/mentions/trending` | 최근 N일 언급 급증 종목 (직전 N일 대비) | days, limit | — | 200 ListTrending |
| GET | `/v1/unmatched` | 종목을 못 잡은 영상 제목 (별칭 사전 보강용) | limit | — | 200 ListUnmatched |
| GET | `/v1/coverage` | 매칭 성공률 (데이터 페이지용) | — | — | 200 CoverageOut |
| POST | `/internal/sync` | youtube 의 새 영상을 market-data 사전으로 매칭 (full=true 면 처음부터 다시) | full, X-Internal-Token | — | 200 SyncResult |

## stats

언급 뒤 5·20·60 거래일 수익률과 벤치마크 대비 초과수익. 채널별 랭킹 포함.

- 소유: `team-stats` · 호출하는 서비스: mentions, market-data
- 서버: `http://localhost:8004`, `https://hindsight-stats.onrender.com`

| Method | Path | 기능 | 파라미터 | 요청 본문 | 응답 |
|---|---|---|---|---|---|
| GET | `/healthz` | 서비스 상태 | — | — | 200 json |
| GET | `/v1/summary` | 전체 분포 (scope=overall | market:KRX | market:US | market:CRYPTO | kind:theme | asset:<id> | channel:<id>) | scope, horizon | — | 200 SummaryOut |
| GET | `/v1/summaries` | 요약 전부 (prefix 로 필터: overall · market · channel · asset) | prefix, horizon, slim | — | 200 ListSummaries |
| GET | `/v1/coverage` | 계산 현황 (데이터 페이지용): 언급별 수익률이 몇 건 채워졌나 | — | — | 200 StatsCoverage |
| GET | `/v1/channels/ranking` | 채널 랭킹 — 언급 뒤 수익률 기준 상·하위 (metric=excess_mean|mean|win_rate, 표본 min_n 이상만) | horizon, metric, min_n, limit | — | 200 ChannelRanking |
| GET | `/v1/assets/{asset_id}/events` | 종목 하나의 언급별 이후 수익률 (타임라인 화면) | asset_id | — | 200 ListEvents |
| GET | `/v1/channels/{channel_id}/events` | 채널 하나의 언급별 이후 수익률 | channel_id | — | 200 ListEvents |
| POST | `/internal/sync` | 새 언급의 수익률 계산 + 미완성 값 채우기 + 요약 갱신 | since_days, full, X-Internal-Token | — | 200 SyncResult |
