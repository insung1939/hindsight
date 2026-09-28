"""mentions — "이 영상이 어떤 종목을 말했나?" 에 답한다. youtube(영상)와 market-data(사전)를 부른다.
새로 언급된 종목은 market-data 에 track 을 켜서 시세 수집이 시작되게 한다."""
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from hs_common import InternalOnly, ServiceClient, create_app
from hs_common.settings import env
from matcher import build_terms, match
from models import Mention, SyncState, Unmatched, db

# 설명란까지 볼지. 설명란은 채널 링크·광고 문구("네이버 카페", "link") 때문에 오탐이 많아 기본은 제목만.
MATCH_FIELDS = ("title", "description") if env("MATCH_DESCRIPTION", "false") == "true" else ("title",)

app = create_app("mentions", "힌드사이트 mentions", "0.1.0",
                 "영상 제목·설명에서 종목을 찾아 언급 사실을 저장한다. 사전은 market-data, 영상은 youtube 에서 받는다.")
youtube = ServiceClient("youtube", timeout=60)
market = ServiceClient("market-data", timeout=60)


@app.on_event("startup")
def _startup():
    db.create_all()


class MentionOut(BaseModel):
    id: int
    video_id: str
    channel_id: str
    asset_id: str
    matched_text: str
    field: str
    confidence: float
    published_at: datetime
    view_count: int | None = None
    model_config = {"from_attributes": True}


class ListMentions(BaseModel):
    items: list[MentionOut]
    next_cursor: str | None = None


class TrendingItem(BaseModel):
    asset_id: str
    mentions: int
    prev_mentions: int
    channels: int
    views: int
    last_mentioned_at: datetime


class ListTrending(BaseModel):
    items: list[TrendingItem]
    next_cursor: str | None = None
    days: int


class UnmatchedOut(BaseModel):
    video_id: str
    channel_id: str
    title: str
    published_at: datetime
    model_config = {"from_attributes": True}


class ListUnmatched(BaseModel):
    items: list[UnmatchedOut]
    next_cursor: str | None = None


class CoverageOut(BaseModel):
    videos_seen: int
    videos_matched: int
    match_rate: float
    mentions: int
    assets: int
    last_video_at: str | None


class SyncResult(BaseModel):
    videos_scanned: int
    mentions_added: int
    unmatched_added: int
    assets_tracked: int
    skipped: list[str]


@app.get("/v1/mentions", response_model=ListMentions, tags=["mentions"], operation_id="list_mentions", summary="언급 목록")
def list_mentions(asset_id: str | None = None, channel_id: str | None = None, since: datetime | None = None,
                  limit: int = Query(default=500, le=5000), s: Session = Depends(db.session)):
    q = select(Mention)
    if asset_id:
        q = q.where(Mention.asset_id == asset_id)
    if channel_id:
        q = q.where(Mention.channel_id == channel_id)
    if since:
        q = q.where(Mention.published_at >= since)
    return {"items": s.scalars(q.order_by(Mention.published_at.desc()).limit(limit)).all(), "next_cursor": None}


@app.get("/v1/mentions/trending", response_model=ListTrending, tags=["mentions"], operation_id="trending_mentions",
         summary="최근 N일 언급 급증 종목 (직전 N일 대비)")
def trending(days: int = Query(default=7, ge=1, le=90), limit: int = Query(default=20, le=100), s: Session = Depends(db.session)):
    now = datetime.utcnow()
    cur_from, prev_from = now - timedelta(days=days), now - timedelta(days=2 * days)
    cur = s.execute(select(Mention.asset_id, func.count(), func.count(func.distinct(Mention.channel_id)),
                           func.coalesce(func.sum(Mention.view_count), 0), func.max(Mention.published_at))
                    .where(Mention.published_at >= cur_from).group_by(Mention.asset_id)).all()
    prev = dict(s.execute(select(Mention.asset_id, func.count()).where(Mention.published_at >= prev_from, Mention.published_at < cur_from)
                          .group_by(Mention.asset_id)).all())
    items = [{"asset_id": a, "mentions": n, "prev_mentions": prev.get(a, 0), "channels": c, "views": int(v), "last_mentioned_at": last}
             for a, n, c, v, last in cur]
    items.sort(key=lambda x: (x["mentions"] - x["prev_mentions"], x["mentions"], x["views"]), reverse=True)
    return {"items": items[:limit], "next_cursor": None, "days": days}


