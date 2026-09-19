"""DATABASE_URL 하나로 SQLite(로컬) ↔ PostgreSQL/Supabase(배포) 전환. 서비스마다 자기 스키마만 쓴다."""
from collections.abc import Iterator

from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .settings import env


class Database:
    def __init__(self, service_name: str, schema: str):
        self.url = env("DATABASE_URL", f"sqlite:///./{service_name}.db") or ""
        self.is_sqlite = self.url.startswith("sqlite")
        # SQLite 는 스키마가 없으므로 PostgreSQL 일 때만 스키마를 붙인다.
        self.schema = None if self.is_sqlite else schema
        connect_args = {"check_same_thread": False} if self.is_sqlite else {}
        self.engine = create_engine(self.url, connect_args=connect_args, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        metadata = MetaData(schema=self.schema)

        class Base(DeclarativeBase):
            pass

        Base.metadata = metadata
        self.Base = Base

    def create_all(self) -> None:
        if self.schema:
            with self.engine.begin() as conn:
                conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{self.schema}"'))
        self.Base.metadata.create_all(bind=self.engine)

    def session(self) -> Iterator[Session]:
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()
