"""채널 후보 발굴 · 선정 기준 테스트.

왜: 채널을 사람이 지어내지 않고, YouTube API 로 후보를 모은 뒤 구독자 수 · 업로드 빈도 · 제목의 종목 언급률을 실제로 재서
임계값을 정한다. 결과는 docs/channel-selection.md(선정 근거)와 scripts/channels.json(등록 목록)으로 남긴다.

쿼터: search.list 는 100 유닛이라 여기서만 쓴다(기본 질의 18개 ≈ 1,800 유닛). channels/playlistItems 는 1 유닛.
원시 응답은 .run/discover/ 에 캐시해 다시 돌려도 쿼터를 쓰지 않는다.

사용:  .venv/bin/python scripts/discover_channels.py            # 전부
       .venv/bin/python scripts/discover_channels.py --no-search # 캐시된 후보로 분석만
"""
import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "mentions"))
sys.path.insert(0, str(ROOT / "services" / "market-data"))
from matcher import build_terms, match  # noqa: E402
from seed import AMBIGUOUS_NAMES  # noqa: E402

BASE = "https://www.googleapis.com/youtube/v3"
CACHE = ROOT / ".run" / "discover"
CACHE.mkdir(parents=True, exist_ok=True)

CHANNEL_QUERIES = ["주식", "주식 투자", "미국주식", "해외주식", "코인", "비트코인", "암호화폐", "종목 분석", "재테크 주식", "증권"]
VIDEO_QUERIES = ["삼성전자 주가", "엔비디아 주식", "SK하이닉스 전망", "테슬라 주가", "코스피 전망", "비트코인 전망", "이더리움 전망", "급등주"]
HANGUL = re.compile(r"[가-힣]")
CRYPTO_WORDS = ("코인", "크립토", "비트", "블록체인", "crypto", "bitcoin", "가상자산", "암호화폐")


