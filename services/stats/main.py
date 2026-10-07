"""stats — "언급 뒤 주가는 어땠나?" 에 답한다. mentions(언급)와 market-data(시세)를 부른다.
계산은 /internal/sync 배치에서 끝내 두고, 조회 API 는 저장된 결과와 요약 캐시만 읽는다(Render 콜드 스타트 대비)."""
from datetime import date, datetime, timedelta

import threading

from fastapi import BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from engine import HORIZONS, event_day, forward_returns, summarize
from hs_common import InternalOnly, ServiceClient, create_app, memo_ttl
from models import EventReturn, Summary, db

app = create_app("stats", "하인드사이트 stats", "0.1.0", "언급 뒤 5·20·60 거래일 수익률과 벤치마크 대비 초과수익. 채널별 랭킹 포함.")
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
    stance: str = "neutral"
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
    assets_n: int | None = None  # 언급한 종목 수
    assets_up: int | None = None  # 그중 평균 수익률이 양(+)인 종목 수
    asset_win_rate: float | None = None  # assets_up / assets_n


class ChannelRanking(BaseModel):
    horizon: int
    metric: str
    stance: str = "all"
    min_n: int
    top: list[ChannelRank]
    bottom: list[ChannelRank]
    all: list[ChannelRank]


class SyncStatus(BaseModel):
    state: str  # idle · running · done · failed
    started_at: datetime | None = None
    finished_at: datetime | None = None
    result: dict | None = None
    error: str | None = None


_job = {"state": "idle", "started_at": None, "finished_at": None, "result": None, "error": None}
_job_lock = threading.Lock()


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
def get_summary(scope: str = "overall", horizon: int = Query(default=20, description="5 · 20 · 60"),
                stance: str = Query(default="all", pattern="^(all|bull|bear|neutral)$", description="제목 논조. 화면 기본은 bull(낙관 언급만)"),
                s: Session = Depends(db.session)):
    key = f"{scope}:{horizon}" if stance == "all" else f"{stance}:{scope}:{horizon}"
    return _summary(s, key)


@app.get("/v1/summaries", response_model=ListSummaries, tags=["summary"], operation_id="list_summaries",
         summary="요약 전부 (prefix 로 필터: overall · market · channel · asset)")
def list_summaries(prefix: str | None = None, horizon: int | None = Query(default=None, description="5 · 20 · 60 중 하나만"),
                   stance: str = Query(default="all", pattern="^(all|bull|bear|neutral)$", description="all 이면 전체 논조 키, 아니면 그 논조 키만"),
                   slim: bool = Query(default=False, description="true 면 histogram 을 빼고 준다 (목록 화면용, 응답 1/5)"),
                   s: Session = Depends(db.session)):
    q = select(Summary)
    if prefix:
        q = q.where(Summary.key.like(f"{(stance + ':') if stance != 'all' else ''}{prefix}%"))
    elif stance != "all":
        q = q.where(Summary.key.like(f"{stance}:%"))
    if stance == "all":
        q = q.where(~Summary.key.like("bull:%"), ~Summary.key.like("bear:%"), ~Summary.key.like("neutral:%"))
    if horizon:
        q = q.where(Summary.key.like(f"%:{horizon}"))
    rows = s.scalars(q.order_by(Summary.key)).all()
    strip = (stance + ":") if stance != "all" else None
    out = []
    for r in rows:
        key = r.key[len(strip):] if strip and r.key.startswith(strip) else r.key
        out.append({"key": key, "updated_at": r.updated_at, "value": ({k: v for k, v in r.value.items() if k != "histogram"} if slim else r.value)})
    return {"items": out, "next_cursor": None}


@app.get("/v1/coverage", response_model=StatsCoverage, tags=["ops"], operation_id="get_stats_coverage",
         summary="계산 현황 (데이터 페이지용): 언급별 수익률이 몇 건 채워졌나")
def stats_coverage(s: Session = Depends(db.session)):
    return _stats_coverage_cached()


@memo_ttl(300)
def _stats_coverage_cached():
    with db.SessionLocal() as s:
        cnt = lambda cond=None: s.scalar(select(func.count()).select_from(EventReturn).where(cond) if cond is not None else select(func.count()).select_from(EventReturn)) or 0  # noqa: E731
        return {"events": cnt(), "events_theme": cnt(EventReturn.kind == "theme"), "with_t0": cnt(EventReturn.t0_date.is_not(None)),
                "r5_filled": cnt(EventReturn.r5.is_not(None)), "r20_filled": cnt(EventReturn.r20.is_not(None)), "r60_filled": cnt(EventReturn.r60.is_not(None)),
                "vol_ratio_filled": cnt(EventReturn.vol_ratio.is_not(None)), "disclosure_checked": cnt(EventReturn.near_disclosure.is_not(None)), "last_computed_at": s.scalar(select(func.max(EventReturn.computed_at))),
                "summaries": s.scalar(select(func.count()).select_from(Summary)) or 0}


