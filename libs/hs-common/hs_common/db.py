"""DATABASE_URL 하나로 SQLite(로컬) ↔ PostgreSQL/Supabase(배포) 전환. 서비스마다 자기 스키마만 쓴다."""
from collections.abc import Iterator

from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .settings import env


def normalize_url(url: str) -> str:
    """Supabase 가 주는 `postgresql://…` 를 psycopg2 드라이버로 고정한다.
    SQLAlchemy 2.1 부터 접두사 없는 postgresql:// 의 기본 드라이버가 psycopg(3)으로 바뀌어, psycopg2-binary 만 설치된 환경에서 'No module named psycopg' 가 난다."""
    if url.startswith("postgres://"):  # Heroku 식 접두사도 허용
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


class Database:
    def __init__(self, service_name: str, schema: str):
        self.url = normalize_url(env("DATABASE_URL", f"sqlite:///./{service_name}.db") or "")
        self.is_sqlite = self.url.startswith("sqlite")
        # SQLite 는 스키마가 없으므로 PostgreSQL 일 때만 스키마를 붙인다.
        self.schema = None if self.is_sqlite else schema
        connect_args = {"check_same_thread": False} if self.is_sqlite else {"connect_timeout": 15}
        # Supabase Session pooler 는 동시 접속 15개 한도. 서비스 4개 × 기본 풀(5+10)이면 금방 넘쳐 배포(새 인스턴스 기동)가 실패한다.
        # 엔진당 상시 1개, 최대 3개(4 서비스 = 12 이하). 5분 넘은 연결은 재생성, 끊긴 연결은 pre_ping 으로 감지.
        pool_kwargs = {} if self.is_sqlite else {"pool_size": 1, "max_overflow": 2, "pool_timeout": 30, "pool_recycle": 300}
        self.engine = create_engine(self.url, connect_args=connect_args, pool_pre_ping=True, **pool_kwargs)
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