@app.get("/v1/unmatched", response_model=ListUnmatched, tags=["mentions"], operation_id="list_unmatched",
         summary="종목을 못 잡은 영상 제목 (별칭 사전 보강용)")
def list_unmatched(limit: int = Query(default=50, le=500), s: Session = Depends(db.session)):
    return {"items": s.scalars(select(Unmatched).order_by(Unmatched.published_at.desc()).limit(limit)).all(), "next_cursor": None}


@app.get("/v1/coverage", response_model=CoverageOut, tags=["mentions"], operation_id="get_coverage", summary="매칭 성공률 (데이터 페이지용)")
def coverage(s: Session = Depends(db.session)):
    matched = s.scalar(select(func.count(func.distinct(Mention.video_id)))) or 0
    unmatched = s.scalar(select(func.count()).select_from(Unmatched)) or 0
    seen = matched + unmatched
    last = s.get(SyncState, "last_video_at")
    return {"videos_seen": seen, "videos_matched": matched, "match_rate": (matched / seen) if seen else 0.0,
            "mentions": s.scalar(select(func.count()).select_from(Mention)) or 0,
            "assets": s.scalar(select(func.count(func.distinct(Mention.asset_id)))) or 0,
            "last_video_at": last.value if last else None}


@app.post("/internal/sync", response_model=SyncResult, tags=["ops"], operation_id="sync_mentions",
          summary="youtube 의 새 영상을 market-data 사전으로 매칭 (full=true 면 처음부터 다시)", dependencies=[InternalOnly])
def sync(full: bool = False, s: Session = Depends(db.session)):
    d = market.get("/v1/dictionary")
    terms = build_terms(d["items"], set(d["ambiguous_names"]))
    crypto_channels = {c["channel_id"] for c in youtube.get("/v1/channels")["items"] if c["category"] == "crypto"}
    state = s.get(SyncState, "last_video_at")
    cursor = None if (full or not state) else state.value
    if full:
        s.query(Mention).delete(); s.query(Unmatched).delete()
    scanned, added, un_added, tracked, skipped = 0, 0, 0, 0, []
    newly_tracked: set[str] = set()
    last_at = cursor
    while True:
        page = youtube.get("/v1/videos", cursor=cursor, limit=500)
        videos = page["items"]
        if not videos:
            break
        for v in videos:
            scanned += 1
            hits = {}
            for field in MATCH_FIELDS:
                for aid, txt, conf in match(v.get(field) or "", terms, crypto_channel=v["channel_id"] in crypto_channels):
                    if aid not in hits or conf > hits[aid][1]:
                        hits[aid] = (txt, conf, field)
            pub = datetime.fromisoformat(v["published_at"])
            if not hits:
                if not s.get(Unmatched, v["video_id"]):
                    s.add(Unmatched(video_id=v["video_id"], channel_id=v["channel_id"], title=v["title"], published_at=pub))
                    un_added += 1
            for aid, (txt, conf, field) in hits.items():
                exists = s.scalar(select(Mention).where(Mention.video_id == v["video_id"], Mention.asset_id == aid))
                if exists:
                    continue
                s.add(Mention(video_id=v["video_id"], channel_id=v["channel_id"], asset_id=aid, matched_text=txt,
                              field=field, confidence=conf, published_at=pub, view_count=v.get("view_count")))
                added += 1
                newly_tracked.add(aid)
            last_at = v["published_at"]
        cursor = page.get("next_cursor")
        if not cursor:
            break
    # 새로 언급된 종목의 시세 수집을 켠다 (market-data 는 tracked 인 것만 긁는다)
    for aid in newly_tracked:
        try:
            r = market.post(f"/v1/assets/{aid}/track")
            tracked += 1
        except HTTPException as e:
            skipped.append(f"track {aid}: {e.detail}")
    if last_at:
        st = s.get(SyncState, "last_video_at") or SyncState(key="last_video_at", value=last_at)
        st.value = last_at
        s.merge(st)
    s.commit()
    return {"videos_scanned": scanned, "mentions_added": added, "unmatched_added": un_added,
            "assets_tracked": tracked, "skipped": skipped}
