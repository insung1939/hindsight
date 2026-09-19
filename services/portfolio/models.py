from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from routine_common import Database

db = Database("portfolio", schema="portfolio")
Base = db.Base


class Portfolio(Base):
    """사용자 1명 = 포트폴리오 1개(프로토타입). 로그인은 구상 단계라 owner 문자열로 구분한다."""

    __tablename__ = "portfolios"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner: Mapped[str] = mapped_column(String(50), index=True)
    name: Mapped[str] = mapped_column(String(100))
    base_currency: Mapped[str] = mapped_column(String(3), default="KRW")
    monthly_budget: Mapped[float] = mapped_column(Float, default=0)  # 월 적립액(원)
    buy_day: Mapped[int] = mapped_column(Integer, default=1)  # 매수일(1~28)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Account(Base):
    """계좌. account_type: general · isa · pension · exchange"""

    __tablename__ = "accounts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    account_type: Mapped[str] = mapped_column(String(10))
    broker: Mapped[str | None] = mapped_column(String(50), nullable=True)


class Holding(Base):
    __tablename__ = "holdings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    asset_id: Mapped[str] = mapped_column(String(40), index=True)  # market-data 의 asset_id
    quantity: Mapped[float] = mapped_column(Float)
    avg_cost: Mapped[float | None] = mapped_column(Float, nullable=True)  # 자산 통화 기준 평단


class Rule(Base):
    """적립 규칙: 이 자산을 이 계좌에 목표 비중만큼."""

    __tablename__ = "rules"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    asset_id: Mapped[str] = mapped_column(String(40))
    target_weight: Mapped[float] = mapped_column(Float)  # 0~1


class Execution(Base):
    """실행 기록. status: done(지시대로) · skipped(건너뜀) · extra(임의 추가매수) · sell(매도)"""

    __tablename__ = "executions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id"), index=True)
    instruction_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # plan 서비스의 지시서 id
    asset_id: Mapped[str] = mapped_column(String(40))
    executed_on: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(10))
    amount_krw: Mapped[float] = mapped_column(Float, default=0)
    quantity: Mapped[float] = mapped_column(Float, default=0)
    note: Mapped[str | None] = mapped_column(String(200), nullable=True)
