"""youtube — "어떤 채널이 언제 무슨 영상을 올렸나?" 에 답한다. 아무도 부르지 않는 수집 전용 최하층.
채널은 팀이 /v1/channels 로 등록한다(핸들만 주면 API 로 id 를 찾는다). 영상은 /internal/sync 가 매일 받는다."""
import json
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import collectors
from hs_common import InternalOnly, create_app
from models import Channel, Video, db

app = create_app("youtube", "하인드사이트 youtube", "0.1.0",
                 "추적 채널과 영상 메타데이터(제목·설명·게시일·조회수). 출처: YouTube Data API v3.")


@app.on_event("startup")
def _startup():
    db.create_all()


# ── 스키마 ──────────────────────────────────────────────
class ChannelIn(BaseModel):
    handle: str = Field(description="@핸들 (채널 페이지 주소의 @ 뒤)", examples=["@sampro_tv"])
    category: str = Field(pattern="^(stock|crypto)$")


class ChannelOut(BaseModel):
    channel_id: str
    anon_code: str
    title: str  # 2026-10-07 팀 결정: 채널 실명을 보여준다 (학습용 통계이며 추천이 아님을 화면에 고정 고지)
    handle: str
    category: str
    subscriber_count: int | None = None
    tracked: bool
    added_at: datetime
    model_config = {"from_attributes": True}


class VideoOut(BaseModel):
    video_id: str
    channel_id: str
    title: str
    description: str
    published_at: datetime
    view_count: int | None = None
    model_config = {"from_attributes": True}


class ListChannels(BaseModel):
    items: list[ChannelOut]
    next_cursor: str | None = None


class ListVideos(BaseModel):
    items: list[VideoOut]
    next_cursor: str | None = None


class Coverage(BaseModel):
    channels: int
    videos: int
    first_published: datetime | None
    last_published: datetime | None
    by_category: dict[str, int]


class SyncResult(BaseModel):
    videos_added: int
    channels_synced: int
    skipped: list[str]


# ── 채널 ────────────────────────────────────────────────
def _next_anon(s: Session) -> str:
    """A…Z 다음은 AA, AB … (채널 51개도 두 글자면 충분)."""
    n = s.scalar(select(func.count()).select_from(Channel)) or 0
    return chr(ord("A") + n) if n < 26 else chr(ord("A") + n // 26 - 1) + chr(ord("A") + n % 26)


@app.post("/v1/channels", response_model=ChannelOut, status_code=201, tags=["channels"], operation_id="add_channel",
          summary="채널 등록 (핸들 → YouTube API 로 id 조회)")
def add_channel(body: ChannelIn, s: Session = Depends(db.session)):
    info = collectors.channel_by_handle(body.handle)
    if s.get(Channel, info["channel_id"]):
        raise HTTPException(409, "이미 등록된 채널")
    ch = Channel(**info, category=body.category, anon_code=_next_anon(s))
    s.add(ch); s.commit(); s.refresh(ch)
    return ch


@app.get("/v1/channels", response_model=ListChannels, tags=["channels"], operation_id="list_channels", summary="채널 목록 (실명·핸들·구독자)")
def list_channels(s: Session = Depends(db.session)):
    return {"items": s.scalars(select(Channel).order_by(Channel.anon_code)).all(), "next_cursor": None}


# ── 영상 ────────────────────────────────────────────────
@app.get("/v1/videos", response_model=ListVideos, tags=["videos"], operation_id="list_videos",
         summary="영상 목록 (since 이후, 게시일 오름차순). mentions 가 매일 새 영상을 받아간다")
def list_videos(since: datetime | None = None, channel_id: str | None = None,
                cursor: str | None = Query(default=None, description="마지막으로 받은 video_id 의 published_at ISO"),
                limit: int = Query(default=500, le=2000), s: Session = Depends(db.session)):
    q = select(Video)
    if since:
        q = q.where(Video.published_at >= since)
    if cursor:
        q = q.where(Video.published_at > datetime.fromisoformat(cursor))
    if channel_id:
        q = q.where(Video.channel_id == channel_id)
    rows = s.scalars(q.order_by(Video.published_at).limit(limit + 1)).all()
    nxt = rows[limit - 1].published_at.isoformat() if len(rows) > limit else None
    return {"items": rows[:limit], "next_cursor": nxt}


@app.get("/v1/videos/{video_id}", response_model=VideoOut, tags=["videos"], operation_id="get_video", summary="영상 하나")
def get_video(video_id: str, s: Session = Depends(db.session)):
    v = s.get(Video, video_id)
    if not v:
        raise HTTPException(404, f"영상 {video_id} 없음")
    return v


@app.get("/v1/coverage", response_model=Coverage, tags=["videos"], operation_id="get_coverage", summary="수집 현황 (데이터 페이지용)")
def get_coverage(s: Session = Depends(db.session)):
    by = dict(s.execute(select(Channel.category, func.count(Video.video_id)).join(Video, Video.channel_id == Channel.channel_id)
                        .group_by(Channel.category)).all())
    return {"channels": s.scalar(select(func.count()).select_from(Channel)) or 0,
            "videos": s.scalar(select(func.count()).select_from(Video)) or 0,
            "first_published": s.scalar(select(func.min(Video.published_at))),
            "last_published": s.scalar(select(func.max(Video.published_at))), "by_category": by}


# ── 수집 ────────────────────────────────────────────────
@app.post("/internal/sync", response_model=SyncResult, tags=["ops"], operation_id="sync_youtube",
          summary="추적 채널의 새 영상 수집 (days 만큼 거슬러; 최초 백필은 days=365)", dependencies=[InternalOnly])
def sync(days: int = Query(default=7, le=730), s: Session = Depends(db.session)):
    since = datetime.utcnow() - timedelta(days=days)
    added, synced, skipped = 0, 0, []
    for ch in s.scalars(select(Channel).where(Channel.tracked == True)).all():  # noqa: E712
        try:
            items = collectors.uploads_since(ch.uploads_playlist_id, since)
            new = [it for it in items if not s.get(Video, it["video_id"])]
            views = collectors.view_counts([it["video_id"] for it in new]) if new else {}
            for it in new:
                s.add(Video(channel_id=ch.channel_id, view_count=views.get(it["video_id"]), **it))
            added += len(new); synced += 1
        except HTTPException as e:
            skipped.append(f"{ch.anon_code}: {e.detail}")
            if e.status_code == 409:  # 키 없음 — 더 돌 필요 없다
                break
        except Exception as e:
            skipped.append(f"{ch.anon_code}: {e}")
    s.commit()
    return {"videos_added": added, "channels_synced": synced, "skipped": skipped}


@app.post("/internal/load-fixture", response_model=SyncResult, tags=["ops"], operation_id="load_fixture",
          summary="키 없이 개발할 때 쓰는 샘플 데이터 (fixtures/sample.json). 실제 채널·영상이 아니다", dependencies=[InternalOnly])
def load_fixture(s: Session = Depends(db.session)):
    path = Path(__file__).parent / "fixtures" / "sample.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    added = 0
    for ch in data["channels"]:
        if not s.get(Channel, ch["channel_id"]):
            s.add(Channel(**ch))
    s.flush()
    for v in data["videos"]:
        if not s.get(Video, v["video_id"]):
            v = {**v, "published_at": datetime.fromisoformat(v["published_at"])}
            s.add(Video(**v)); added += 1
    s.commit()
    return {"videos_added": added, "channels_synced": len(data["channels"]), "skipped": ["샘플 데이터 — 실제 채널·영상 아님"]}