@app.get("/v1/channels/ranking", response_model=ChannelRanking, tags=["summary"], operation_id="channel_ranking",
         summary="채널 랭킹 — 언급 뒤 수익률 기준 상·하위 (metric=excess_mean|mean|win_rate|asset_win_rate, 표본 min_n 이상만)")
def channel_ranking(horizon: int = Query(default=20, description="5 · 20 · 60"), metric: str = Query(default="excess_mean", pattern="^(excess_mean|mean|win_rate|asset_win_rate)$"),
                    min_n: int = Query(default=30, ge=1), min_assets: int = Query(default=10, ge=1, description="asset_win_rate 기준일 때 최소 언급 종목 수"),
                    stance: str = Query(default="all", pattern="^(all|bull|bear|neutral)$", description="제목 논조. 화면 기본은 bull"),
                    limit: int = Query(default=3, ge=1, le=20), s: Session = Depends(db.session)):
    rows = []
    pre = "" if stance == "all" else f"{stance}:"
    for sm in s.scalars(select(Summary).where(Summary.key.like(f"{pre}channel:%:{horizon}"))).all():
        v = sm.value
        if (v.get("n") or 0) < min_n or v.get(metric) is None:
            continue
        if metric == "asset_win_rate" and (v.get("assets_n") or 0) < min_assets:
            continue
        rows.append({"channel_id": sm.key[len(pre) + len("channel:"):-(len(str(horizon)) + 1)], "n": v["n"], "mean": v["mean"], "median": v["median"],
                     "win_rate": v["win_rate"], "excess_mean": v.get("excess_mean"), "excess_win_rate": v.get("excess_win_rate"),
                     "vol_ratio_median": v.get("vol_ratio_median"), "assets_n": v.get("assets_n"), "assets_up": v.get("assets_up"), "asset_win_rate": v.get("asset_win_rate")})
    rows.sort(key=lambda r: r[metric], reverse=True)
    return {"horizon": horizon, "metric": metric, "stance": stance, "min_n": min_n, "top": rows[:limit], "bottom": list(reversed(rows[-limit:])) if len(rows) > limit else [], "all": rows}


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


@app.get("/internal/sync-status", response_model=SyncStatus, tags=["ops"], operation_id="stats_sync_status",
         summary="비동기 계산(background=true) 의 진행 상태", dependencies=[InternalOnly])
def sync_status():
    return _job


@app.post("/internal/sync", response_model=SyncResult, tags=["ops"], operation_id="sync_stats",
          summary="새 언급의 수익률 계산 + 미완성 값 채우기 + 요약 갱신. background=true 면 202 로 바로 돌아오고 /internal/sync-status 로 확인 (Render 는 긴 요청을 끊는다)",
          dependencies=[InternalOnly], status_code=200)
def sync(background_tasks: BackgroundTasks,
         since_days: int = Query(default=130, le=2000, description="이 기간의 언급만 다시 계산 (최초 백필은 400). 60거래일이 채워지려면 약 90일이면 되므로 매일은 130일"),
         full: bool = Query(default=False, description="true 면 이미 60일까지 채워진 언급도 다시 계산(규칙이 바뀌었을 때)"),
         background: bool = Query(default=False, description="true 면 백그라운드 실행 (응답 즉시, 결과는 sync-status)")):
    if background:
        with _job_lock:
            if _job["state"] == "running":
                return {"events_added": 0, "events_updated": 0, "summaries": 0, "skipped": ["이미 실행 중 — /internal/sync-status 확인"]}
            _job.update({"state": "running", "started_at": datetime.utcnow(), "finished_at": None, "result": None, "error": None})
        background_tasks.add_task(_run_job, since_days, full)
        return {"events_added": 0, "events_updated": 0, "summaries": 0, "skipped": ["백그라운드 시작 — /internal/sync-status 확인"]}
    with db.SessionLocal() as s:
        return _sync(s, since_days, full)


def _run_job(since_days: int, full: bool):
    try:
        with db.SessionLocal() as s:
            res = _sync(s, since_days, full)
        _job.update({"state": "done", "finished_at": datetime.utcnow(), "result": res})
    except Exception as e:  # noqa: BLE001
        _job.update({"state": "failed", "finished_at": datetime.utcnow(), "error": str(e)[:300]})


