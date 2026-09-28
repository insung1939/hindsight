# DB 테이블 문서

Supabase(PostgreSQL) 프로젝트 하나에 **서비스마다 스키마 하나**(`market` `yt` `mentions` `stats`). 각 서비스는 자기 스키마만 쓴다. 로컬은 SQLite 파일. 테이블은 서비스 시작 시 `create_all` 로 만든다.

서비스 간에는 **외래키를 걸지 않는다.** 다른 서비스의 id(`asset_id`, `video_id`, `channel_id`, `mention_id`)는 문자열·정수로만 보관하고 REST 로 조회한다.

## market (market-data)

| 테이블 | 컬럼 | 키 |
|---|---|---|
| `assets` | asset_id(`시장:심볼`), market(KRX·US·CRYPTO·INDEX), symbol, name, aliases(JSON), currency, asset_type(stock·etf·crypto·index), source(datagokr·yahoo·upbit), yahoo_symbol, benchmark_id, tracked, updated_at | PK asset_id |
| `prices` | id, asset_id, trade_date, close, currency, collected_at | PK id · UQ(asset_id, trade_date) |

`assets` 가 곧 종목 사전이다. `tracked=True` 인 것만 시세를 매일 긁는다(언급되면 mentions 가 켠다). `benchmark_id` 는 초과수익 기준(코스피·S&P500·비트코인).

## yt (youtube)

| 테이블 | 컬럼 | 키 |
|---|---|---|
| `channels` | channel_id, handle, title, category(stock·crypto), anon_code, uploads_playlist_id, subscriber_count, tracked, added_at | PK channel_id · UQ anon_code |
| `videos` | video_id, channel_id, title, description, published_at, view_count, collected_at | PK video_id · FK channel_id |

`handle`·`title` 은 API 응답에 내지 않는다(익명 원칙). 자막·댓글 컬럼 없음.

## mentions

| 테이블 | 컬럼 | 키 |
|---|---|---|
| `mentions` | id, video_id, channel_id, asset_id, matched_text, field(title·description), confidence(1.0·0.8), published_at, view_count, created_at | PK id · UQ(video_id, asset_id) |
| `unmatched` | video_id, channel_id, title, published_at | PK video_id |
| `sync_state` | key, value | PK key |

## stats

| 테이블 | 컬럼 | 키 |
|---|---|---|
| `event_returns` | id, mention_id, asset_id, channel_id, market, benchmark_id, published_at, t0_date, t0_close, r5, r20, r60, x5, x20, x60, computed_at | PK id · UQ mention_id |
| `summaries` | key(`overall:20`, `market:KRX:20`, `channel:<id>:20`, `asset:<id>:20`), value(JSON), updated_at | PK key |

`r_n` = P(T0+n거래일)/P(T0) − 1, `x_n` = r_n − 벤치마크 같은 구간 수익률. n일이 안 지났으면 null 로 두고 다음 배치에서 채운다.

## 관계 요약

```
yt.channels 1 ─ n yt.videos
yt.videos 1 ─ n mentions.mentions        (video_id, FK 없음)
market.assets 1 ─ n mentions.mentions    (asset_id, FK 없음)
market.assets 1 ─ n market.prices
mentions.mentions 1 ─ 1 stats.event_returns (mention_id, FK 없음)
```
