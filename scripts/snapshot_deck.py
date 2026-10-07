"""발표 페이지가 쓰는 숫자 스냅샷 — 서비스 API 에서 현황·요약을 뽑아 apps/team-page/data/snapshot.json 으로.
발표 페이지는 이 파일을 먼저 읽고, API_URL 이 깨어 있으면 같은 값을 실시간으로 덮어쓴다(Render 가 자는 경우 대비).
    .venv/bin/python scripts/snapshot_deck.py                      # 로컬 서비스(8001~8004)
    API_URL=https://hindsight-api.onrender.com .venv/bin/python scripts/snapshot_deck.py"""
import json
import os
from datetime import datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
API = os.getenv("API_URL", "").rstrip("/")
BASE = {s: (f"{API}/{s}" if API else f"http://127.0.0.1:{p}") for s, p in {"market-data": 8001, "youtube": 8002, "mentions": 8003, "stats": 8004}.items()}
c = httpx.Client(timeout=120)


def get(svc, path, **params):
    r = c.get(BASE[svc] + path, params=params); r.raise_for_status(); return r.json()


names = {a["asset_id"]: a for a in get("market-data", "/v1/assets", limit=5000)["items"]}
summaries = {i["key"]: i["value"] for i in get("stats", "/v1/summaries")["items"]}  # 전체 논조 키
for st in ("bull", "bear", "neutral"):  # 논조별 키는 "bull:overall:20" 처럼 접두사로
    for i in get("stats", "/v1/summaries", stance=st)["items"]:
        summaries[f"{st}:{i['key']}"] = i["value"]
channels = get("youtube", "/v1/channels")["items"]


def top_assets(h=20, kind="stock", n=12):
    rows = []
    for k, v in summaries.items():
        if not k.startswith("asset:") or not k.endswith(f":{h}") or not v.get("n"):
            continue
        aid = k[6:-(len(str(h)) + 1)]
        a = names.get(aid, {})
        if (a.get("asset_type") == "theme") != (kind == "theme"):
            continue
        rows.append({"asset_id": aid, "name": a.get("name", aid), "market": a.get("market"), **{x: v.get(x) for x in ("n", "mean", "median", "win_rate", "excess_mean", "vol_ratio_median", "low_sample")}})
    return sorted(rows, key=lambda r: -r["n"])[:n]


trend = get("mentions", "/v1/mentions/trending", days=30, limit=10)["items"]
chmap = {c["channel_id"]: c for c in channels}
rk = get("stats", "/v1/channels/ranking", horizon=20, metric="excess_mean", min_n=30, limit=3, stance="bull")
ranking = {side: [{"title": chmap.get(r["channel_id"], {}).get("title", r["channel_id"]), "n": r["n"], "mean": r["mean"], "excess_mean": r["excess_mean"], "win_rate": r["win_rate"]} for r in rk[side]] for side in ("top", "bottom")}
snap = {
    "generated_at": datetime.now().isoformat(timespec="minutes"),
    "youtube": get("youtube", "/v1/coverage"),
    "mentions": get("mentions", "/v1/coverage"),
    "market": get("market-data", "/v1/coverage"),
    "stats": get("stats", "/v1/coverage"),
    "channels": {"total": len(channels), "stock": sum(1 for x in channels if x["category"] == "stock"), "crypto": sum(1 for x in channels if x["category"] == "crypto")},
    "summary": {k: summaries.get(k) for k in ["overall:5", "overall:20", "overall:60", "market:KRX:20", "market:US:20", "market:CRYPTO:20", "kind:theme:20",
                                               "bull:overall:5", "bull:overall:20", "bull:overall:60", "bull:market:KRX:20", "bull:market:US:20", "bull:market:CRYPTO:20", "bull:kind:theme:20",
                                               "bear:overall:20", "neutral:overall:20", "bear:overall:5", "bear:overall:60"]},
    "stance_counts": get("mentions", "/v1/coverage").get("by_stance", {}),
    "top_assets_20": top_assets(20, "stock"), "top_themes_20": top_assets(20, "theme"),
    "trending_30d": [{"asset_id": t["asset_id"], "name": names.get(t["asset_id"], {}).get("name", t["asset_id"]), "mentions": t["mentions"], "prev": t["prev_mentions"], "channels": t["channels"]} for t in trend],
    "unmatched_sample": [u["title"] for u in get("mentions", "/v1/unmatched", limit=8)["items"]],
    "channel_ranking": ranking,
}
out = ROOT / "apps" / "team-page" / "data" / "snapshot.json"
out.write_text(json.dumps(snap, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print(f"wrote {out} ({out.stat().st_size:,} bytes)")
