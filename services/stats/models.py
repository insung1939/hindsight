from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from hs_common import Database

db = Database("stats", schema="stats")
Base = db.Base


class EventReturn(Base):
    """언급 하나의 이후 수익률. T0 = 게시일 당일 또는 다음 거래일 종가. r_n = P(T0+n거래일)/P(T0) − 1.
    x_n = r_n − 벤치마크 같은 구간 수익률(초과수익). 아직 n일이 안 지났으면 null 로 두고 다음 sync 에서 채운다."""

    __tablename__ = "event_returns"
    __table_args__ = (UniqueConstraint("mention_id", name="uq_event_mention"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mention_id: Mapped[int] = mapped_column(Integer, index=True)
    asset_id: Mapped[str] = mapped_column(String(40), index=True)
    channel_id: Mapped[str] = mapped_column(String(40), index=True)
    market: Mapped[str] = mapped_column(String(10), index=True)
    kind: Mapped[str] = mapped_column(String(10), default="stock", index=True)  # stock(종목·코인) · theme(업종·테마 ETF)
    benchmark_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    t0_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    t0_close: Mapped[float | None] = mapped_column(Float, nullable=True)
    r5: Mapped[float | None] = mapped_column(Float, nullable=True)
    r20: Mapped[float | None] = mapped_column(Float, nullable=True)
    r60: Mapped[float | None] = mapped_column(Float, nullable=True)
    x5: Mapped[float | None] = mapped_column(Float, nullable=True)
    x20: Mapped[float | None] = mapped_column(Float, nullable=True)
    x60: Mapped[float | None] = mapped_column(Float, nullable=True)
    vol_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)  # 언급 뒤 5일 평균 거래량 ÷ 언급 전 20일 평균
    near_disclosure: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # 사건일 ±3일에 DART 주요 공시(실적·계약·자금조달·주요사항)가 있었나 (국내 종목만, 공시 데이터 없으면 null)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Summary(Base):
    """집계 캐시. key 예: overall:20(종목·코인, 테마 제외), market:KRX:20, kind:theme:20, channel:UC…:20, asset:KRX:005930:20"""

    __tablename__ = "summaries"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
