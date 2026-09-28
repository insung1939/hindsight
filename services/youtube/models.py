from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from hs_common import Database

db = Database("youtube", schema="yt")
Base = db.Base


class Channel(Base):
    """추적 채널. anon_code 는 화면·통계에서 쓰는 익명 코드(A, B, C …). 실명(title)은 데이터 페이지에도 내지 않는다."""

    __tablename__ = "channels"
    channel_id: Mapped[str] = mapped_column(String(40), primary_key=True)  # UC…
    handle: Mapped[str] = mapped_column(String(100))  # @삼프로TV
    title: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(10))  # stock · crypto
    anon_code: Mapped[str] = mapped_column(String(4), unique=True)
    uploads_playlist_id: Mapped[str] = mapped_column(String(40))
    subscriber_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tracked: Mapped[bool] = mapped_column(Boolean, default=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Video(Base):
    """영상 메타데이터만 저장한다(제목·설명·게시일·조회수). 자막·댓글은 수집하지 않는다."""

    __tablename__ = "videos"
    video_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    channel_id: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")
    published_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    view_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
