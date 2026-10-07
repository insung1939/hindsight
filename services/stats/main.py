"""stats — "언급 뒤 주가는 어땠나?" 에 답한다. mentions(언급)와 market-data(시세)를 부른다.
계산은 /internal/sync 배치에서 끝내 두고, 조회 API 는 저장된 결과와 요약 캐시만 읽는다(Render 콜드 스타트 대비)."""
from datetime import date, datetime, timedelta

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from engine import HORIZONS, event_day, forward_returns, summarize
from hs_common import InternalOnly, ServiceClient, create_app
from models import EventReturn, Summary, db

app = create_app("stats", "힌드사이트 stats", "0.1.0", "언급 뒤 5·20·60 거래일 수익률과 벤치마크 대비 초과수익. 채널별 랭킹 포함.")
mentions = ServiceClient("mentions", timeout=60)
market = ServiceClient("market-data", timeout=120)


@app.on_event("startup")
def _startup():
    db.create_all()


class EventOut(BaseModel):
    mention_id: int
    asset_id: str
    channel_id: str
    market: str
    kind: str = "stock"
    published_at: datetime
    t0_date: date | None
    t0_close: float | None
    r5: float | None
    r20: float | None
    r60: float | None
    x5: float | None
    x20: float | None
    x60: float | None
    vol_ratio: float | None = None
    near_disclosure: bool | None = None
    model_config = {"from_attributes": True}


class ListEvents(BaseModel):
    items: list[EventOut]
    next_cursor: str | None = None


class SummaryOut(BaseModel):
    key: str
    value: dict
    updated_at: datetime
    model_config = {"from_attributes": True}


class ListSummaries(BaseModel):
    items: list[SummaryOut]
    next_cursor: str | None = None


class StatsCoverage(BaseModel):
    events: int
    events_theme: int
    with_t0: int
    r5_filled: int
    r20_filled: int
    r60_filled: int
    vol_ratio_filled: int
    disclosure_checked: int
    last_computed_at: datetime | None
    summaries: int


class ChannelRank(BaseModel):
    channel_id: str
    n: int
    mean: float
    median: float
    win_rate: float
    excess_mean: float | None
    excess_win_rate: float | None
    vol_ratio_median: float | None


class ChannelRanking(BaseModel):
    horizon: int
    metric: str
    min_n: int
    top: list[ChannelRank]
    bottom: list[ChannelRank]
    all: list[ChannelRank]


class SyncResult(BaseModel):
    events_added: int
    events_updated: int
    summaries: int
    skipped: list[str]


def _summary(s: Session, key: str) -> dict:
    row = s.get(Summary, key)
    if not row:
        raise HTTPException(404, f"요약 {key} 없음. /internal/sync 를 먼저 실행")
    return row


@app.get("/v1/summary", response_model=SummaryOut, tags=["summary"], operation_id="get_summary",
         summary="전체 분포 (scope=overall | market:KRX | market:US | market:CRYPTO | kind:theme | asset:<id> | channel:<id>)")
def get_summary(scope: str = "overall", horizon: int = Query(default=20, description="5 · 20 · 60"), s: Session = Depends(db.session)):
    return _summary(s, f"{scope}:{horizon}")


@app.get("/v1/summaries", response_model=ListSummaries, tags=["summary"], operation_id="list_summaries",
         summary="요약 전부 (prefix 로 필터: overall · market · channel · asset)")
def list_summaries(prefix: str | None = None, s: Session = Depends(db.session)):
    q = select(Summary)
    if prefix:
        q = q.where(Summary.key.like(f"{prefix}%"))
    return {"items": s.scalars(q.order_by(Summary.key)).all(), "next_cursor": None}


@app.get("/v1/coverage", response_model=StatsCoverage, tags=["ops"], operation_id="get_stats_coverage",
         summary="계산 현황 (데이터 페이지용): 언급별 수익률이 몇 건 채워졌나")
def stats_coverage(s: Session = Depends(db.session)):
    cnt = lambda cond=None: s.scalar(select(func.count()).select_from(EventReturn).where(cond) if cond is not None else select(func.count()).select_from(EventReturn)) or 0  # noqa: E731
    return {"events": cnt(), "events_theme": cnt(EventReturn.kind == "theme"), "with_t0": cnt(EventReturn.t0_date.is_not(None)),
            "r5_filled": cnt(EventReturn.r5.is_not(None)), "r20_filled": cnt(EventReturn.r20.is_not(None)), "r60_filled": cnt(EventReturn.r60.is_not(None)),
            "vol_ratio_filled": cnt(EventReturn.vol_ratio.is_not(None)), "disclosure_checked": cnt(EventReturn.near_disclosure.is_not(None)), "last_computed_at": s.scalar(select(func.max(EventReturn.computed_at))),
            "summaries": s.scalar(select(func.count()).select_from(Summary)) or 0}


