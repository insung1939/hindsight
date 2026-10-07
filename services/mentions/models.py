from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from hs_common import Database

db = Database("mentions", schema="mentions")
Base = db.Base


class Mention(Base):
    """영상 하나가 종목 하나를 언급한 사실. 같은 영상·종목은 한 번만."""

    __tablename__ = "mentions"
    __table_args__ = (UniqueConstraint("video_id", "asset_id", name="uq_mention_video_asset"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[str] = mapped_column(String(20), index=True)
    channel_id: Mapped[str] = mapped_column(String(40), index=True)
    asset_id: Mapped[str] = mapped_column(String(40), index=True)
    matched_text: Mapped[str] = mapped_column(String(100))  # 제목에서 실제로 잡힌 문자열
    field: Mapped[str] = mapped_column(String(12))  # title · description
    confidence: Mapped[float] = mapped_column(Float)  # 정식 이름 1.0 · 별칭 0.8
    stance: Mapped[str] = mapped_column(String(8), default="neutral", index=True)  # 제목 논조: bull · bear · neutral
    stance_words: Mapped[str] = mapped_column(String(100), default="")  # 논조를 판정한 단어들
    published_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    view_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Unmatched(Base):
    """종목을 하나도 못 잡은 영상. 별칭 사전 보강의 재료이자 데이터 페이지의 '매칭 성공률' 근거."""

    __tablename__ = "unmatched"
    video_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    channel_id: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(300))
    published_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class SyncState(Base):
    __tablename__ = "sync_state"
    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    value: Mapped[str] = mapped_column(String(100))
