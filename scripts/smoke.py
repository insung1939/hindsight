"""서비스 4개를 띄운 뒤(scripts/dev_up.sh 또는 make compose) 파이프라인을 한 바퀴 돌리는 스모크 테스트 겸 데모.

    python scripts/smoke.py             # 샘플 영상(fixture)으로 전체 흐름
    python scripts/smoke.py --real      # YOUTUBE_API_KEY 가 있을 때: 등록된 실제 채널의 최근 30일 영상 수집
    python scripts/smoke.py --no-prices # 시세 수집 건너뜀 (이미 받아 둔 경우)

흐름: market-data(사전·시세) → youtube(영상) → mentions(매칭, 새 종목 track) → market-data(새 종목 시세) → stats(수익률·요약)
"""
import os
import sys

import httpx

BASE = {"market-data": "http://127.0.0.1:8001", "youtube": "http://127.0.0.1:8002",
        "mentions": "http://127.0.0.1:8003", "stats": "http://127.0.0.1:8004"}
c = httpx.Client(timeout=600, headers={"X-Internal-Token": os.getenv("INTERNAL_TOKEN", "dev-token")})


def call(svc, method, path, **kw):
    r = c.request(method, BASE[svc] + path, **kw)
    if r.status_code >= 400:
        print(f"  !! {svc} {method} {path} -> {r.status_code} {r.text[:300]}")
        r.raise_for_status()
    return r.json() if r.content else None


def step(t):
    print(f"\n== {t}")


if "--no-prices" not in sys.argv:
    step("1) market-data: 사전(업비트 마켓·DART) + tracked 종목 시세 (1~2분)")
    r = call("market-data", "POST", "/internal/sync", params={"days": 400})
    print(f"  assets_added={r['assets_added']} prices_upserted={r['prices_upserted']} skipped={len(r['skipped'])}")
    for x in r["skipped"][:3]:
        print("   -", x[:120])

if "--real" in sys.argv:
    step("2) youtube: 등록 채널의 최근 30일 영상 수집 (YouTube Data API)")
    r = call("youtube", "POST", "/internal/sync", params={"days": 30})
else:
    step("2) youtube: 샘플 영상 로드 (실제 채널·영상 아님)")
    r = call("youtube", "POST", "/internal/load-fixture")
print(f"  videos_added={r['videos_added']} channels={r['channels_synced']} {r['skipped'][:1]}")
cov = call("youtube", "GET", "/v1/coverage")
print(f"  누적 영상 {cov['videos']}편 · 채널 {cov['channels']}개")

step("3) mentions: 제목·설명 매칭 (youtube → market-data 사전 → track)")
r = call("mentions", "POST", "/internal/sync")
print(f"  scanned={r['videos_scanned']} mentions_added={r['mentions_added']} unmatched={r['unmatched_added']} newly_tracked={r['assets_tracked']}")
cov = call("mentions", "GET", "/v1/coverage")
print(f"  매칭 성공률 {cov['match_rate']:.0%} (영상 {cov['videos_seen']}편 중 {cov['videos_matched']}편), 언급 {cov['mentions']}건, 종목 {cov['assets']}개")
for u in call("mentions", "GET", "/v1/unmatched", params={"limit": 5})["items"]:
    print("   못 잡음:", u["title"][:60])

if "--no-prices" not in sys.argv:
    step("4) market-data: 새로 언급된 종목 시세")
    r = call("market-data", "POST", "/internal/sync", params={"days": 400, "dictionary": "false"})
    print(f"  prices_upserted={r['prices_upserted']}")

step("5) stats: 언급 뒤 수익률 + 요약 (mentions → market-data)")
r = call("stats", "POST", "/internal/sync")
print(f"  events_added={r['events_added']} updated={r['events_updated']} summaries={r['summaries']} skipped={len(r['skipped'])}")
for h in (5, 20, 60):
    v = call("stats", "GET", "/v1/summary", params={"scope": "overall", "horizon": h})["value"]
    if v["n"]:
        print(f"  {h:>2}일: n={v['n']} 평균 {v['mean']:+.1%} 중앙값 {v['median']:+.1%} 상승확률 {v['win_rate']:.0%} 초과 {v['excess_mean']:+.1%}")
    else:
        print(f"  {h:>2}일: 표본 없음")

step("6) 이번 주 언급 급증 (mentions)")
for i in call("mentions", "GET", "/v1/mentions/trending", params={"days": 90, "limit": 5})["items"]:
    print(f"   {i['asset_id']:18s} 언급 {i['mentions']} (직전 {i['prev_mentions']}) 채널 {i['channels']}")

print("\n완료. 프론트: cd apps/web && npm run dev → http://localhost:5173")