@app.get("/v1/channels/ranking", response_model=ChannelRanking, tags=["summary"], operation_id="channel_ranking",
         summary="채널 랭킹 — 언급 뒤 수익률 기준 상·하위 (metric=excess_mean|mean|win_rate, 표본 min_n 이상만)")
def channel_ranking(horizon: int = Query(default=20, description="5 · 20 · 60"), metric: str = Query(default="excess_mean", pattern="^(excess_mean|mean|win_rate)$"),
                    min_n: int = Query(default=30, ge=1), limit: int = Query(default=3, ge=1, le=20), s: Session = Depends(db.session)):
    rows = []
    for sm in s.scalars(select(Summary).where(Summary.key.like(f"channel:%:{horizon}"))).all():
        v = sm.value
        if (v.get("n") or 0) < min_n or v.get(metric) is None:
            continue
        rows.append({"channel_id": sm.key[len("channel:"):-(len(str(horizon)) + 1)], "n": v["n"], "mean": v["mean"], "median": v["median"],
                     "win_rate": v["win_rate"], "excess_mean": v.get("excess_mean"), "excess_win_rate": v.get("excess_win_rate"),
                     "vol_ratio_median": v.get("vol_ratio_median")})
    rows.sort(key=lambda r: r[metric], reverse=True)
    return {"horizon": horizon, "metric": metric, "min_n": min_n, "top": rows[:limit], "bottom": list(reversed(rows[-limit:])) if len(rows) > limit else [], "all": rows}


@app.get("/v1/assets/{asset_id}/events", response_model=ListEvents, tags=["events"], operation_id="asset_events",
         summary="종목 하나의 언급별 이후 수익률 (타임라인 화면)")
def asset_events(asset_id: str, s: Session = Depends(db.session)):
    rows = s.scalars(select(EventReturn).where(EventReturn.asset_id == asset_id).order_by(EventReturn.published_at)).all()
    return {"items": rows, "next_cursor": None}


@app.get("/v1/channels/{channel_id}/events", response_model=ListEvents, tags=["events"], operation_id="channel_events",
         summary="채널 하나의 언급별 이후 수익률")
def channel_events(channel_id: str, s: Session = Depends(db.session)):
    rows = s.scalars(select(EventReturn).where(EventReturn.channel_id == channel_id).order_by(EventReturn.published_at.desc())).all()
    return {"items": rows, "next_cursor": None}


@app.post("/internal/sync", response_model=SyncResult, tags=["ops"], operation_id="sync_stats",
          summary="새 언급의 수익률 계산 + 미완성 값 채우기 + 요약 갱신", dependencies=[InternalOnly])
def sync(since_days: int = Query(default=130, le=2000, description="이 기간의 언급만 다시 계산 (최초 백필은 400). 60거래일이 채워지려면 약 90일이면 되므로 매일은 130일"), s: Session = Depends(db.session)):
    since = datetime.utcnow() - timedelta(days=since_days)
    ments, after = [], 0
    while True:  # 2만 건도 다 받도록 id 페이징
        page = mentions.get("/v1/mentions", since=since.isoformat(), after_id=after, limit=5000)
        ments += page["items"]
        if not page.get("next_cursor"):
            break
        after = int(page["next_cursor"])
    existing = {e.mention_id: e for e in s.scalars(select(EventReturn).where(EventReturn.published_at >= since)).all()}
    asset_ids = sorted({m["asset_id"] for m in ments})
    if not asset_ids:
        return {"events_added": 0, "events_updated": 0, "summaries": 0, "skipped": ["언급 없음"]}
    assets = {a["asset_id"]: a for a in market.get("/v1/assets", limit=5000)["items"]}
    bench_ids = sorted({assets[a]["benchmark_id"] for a in asset_ids if a in assets and assets[a].get("benchmark_id")})
    series = _load_series(asset_ids + bench_ids, since.date() - timedelta(days=10))
    disc = _load_disclosures([a for a in asset_ids if a.startswith("KRX:") and assets.get(a, {}).get("asset_type") != "theme"], since.date() - timedelta(days=10))
    added, updated, skipped = 0, 0, []
    for m in ments:
        a = assets.get(m["asset_id"])
        if not a:
            skipped.append(f"{m['asset_id']}: 사전에 없음"); continue
        ser = series.get(m["asset_id"])
        if not ser:
            skipped.append(f"{m['asset_id']}: 시세 없음(아직 수집 전)"); continue
        pub = datetime.fromisoformat(m["published_at"])
        day = event_day(pub, a["market"])
        fr = forward_returns(ser, day)
        bench = series.get(a.get("benchmark_id") or "")
        br = forward_returns(bench, day) if bench else {f"r{h}": None for h in HORIZONS}
        vals = {"t0_date": fr["t0_date"], "t0_close": fr["t0_close"], "vol_ratio": fr["vol_ratio"],
                "near_disclosure": _near(disc.get(m["asset_id"]), fr["t0_date"]) if m["asset_id"] in disc else None}
        for h in HORIZONS:
            vals[f"r{h}"] = fr[f"r{h}"]
            vals[f"x{h}"] = (fr[f"r{h}"] - br[f"r{h}"]) if fr[f"r{h}"] is not None and br.get(f"r{h}") is not None else None
        ev = existing.get(m["id"])
        if ev:
            changed = any(getattr(ev, k) != v for k, v in vals.items())
            if changed:
                for k, v in vals.items():
                    setattr(ev, k, v)
                ev.computed_at = datetime.utcnow(); updated += 1
        else:
            s.add(EventReturn(mention_id=m["id"], asset_id=m["asset_id"], channel_id=m["channel_id"], market=a["market"],
                              kind="theme" if a.get("asset_type") == "theme" else "stock",
                              benchmark_id=a.get("benchmark_id"), published_at=pub, **vals)); added += 1
    s.flush()
    n = _rebuild_summaries(s)
    s.commit()
    return {"events_added": added, "events_updated": updated, "summaries": n, "skipped": skipped[:50]}