def key() -> str:
    for line in (ROOT / "services" / "youtube" / ".env").read_text().splitlines():
        if line.startswith("YOUTUBE_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("services/youtube/.env 에 YOUTUBE_API_KEY 가 없습니다")


KEY = key()
UNITS = Counter()


def get(path: str, cost: int, cache_name: str | None = None, **params) -> dict:
    f = CACHE / f"{cache_name}.json" if cache_name else None
    if f and f.exists():
        return json.loads(f.read_text())
    r = httpx.get(f"{BASE}/{path}", params={**params, "key": KEY}, timeout=30)
    if r.status_code == 404:  # 업로드 재생목록이 없는(영상 0개·비공개) 채널
        return {}
    if r.status_code >= 400:
        raise SystemExit(f"YouTube API {r.status_code}: {r.text[:300].replace(KEY, '***')}")
    UNITS[path] += cost
    data = r.json()
    if f:
        f.write_text(json.dumps(data, ensure_ascii=False))
    return data


def search_channels() -> set[str]:
    ids: set[str] = set()
    for q in CHANNEL_QUERIES:
        d = get("search", 100, f"search_ch_{q}", part="snippet", type="channel", q=q, maxResults=50, regionCode="KR", relevanceLanguage="ko")
        ids |= {it["snippet"]["channelId"] for it in d.get("items", [])}
    since = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
    for q in VIDEO_QUERIES:
        d = get("search", 100, f"search_vid_{q}", part="snippet", type="video", q=q, maxResults=50, order="viewCount",
                publishedAfter=since, regionCode="KR", relevanceLanguage="ko")
        ids |= {it["snippet"]["channelId"] for it in d.get("items", [])}
    return ids


def channel_stats(ids: list[str]) -> list[dict]:
    out = []
    for i in range(0, len(ids), 50):
        chunk = ids[i:i + 50]
        d = get("channels", 1, "ch_" + chunk[0], part="snippet,statistics,contentDetails", id=",".join(chunk), maxResults=50)
        for c in d.get("items", []):
            st, sn = c["statistics"], c["snippet"]
            out.append({"channel_id": c["id"], "title": sn["title"], "handle": sn.get("customUrl", ""), "country": sn.get("country", ""),
                        "description": sn.get("description", "")[:300],
                        "subscribers": int(st.get("subscriberCount", 0) or 0), "videos": int(st.get("videoCount", 0) or 0),
                        "views": int(st.get("viewCount", 0) or 0),
                        "uploads": c["contentDetails"]["relatedPlaylists"]["uploads"]})
    return out


def recent_titles(playlist_id: str, channel_id: str) -> list[tuple[str, datetime, str]]:
    d = get("playlistItems", 1, "pl_" + channel_id, part="snippet,contentDetails", playlistId=playlist_id, maxResults=50)
    return [(it["snippet"]["title"], datetime.fromisoformat(it["snippet"]["publishedAt"].replace("Z", "+00:00")),
             it.get("contentDetails", {}).get("videoId") or it["snippet"]["resourceId"]["videoId"]) for it in d.get("items", [])]


ISO_DUR = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


def durations(video_ids: list[str], channel_id: str) -> dict[str, int]:
    d = get("videos", 1, "dur_" + channel_id, part="contentDetails", id=",".join(video_ids[:50]), maxResults=50)
    out = {}
    for v in d.get("items", []):
        m = ISO_DUR.fullmatch(v["contentDetails"].get("duration", "PT0S")) or ISO_DUR.match("PT0S")
        h, mi, se = (int(x or 0) for x in m.groups())
        out[v["id"]] = h * 3600 + mi * 60 + se
    return out


MEDIA_WORDS = ("경제TV", "경제 TV", "뉴스", "News", "SBS", "KBS", "MBC", "JTBC", "YTN", "MTN", "연합", "매일경제", "한경", "이데일리", "서울경제", "딜사이트", "TomatoTV",
               "이투데이", "증권", "Bithumb", "빗썸", "업비트", "LS증권", "교보", "한국투자", "KB증권", "키움", "삼성증권", "머니투데이", "라디오", "경제타임즈")


def load_terms():
    import sqlite3
    con = sqlite3.connect(ROOT / "services" / "market-data" / "market-data.db")
    rows = con.execute("SELECT asset_id, name, aliases, market, curated FROM assets WHERE asset_type != 'index'").fetchall()
    items = [{"asset_id": a, "name": n, "aliases": json.loads(al or "[]"), "market": m, "curated": bool(c), "ambiguous": n in AMBIGUOUS_NAMES}
             for a, n, al, m, c in rows]
    return build_terms(items, set(AMBIGUOUS_NAMES))


def analyze(channels: list[dict], terms, floor: int) -> list[dict]:
    rows = []
    for c in channels:
        if c["subscribers"] < floor:
            continue
        korean = c["country"] == "KR" or bool(HANGUL.search(c["title"] + c["description"]))
        if not korean:
            continue
        titles = recent_titles(c["uploads"], c["channel_id"])
        if len(titles) < 10:
            continue
        span_days = max((titles[0][1] - titles[-1][1]).total_seconds() / 86400, 0.5)
        per_week = len(titles) / span_days * 7
        durs = durations([v for _, _, v in titles], c["channel_id"])
        shorts_share = sum(1 for d_ in durs.values() if d_ <= 60) / max(len(durs), 1)
        media = any(w.lower() in c["title"].lower() for w in MEDIA_WORDS)
        text_blob = (c["title"] + " " + c["description"]).lower()
        crypto_hint = any(w in text_blob for w in CRYPTO_WORDS)
        hits, markets = 0, Counter()
        for t, _, _ in titles:
            m = match(t, terms, crypto_channel=crypto_hint)
            if m:
                hits += 1
                for aid, _, _ in m:
                    markets[aid.split(":")[0]] += 1
        rate = hits / len(titles)
        category = "crypto" if markets and markets.most_common(1)[0][0] == "CRYPTO" else "stock"
        last = titles[0][1]
        rows.append({**c, "sample": len(titles), "uploads_per_week": round(per_week, 1), "mention_rate": round(rate, 2),
                     "mentions_per_week": round(per_week * rate, 1), "category": category, "markets": dict(markets),
                     "shorts_share": round(shorts_share, 2), "media": media,
                     "days_since_last": (datetime.now(timezone.utc) - last).days})
    return rows


RULES = {
    # A단: 대형 영향력 채널 — 구독자가 많으면 언급률이 낮아도(시황 섞여도) 한 번의 언급이 닿는 사람이 많다
    "A": {"min_subscribers": 1_000_000, "min_mention_rate": 0.15, "max_uploads_per_week": 110},
    # B단: 종목 집중 채널 — 규모는 작아도 제목에 종목을 콕 집는 채널
    "B": {"min_subscribers_stock": 50_000, "min_subscribers_crypto": 100_000, "min_mention_rate": 0.30, "max_uploads_per_week": 35},
    "max_days_since_last": 45, "max_shorts_share": 0.5, "exclude_media": True, "min_sample": 10,
}


def tier(r: dict) -> str | None:
    if r["days_since_last"] > RULES["max_days_since_last"] or r["shorts_share"] > RULES["max_shorts_share"]:
        return None
    if RULES["exclude_media"] and r["media"]:
        return None
    a = RULES["A"]
    if r["subscribers"] >= a["min_subscribers"] and r["mention_rate"] >= a["min_mention_rate"] and r["uploads_per_week"] <= a["max_uploads_per_week"]:
        return "A"
    b = RULES["B"]
    floor = b["min_subscribers_crypto"] if r["category"] == "crypto" else b["min_subscribers_stock"]
    if r["subscribers"] >= floor and r["mention_rate"] >= b["min_mention_rate"] and r["uploads_per_week"] <= b["max_uploads_per_week"]:
        return "B"
    return None


def passes(r: dict, min_sub: int, min_rate: float) -> bool:
    """임계값 표용(B단 조건만 바꿔 가며 본다)."""
    return (r["subscribers"] >= min_sub and r["mention_rate"] >= min_rate and r["days_since_last"] <= RULES["max_days_since_last"]
            and r["uploads_per_week"] <= RULES["B"]["max_uploads_per_week"] and r["shorts_share"] <= RULES["max_shorts_share"]
            and not (RULES["exclude_media"] and r["media"]))


def threshold_table(rows: list[dict]) -> str:
    subs = [30_000, 50_000, 100_000, 200_000, 500_000]
    rates = [0.2, 0.3, 0.5]
    lines = ["| 구독자 ≥ | " + " | ".join(f"언급률 ≥ {r:.0%}" for r in rates) + " |", "|---|" + "---|" * len(rates)]
    for sb in subs:
        cells = []
        for rt in rates:
            sel = [r for r in rows if passes(r, sb, rt)]
            cells.append(f"{len(sel)}개 · 주 {sum(r['mentions_per_week'] for r in sel):.0f}건 (코인 {sum(1 for r in sel if r['category']=='crypto')})")
        lines.append(f"| {sb:,} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def write_outputs(rows: list[dict]) -> list[dict]:
    for r in rows:
        r["tier"] = tier(r)
    chosen = [r for r in rows if r["tier"]]
    chosen.sort(key=lambda r: (r["tier"], r["category"], -r["subscribers"]))
    (ROOT / "scripts" / "channels.json").write_text(json.dumps(
        [{"handle": r["handle"], "channel_id": r["channel_id"], "title": r["title"], "category": r["category"], "tier": r["tier"],
          "subscribers": r["subscribers"], "uploads_per_week": r["uploads_per_week"], "mention_rate": r["mention_rate"]} for r in chosen],
        ensure_ascii=False, indent=1) + "\n")
    B = RULES["B"]
    excluded_media = [r for r in rows if r["media"] and r["subscribers"] >= B["min_subscribers_stock"] and r["mention_rate"] >= B["min_mention_rate"]]
    excluded_spam = [r for r in rows if not r["media"] and not r["tier"] and r["subscribers"] >= B["min_subscribers_stock"] and r["mention_rate"] >= B["min_mention_rate"]
                     and (r["uploads_per_week"] > B["max_uploads_per_week"] or r["shorts_share"] > RULES["max_shorts_share"])]
    excluded_big = [r for r in rows if not r["media"] and not r["tier"] and r["subscribers"] >= RULES["A"]["min_subscribers"] and r["days_since_last"] <= RULES["max_days_since_last"]]
    today = datetime.now().strftime("%Y-%m-%d")
    md = [f"# 채널 선정 기준과 결과 ({today})", "",
          "채널은 사람이 고르지 않고 `scripts/discover_channels.py` 가 YouTube Data API 로 후보를 모아 측정한 뒤 규칙으로 걸렀다. "
          "측정 표본은 채널별 최근 업로드 50편의 **제목**이고, 언급률은 그중 종목 사전(국내·미국·코인)에 잡히는 제목의 비율이다.", "",
          "## 1. 후보 수집", "",
          f"- `search.list` 채널 검색 {len(CHANNEL_QUERIES)}개 질의({', '.join(CHANNEL_QUERIES)}) + 최근 90일 조회수 상위 영상 검색 {len(VIDEO_QUERIES)}개 질의({', '.join(VIDEO_QUERIES)})",
          f"- 후보 채널 {len(json.loads((CACHE / 'candidate_ids.json').read_text()))}개 → 구독자 3만 이상·한국어·영상 10편 이상 {len(rows)}개를 측정", "",
          "## 2. 측정 항목", "",
          "| 항목 | 뜻 | 출처 |", "|---|---|---|",
          "| 구독자 수 | 채널 영향력 | channels.list statistics |",
          "| 주당 업로드 | 최근 50편이 걸친 기간으로 환산 | playlistItems.list |",
          "| 언급률 | 최근 50편 제목 중 종목이 잡힌 비율 | 우리 매칭기(services/mentions/matcher.py) |",
          "| 쇼츠 비율 | 60초 이하 영상 비율 | videos.list contentDetails |",
          "| 미디어 여부 | 방송사·증권사·거래소 공식 채널 | 채널명 키워드 |", "",
          "## 3. 임계값 테스트", "",
          f"구독자 하한과 언급률 하한을 바꿔 가며 남는 채널 수와 기대 언급 수(주당)를 봤다. 공통 조건: 최근 {RULES['max_days_since_last']}일 내 업로드, 주당 {B['max_uploads_per_week']}편 이하, 쇼츠 {RULES['max_shorts_share']:.0%} 이하, 미디어 제외.", "",
          threshold_table(rows), "",
          "## 4. 채택한 규칙 — 2단", "",
          "표를 보면 구독자 하한을 5만에서 10만으로 올리면 채널은 반으로 주는데 언급 수도 거의 반으로 준다(작은 채널이 종목을 더 자주 말한다). "
          "반대로 언급률 하한을 30%로 두면 삼프로TV(22%)·김작가TV(28%)·달란트투자(16%) 같은 **구독자 수백만 채널이 전부 빠진다.** "
          "서비스 질문은 '많은 사람이 들은 언급 뒤에 어떻게 됐나'이므로 영향력 큰 채널을 뺄 수 없다. 그래서 기준을 둘로 나눴다.", "",
          "| 단 | 뜻 | 구독자 | 언급률 | 주당 업로드 |", "|---|---|---|---|---|",
          f"| A 대형 영향력 | 시황이 섞여도 한 번의 언급이 닿는 사람이 많다 | {RULES['A']['min_subscribers']:,} 이상 | {RULES['A']['min_mention_rate']:.0%} 이상 | {RULES['A']['max_uploads_per_week']} 이하 |",
          f"| B 종목 집중 | 규모는 작아도 제목에 종목을 콕 집는다 | 주식 {B['min_subscribers_stock']:,} · 코인 {B['min_subscribers_crypto']:,} 이상 | {B['min_mention_rate']:.0%} 이상 | {B['max_uploads_per_week']} 이하 |", "",
          f"공통: 최근 {RULES['max_days_since_last']}일 내 업로드(활동 중), 쇼츠 {RULES['max_shorts_share']:.0%} 이하, 방송사·증권사·거래소 공식 채널 제외.", "",
          "- 코인 하한을 10만으로 더 높인 이유: 코인 채널은 거의 모든 제목에 '비트코인'이 들어가(언급률 90~100%) 채널 수를 늘려도 표본의 다양성이 늘지 않는다.",
          "- 주당 업로드 상한: 하루 5편(B) 넘게 올리는 채널은 자동 생성형이 많았다. A단은 삼프로TV처럼 클립을 많이 쪼개 올리는 정상 채널을 위해 110으로 둔다.",
          "- 방송사·증권사·거래소 제외: 뉴스 보도는 '유튜버의 언급'이 아니고, 증권사는 이해관계가 있어 따로 봐야 한다. 비교군으로 쓸지는 추후 결정.", "",
          f"## 5. 결과 — 채널 {len(chosen)}개 (주식 {sum(1 for r in chosen if r['category']=='stock')} · 코인 {sum(1 for r in chosen if r['category']=='crypto')}), 기대 언급 주 {sum(r['mentions_per_week'] for r in chosen):.0f}건", "",
          "서비스·통계·발표에서는 A·B·C 익명 코드만 쓴다. 아래 표는 데이터 출처 공개(수집 대상) 목적이며 채널별 성적은 어디에도 내지 않는다.", "",
          "| 단 | 분류 | 채널 | 구독자 | 주당 업로드 | 언급률 | 주요 시장 |", "|---|---|---|---|---|---|---|"]
    for r in chosen:
        mk = ", ".join(f"{k} {v}" for k, v in sorted(r["markets"].items(), key=lambda x: -x[1]))
        md.append(f"| {r['tier']} | {r['category']} | {r['title']} ({r['handle']}) | {r['subscribers']:,} | {r['uploads_per_week']} | {r['mention_rate']:.0%} | {mk} |")
    md += ["", "## 6. 규칙 때문에 빠진 주요 채널", "",
           "**구독자 100만 이상인데 빠진 채널** — 대부분 제목에 종목이 거의 없다(시황·거시·예능). 5주차에 등록했던 슈카월드(2%)·소수몽키(4%)도 여기 해당해 통계에서 뺀다:", ""]
    md += [f"- {r['title']} ({r['subscribers']:,}, 언급률 {r['mention_rate']:.0%}, 주 {r['uploads_per_week']}편, 쇼츠 {r['shorts_share']:.0%})" for r in sorted(excluded_big, key=lambda r: -r['subscribers'])]
    md += ["", "**미디어(방송사·증권사·거래소)** — 구독자·언급률은 충족:", ""]
    md += [f"- {r['title']} ({r['subscribers']:,}, 주 {r['uploads_per_week']}편, 언급률 {r['mention_rate']:.0%})" for r in sorted(excluded_media, key=lambda r: -r['subscribers'])]
    md += ["", "**업로드 과다·쇼츠 위주** — 하루 5편 넘게 올리는 자동 생성형:", ""]
    md += [f"- {r['title']} ({r['subscribers']:,}, 주 {r['uploads_per_week']}편, 쇼츠 {r['shorts_share']:.0%})" for r in sorted(excluded_spam, key=lambda r: -r['mentions_per_week'])]
    md += ["", "## 7. 한계", "",
           "- 언급률은 현재 종목 사전(국내 57·미국 48·코인 전 마켓) 기준이라 소형주 위주 채널은 낮게 측정된다. DART 전 상장사 사전을 넣으면 올라간다.",
           "- 최근 50편 표본이라 최근 몇 주의 편집 방향에 흔들린다.",
           "- 검색 질의에 안 걸린 채널은 후보에 없다. 팀원이 아는 채널은 핸들로 추가 등록할 수 있다.", ""]
    (ROOT / "docs" / "channel-selection.md").write_text("\n".join(md), encoding="utf-8")
    return chosen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-search", action="store_true", help="search.list 를 건너뛰고 캐시만 쓴다")
    ap.add_argument("--floor", type=int, default=30000, help="분석할 최소 구독자 수")
    a = ap.parse_args()

    ids_file = CACHE / "candidate_ids.json"
    if a.no_search and ids_file.exists():
        ids = set(json.loads(ids_file.read_text()))
    else:
        ids = search_channels()
        ids_file.write_text(json.dumps(sorted(ids)))
    # 이미 등록된 채널도 후보에 넣는다
    import sqlite3
    con = sqlite3.connect(ROOT / "services" / "youtube" / "youtube.db")
    ids |= {r[0] for r in con.execute("SELECT channel_id FROM channels")}
    print(f"후보 채널 {len(ids)}개", file=sys.stderr)

    channels = channel_stats(sorted(ids))
    terms = load_terms()
    rows = analyze(channels, terms, a.floor)
    rows.sort(key=lambda r: (-r["mentions_per_week"], -r["subscribers"]))
    (CACHE / "analysis.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1, default=str))
    print(f"분석 {len(rows)}개 (구독자 ≥ {a.floor:,}) · 쿼터 사용 {sum(UNITS.values())} 유닛 {dict(UNITS)}", file=sys.stderr)

    chosen = write_outputs(rows)
    print(threshold_table(rows))
    print(f"\n채택 {len(chosen)}개 → scripts/channels.json · docs/channel-selection.md")
    print(f"{'단':>2} {'구독자':>9} {'주/업로드':>7} {'언급률':>5} {'주/언급':>6} {'쇼츠':>4} {'분류':>6}  채널")
    for r in chosen:
        print(f"{r['tier']:>2} {r['subscribers']:>9,} {r['uploads_per_week']:>7} {r['mention_rate']:>5} {r['mentions_per_week']:>6} {r['shorts_share']:>4} {r['category']:>6}  {r['title']} ({r['handle']})")
    print(f"합계: 주식 {sum(1 for r in chosen if r['category']=='stock')} · 코인 {sum(1 for r in chosen if r['category']=='crypto')} · 기대 언급 주 {sum(r['mentions_per_week'] for r in chosen):.0f}건")


if __name__ == "__main__":
    main()
