from datetime import date

from sqlalchemy import Date, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from routine_common import Database

db = Database("income", schema="income")
Base = db.Base


class Distribution(Base):
    """배당·분배금 이벤트 하나. amount_per_unit 은 1주(1좌)당 금액, 자산 통화 기준."""

    __tablename__ = "distributions"
    __table_args__ = (UniqueConstraint("asset_id", "ex_date", name="uq_dist_asset_exdate"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[str] = mapped_column(String(40), index=True)
    ex_date: Mapped[date] = mapped_column(Date, index=True)  # 배당락일(기준일)
    pay_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    amount_per_unit: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3))
    kind: Mapped[str] = mapped_column(String(10), default="cash")  # cash · stock
    source: Mapped[str] = mapped_column(String(30))  # dart · issuer-crawl · manual
