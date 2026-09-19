from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from routine_common import Database

db = Database("market-data", schema="market")
Base = db.Base


class Asset(Base):
    """자산 마스터. asset_id 는 '시장:심볼' 형식(예: KRX:005930, US:SPY, CRYPTO:KRW-BTC)."""

    __tablename__ = "assets"
    asset_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    market: Mapped[str] = mapped_column(String(10), index=True)  # KRX · US · HK · CRYPTO
    symbol: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(100))
    currency: Mapped[str] = mapped_column(String(3))  # KRW · USD · HKD
    asset_type: Mapped[str] = mapped_column(String(10))  # stock · etf · crypto
    expense_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)  # ETF 총보수(연, %)
    source: Mapped[str] = mapped_column(String(30))  # 시세 어댑터 이름


class Price(Base):
    """일별 종가 이력. 백테스트가 필요로 하므로 '현재가'가 아니라 이력으로 쌓는다."""

    __tablename__ = "prices"
    __table_args__ = (UniqueConstraint("asset_id", "trade_date", name="uq_price_asset_date"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[str] = mapped_column(String(40), index=True)
    trade_date: Mapped[date] = mapped_column(Date, index=True)
    close: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3))
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FxRate(Base):
    """환율 이력. base 1단위 = rate quote (예: USD→KRW 1350.5)."""

    __tablename__ = "fx_rates"
    __table_args__ = (UniqueConstraint("base", "quote", "rate_date", name="uq_fx_pair_date"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    base: Mapped[str] = mapped_column(String(3), index=True)
    quote: Mapped[str] = mapped_column(String(3), index=True)
    rate_date: Mapped[date] = mapped_column(Date, index=True)
    rate: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(30))
