from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from routine_common import Database

db = Database("backtest", schema="backtest")
Base = db.Base


class Run(Base):
    """백테스트 실행 한 건. 입력(params)과 결과(result)를 JSON 으로 남겨 재현 가능하게 한다."""

    __tablename__ = "runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(20), index=True)  # dca · purchase-day
    params: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