def _sync(s: Session, since_days: int, full: bool) -> dict:
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
    to_insert, to_update = [], []
    complete = 0
    for m in ments:
        ev0 = existing.get(m["id"])
        if ev0 is not None and ev0.r60 is not None and not full:
            complete += 1; continue  # 60거래일까지 다 채워진 언급은 더 바뀌지 않는다 — 매일 배치가 2만 건을 다시 계산하지 않게
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
        vals = {"t0_date": fr["t0_date"], "t0_close": fr["t0_close"], "vol_ratio": fr["vol_ratio"], "stance": m.get("stance", "neutral"),
                "near_disclosure": _near(disc.get(m["asset_id"]), fr["t0_date"]) if m["asset_id"] in disc else None}
        for h in HORIZONS:
            vals[f"r{h}"] = fr[f"r{h}"]
            vals[f"x{h}"] = (fr[f"r{h}"] - br[f"r{h}"]) if fr[f"r{h}"] is not None and br.get(f"r{h}") is not None else None
        ev = existing.get(m["id"])
        if ev:
            if any(_differs(getattr(ev, k), v) for k, v in vals.items()):
                to_update.append({"id": ev.id, "computed_at": datetime.utcnow(), **vals}); updated += 1
        else:
            to_insert.append({"mention_id": m["id"], "asset_id": m["asset_id"], "channel_id": m["channel_id"], "market": a["market"],
                              "kind": "theme" if a.get("asset_type") == "theme" else "stock", "stance": m.get("stance", "neutral"), "benchmark_id": a.get("benchmark_id"),
                              "published_at": pub, "computed_at": datetime.utcnow(), **vals}); added += 1
    # 한 건씩이 아니라 묶어서 — Render 0.1 CPU 에서 1만 건 UPDATE 가 20분 → 수십 초
    from sqlalchemy import insert, update
    for i in range(0, len(to_insert), 2000):
        s.execute(insert(EventReturn), to_insert[i:i + 2000])
    for i in range(0, len(to_update), 2000):
        s.execute(update(EventReturn), to_update[i:i + 2000])
    s.flush()
    n = _rebuild_summaries(s)
    s.commit()
    memo_ttl.clear()
    return {"events_added": added, "events_updated": updated, "summaries": n, "skipped": ([f"이미 완료된 언급 {complete}건 건너뜀"] if complete else []) + skipped[:50]}


def _differs(a, b) -> bool:
    """float 은 반올림 차이로 매일 '바뀜' 이 되지 않게 소수 6자리에서 비교."""
    if isinstance(a, float) or isinstance(b, float):
        return a is None or b is None or abs(a - b) > 1e-6
    return a != b


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
            EventReturn.vol_ratio, EventReturn.near_disclosure, EventReturn.stance)
    groups: dict[str, list[tuple]] = {"overall": []}
    for row in s.execute(select(*cols)).yield_per(5000):
        market, kind, channel_id, asset_id, stance = row[0], row[1], row[2], row[3], row[12]
        payload = row[4:12]
        for pre in ("", f"{stance}:"):  # 전체 키와 논조별 키(bull:·bear:·neutral:) 둘 다
            if kind == "theme":
                groups.setdefault(f"{pre}kind:theme", []).append(payload)
            else:
                groups.setdefault(f"{pre}overall", []).append(payload)
                groups.setdefault(f"{pre}kind:stock", []).append(payload)
                groups.setdefault(f"{pre}market:{market}", []).append(payload)
                groups.setdefault(f"{pre}channel:{channel_id}", []).append(payload)
            groups.setdefault(f"{pre}asset:{asset_id}", []).append(payload)
    idx = {5: (0, 3), 20: (1, 4), 60: (2, 5)}  # (r 위치, x 위치) in payload
    # 채널별 "언급한 종목 n개 중 평균 수익률이 양(+)인 종목 비중" — 언급 건 기준 상승 확률과 다른, 종목 기준 지표
    by_channel_asset: dict[str, dict[str, list]] = {}  # 키: "" 또는 "bull:" 등 접두사 + channel_id
    for row in s.execute(select(EventReturn.channel_id, EventReturn.asset_id, EventReturn.r5, EventReturn.r20, EventReturn.r60, EventReturn.stance).where(EventReturn.kind != "theme")).yield_per(5000):
        for pre in ("", f"{row[5]}:"):
            by_channel_asset.setdefault(pre + row[0], {}).setdefault(row[1], []).append(row[2:5])
    n = 0
    for key, evs in groups.items():
        for h in HORIZONS:
            ri, xi = idx[h]
            val = summarize([{"r": e[ri], "x": e[xi], "v": e[6], "d": e[7]} for e in evs], h)
            val["scope"] = key
            if "channel:" in key:
                per_asset = by_channel_asset.get(key.replace("channel:", "", 1) if key.startswith("channel:") else key.split("channel:")[0] + key.split("channel:")[1], {})
                means = []
                for rows_ in per_asset.values():
                    rs = [r_[ri] for r_ in rows_ if r_[ri] is not None]
                    if rs:
                        means.append(sum(rs) / len(rs))
                val["assets_n"] = len(means)
                val["assets_up"] = sum(1 for m_ in means if m_ > 0)
                val["asset_win_rate"] = round(val["assets_up"] / len(means), 4) if means else None
            k = f"{key}:{h}"
            row = s.get(Summary, k)
            if row:
                row.value = val; row.updated_at = datetime.utcnow()
            else:
                s.add(Summary(key=k, value=val))
            n += 1
        evs.clear()
    return n
