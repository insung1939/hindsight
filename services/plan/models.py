from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from routine_common import Database

db = Database("plan", schema="plan")
Base = db.Base


class Instruction(Base):
    """월간 매수 지시서. 한 포트폴리오·한 달에 하나."""

    __tablename__ = "instructions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    portfolio_id: Mapped[int] = mapped_column(Integer, index=True)
    month: Mapped[str] = mapped_column(String(7), index=True)  # YYYY-MM
    budget_krw: Mapped[float] = mapped_column(Float)
    total_value_krw: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class InstructionItem(Base):
    __tablename__ = "instruction_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instruction_id: Mapped[int] = mapped_column(ForeignKey("instructions.id"), index=True)
    asset_id: Mapped[str] = mapped_column(String(40))
    account_id: Mapped[int] = mapped_column(Integer)
    target_weight: Mapped[float] = mapped_column(Float)
    current_weight: Mapped[float] = mapped_column(Float)
    amount_krw: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3))
    fx_rate: Mapped[float] = mapped_column(Float)
    quantity: Mapped[float] = mapped_column(Float)