MATERIAL_KINDS = {"실적", "계약", "자금조달", "주요사항"}  # 가격에 영향이 있는 공시만 (지분 보고·기타 제외)


def _load_disclosures(ids: list[str], from_date: date) -> dict[str, list[date]]:
    """종목별 공시일 목록(실적·계약·자금조달·주요사항만). market-data 에 공시가 하나도 없으면(키 없음) 빈 dict → near_disclosure 는 null 로 남는다."""
    out: dict[str, list[date]] = {}
    for i in range(0, len(ids), 200):
        chunk = ids[i:i + 200]
        try:
            r = market.get("/v1/disclosures", asset_ids=",".join(chunk), limit=20000, **{"from": str(from_date)})
        except HTTPException:
            return {}
        for d_ in r["items"]:
            if d_["kind"] in MATERIAL_KINDS:  # 지분·기타 공시는 대형주에 거의 매일 있어 제외
                out.setdefault(d_["asset_id"], []).append(date.fromisoformat(d_["rcept_dt"]))
    if not out:
        return {}
    for a in ids:  # 공시 데이터가 있는 상태에서 공시가 없는 종목은 False 로 판정되게 빈 목록을 둔다
        out.setdefault(a, [])
    return out


def _near(days: list[date] | None, t0: date | None, window: int = 3) -> bool | None:
    if days is None or t0 is None:
        return None
    return any(abs((d_ - t0).days) <= window for d_ in days)


def _load_series(ids: list[str], from_date: date) -> dict[str, list[tuple]]:
    out = {}
    for i in range(0, len(ids), 100):
        chunk = ids[i:i + 100]
        r = market.get("/v1/prices", asset_ids=",".join(chunk), **{"from": str(from_date)})
        for sr in r["series"]:
            out[sr["asset_id"]] = [(date.fromisoformat(p[0]), p[1], p[2] if len(p) > 2 else None) for p in sr["points"]]
    return out


def _rebuild_summaries(s: Session) -> int:
    """요약 캐시 재계산. ORM 객체 대신 컬럼 튜플만 읽어 메모리를 아낀다(5만 건 ORM 은 Render 무료 512MB 에서 OOM)."""
    cols = (EventReturn.market, EventReturn.kind, EventReturn.channel_id, EventReturn.asset_id,
            EventReturn.r5, EventReturn.r20, EventReturn.r60, EventReturn.x5, EventReturn.x20, EventReturn.x60,
            EventReturn.vol_ratio, EventReturn.near_disclosure)
    groups: dict[str, list[tuple]] = {"overall": []}
    for row in s.execute(select(*cols)).yield_per(5000):
        market, kind, channel_id, asset_id = row[0], row[1], row[2], row[3]
        payload = row[4:]
        if kind == "theme":
            groups.setdefault("kind:theme", []).append(payload)
        else:
            groups["overall"].append(payload)
            groups.setdefault("kind:stock", []).append(payload)
            groups.setdefault(f"market:{market}", []).append(payload)
            groups.setdefault(f"channel:{channel_id}", []).append(payload)
        groups.setdefault(f"asset:{asset_id}", []).append(payload)
    idx = {5: (0, 3), 20: (1, 4), 60: (2, 5)}  # (r 위치, x 위치) in payload
    n = 0
    for key, evs in groups.items():
        for h in HORIZONS:
            ri, xi = idx[h]
            val = summarize([{"r": e[ri], "x": e[xi], "v": e[6], "d": e[7]} for e in evs], h)
            val["scope"] = key
            k = f"{key}:{h}"
            row = s.get(Summary, k)
            if row:
                row.value = val; row.updated_at = datetime.utcnow()
            else:
                s.add(Summary(key=k, value=val))
            n += 1
        evs.clear()
    return n
