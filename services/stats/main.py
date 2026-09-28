"""stats — "언급 뒤 주가는 어땠나?" 에 답한다. mentions(언급)와 market-data(시세)를 부른다.
계산은 /internal/sync 배치에서 끝내 두고, 조회 API 는 저장된 결과와 요약 캐시만 읽는다(Render 콜드 스타트 대비)."""
from datetime import date, datetime, timedelta

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from engine import HORIZONS, forward_returns, summarize
from hs_common import InternalOnly, ServiceClient, create_app
from models import EventReturn, Summary, db

app = create_app("stats", "힌드사이트 stats", "0.1.0", "언급 뒤 5·20·60 거래일 수익률과 벤치마크 대비 초과수익. 채널은 익명 집계.")
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
    published_at: datetime
    t0_date: date | None
    t0_close: float | None
    r5: float | None
    r20: float | None
    r60: float | None
    x5: float | None
    x20: float | None
    x60: float | None
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
         summary="전체 분포 (scope=overall | market:KRX | market:US | market:CRYPTO)")
def get_summary(scope: str = "overall", horizon: int = Query(default=20, description="5 · 20 · 60"), s: Session = Depends(db.session)):
    return _summary(s, f"{scope}:{horizon}")


@app.get("/v1/summaries", response_model=ListSummaries, tags=["summary"], operation_id="list_summaries",
         summary="요약 전부 (prefix 로 필터: overall · market · channel · asset)")
def list_summaries(prefix: str | None = None, s: Session = Depends(db.session)):
    q = select(Summary)
    if prefix:
        q = q.where(Summary.key.like(f"{prefix}%"))
    return {"items": s.scalars(q.order_by(Summary.key)).all(), "next_cursor": None}


@app.get("/v1/assets/{asset_id}/events", response_model=ListEvents, tags=["events"], operation_id="asset_events",
         summary="종목 하나의 언급별 이후 수익률 (타임라인 화면)")
def asset_events(asset_id: str, s: Session = Depends(db.session)):
    rows = s.scalars(select(EventReturn).where(EventReturn.asset_id == asset_id).order_by(EventReturn.published_at)).all()
    return {"items": rows, "next_cursor": None}


@app.get("/v1/channels/{channel_id}/events", response_model=ListEvents, tags=["events"], operation_id="channel_events",
         summary="채널 하나의 언급별 이후 수익률 (익명 코드로만 노출)")
def channel_events(channel_id: str, s: Session = Depends(db.session)):
    rows = s.scalars(select(EventReturn).where(EventReturn.channel_id == channel_id).order_by(EventReturn.published_at.desc())).all()
    return {"items": rows, "next_cursor": None}


@app.post("/internal/sync", response_model=SyncResult, tags=["ops"], operation_id="sync_stats",
          summary="새 언급의 수익률 계산 + 미완성 값 채우기 + 요약 갱신", dependencies=[InternalOnly])
def sync(since_days: int = Query(default=400, le=2000), s: Session = Depends(db.session)):
    since = datetime.utcnow() - timedelta(days=since_days)
    ments = mentions.get("/v1/mentions", since=since.isoformat(), limit=5000)["items"]
    existing = {e.mention_id: e for e in s.scalars(select(EventReturn).where(EventReturn.published_at >= since)).all()}
    asset_ids = sorted({m["asset_id"] for m in ments})
    if not asset_ids:
        return {"events_added": 0, "events_updated": 0, "summaries": 0, "skipped": ["언급 없음"]}
    assets = {a["asset_id"]: a for a in market.get("/v1/assets", limit=5000)["items"]}
    bench_ids = sorted({assets[a]["benchmark_id"] for a in asset_ids if a in assets and assets[a].get("benchmark_id")})
    series = _load_series(asset_ids + bench_ids, since.date() - timedelta(days=10))
    added, updated, skipped = 0, 0, []
    for m in ments:
        a = assets.get(m["asset_id"])
        if not a:
            skipped.append(f"{m['asset_id']}: 사전에 없음"); continue
        ser = series.get(m["asset_id"])
        if not ser:
            skipped.append(f"{m['asset_id']}: 시세 없음(아직 수집 전)"); continue
        pub = datetime.fromisoformat(m["published_at"])
        fr = forward_returns(ser, pub.date())
        bench = series.get(a.get("benchmark_id") or "")
        br = forward_returns(bench, pub.date()) if bench else {f"r{h}": None for h in HORIZONS}
        vals = {"t0_date": fr["t0_date"], "t0_close": fr["t0_close"]}
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
                              benchmark_id=a.get("benchmark_id"), published_at=pub, **vals)); added += 1
    s.flush()
    n = _rebuild_summaries(s)
    s.commit()
    return {"events_added": added, "events_updated": updated, "summaries": n, "skipped": skipped[:50]}


def _load_series(ids: list[str], from_date: date) -> dict[str, list[tuple[date, float]]]:
    out = {}
    for i in range(0, len(ids), 100):
        chunk = ids[i:i + 100]
        r = market.get("/v1/prices", asset_ids=",".join(chunk), **{"from": str(from_date)})
        for sr in r["series"]:
            out[sr["asset_id"]] = [(date.fromisoformat(d), c) for d, c in sr["points"]]
    return out


def _rebuild_summaries(s: Session) -> int:
    rows = s.scalars(select(EventReturn)).all()
    groups: dict[str, list] = {"overall": rows}
    for e in rows:
        groups.setdefault(f"market:{e.market}", []).append(e)
        groups.setdefault(f"channel:{e.channel_id}", []).append(e)
        groups.setdefault(f"asset:{e.asset_id}", []).append(e)
    n = 0
    for key, evs in groups.items():
        for h in HORIZONS:
            val = summarize([{"r": getattr(e, f"r{h}"), "x": getattr(e, f"x{h}")} for e in evs], h)
            val["scope"] = key
            k = f"{key}:{h}"
            row = s.get(Summary, k)
            if row:
                row.value = val; row.updated_at = datetime.utcnow()
            else:
                s.add(Summary(key=k, value=val))
            n += 1
    return n
