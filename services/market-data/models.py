from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from hs_common import Database

db = Database("market-data", schema="market")
Base = db.Base


class Asset(Base):
    """자산 마스터 겸 종목 사전. asset_id 는 '시장:심볼' (KRX:005930, US:NVDA, CRYPTO:KRW-BTC, INDEX:KOSPI).
    aliases 는 제목에서 이 자산을 가리키는 표현들("삼전", "엔비디아"). mentions 서비스가 사전으로 쓴다.
    tracked=True 인 자산만 시세를 매일 수집한다(사전에는 있지만 아무도 언급하지 않은 종목까지 긁지 않는다)."""

    __tablename__ = "assets"
    asset_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    market: Mapped[str] = mapped_column(String(10), index=True)  # KRX · US · CRYPTO · INDEX
    symbol: Mapped[str] = mapped_column(String(30))  # 종목코드 · 티커 · 업비트 마켓 · 지수 심볼
    name: Mapped[str] = mapped_column(String(100), index=True)
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    currency: Mapped[str] = mapped_column(String(3))
    asset_type: Mapped[str] = mapped_column(String(10))  # stock · etf · crypto · index
    source: Mapped[str] = mapped_column(String(30))  # 시세 어댑터: datagokr · yahoo · upbit
    yahoo_symbol: Mapped[str | None] = mapped_column(String(30), nullable=True)  # 국내 종목 Yahoo 대체 심볼(005930.KS)
    benchmark_id: Mapped[str | None] = mapped_column(String(40), nullable=True)  # 초과수익 기준 지수
    tracked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    curated: Mapped[bool] = mapped_column(Boolean, default=False)  # 팀이 손으로 넣은 종목(시드). 자동 수집(업비트·DART)은 False
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Price(Base):
    """일별 종가 이력."""

    __tablename__ = "prices"
    __table_args__ = (UniqueConstraint("asset_id", "trade_date", name="uq_price_asset_date"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[str] = mapped_column(String(40), index=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    close: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3))
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
