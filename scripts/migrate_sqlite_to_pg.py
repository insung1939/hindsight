"""로컬 SQLite(서비스 4개) → Supabase PostgreSQL 복사. 유튜브 쿼터를 다시 쓰지 않고 배포 DB 를 채운다.

    DATABASE_URL=postgresql://postgres.<ref>:…@…pooler.supabase.com:5432/postgres .venv/bin/python scripts/migrate_sqlite_to_pg.py [--truncate]

각 서비스의 models 를 그 서비스 폴더에서 import 해(스키마·테이블 정의가 단일 출처) PostgreSQL 에 create_all 한 뒤,
SQLite 의 모든 행을 1,000행씩 INSERT 한다. 이미 있는 PK 는 건너뛴다(ON CONFLICT DO NOTHING).
"""
import argparse
import importlib
import os
import sys
from pathlib import Path

from sqlalchemy import MetaData, Table, create_engine, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

ROOT = Path(__file__).resolve().parents[1]
SERVICES = {"market-data": "market", "youtube": "yt", "mentions": "mentions", "stats": "stats"}

ap = argparse.ArgumentParser()
ap.add_argument("--truncate", action="store_true", help="복사 전에 대상 테이블을 비운다")
ap.add_argument("--only", help="서비스 하나만 (market-data|youtube|mentions|stats)")
args = ap.parse_args()

PG_URL = os.environ.get("DATABASE_URL", "")
if not PG_URL.startswith("postgres"):
    sys.exit("DATABASE_URL 환경변수에 PostgreSQL 주소를 넣으세요")
sys.path.insert(0, str(ROOT / "libs" / "hs-common"))
from hs_common.db import normalize_url  # noqa: E402

pg = create_engine(normalize_url(PG_URL), pool_pre_ping=True)

for svc, schema in SERVICES.items():
    if args.only and svc != args.only:
        continue
    sqlite_path = ROOT / "services" / svc / f"{svc}.db"
    if not sqlite_path.exists():
        print(f"[{svc}] SQLite 없음 — 건너뜀"); continue
    # 1) 대상 테이블 만들기: 서비스 models 를 DATABASE_URL=PG 로 import → Database 가 스키마를 붙인다
    sys.path.insert(0, str(ROOT / "services" / svc))
    for m in ("models", "hs_common.settings"):
        sys.modules.pop(m, None)
    os.environ["DATABASE_URL"] = PG_URL
    models = importlib.import_module("models")
    models.db.create_all()
    target_md = models.db.Base.metadata
    sys.path.pop(0); sys.modules.pop("models", None)
    # 2) 원본 읽기
    src = create_engine(f"sqlite:///{sqlite_path}")
    src_md = MetaData(); src_md.reflect(bind=src)
    with pg.begin() as conn:
        for tname, ttable in target_md.tables.items():
            bare = ttable.name
            if bare not in src_md.tables:
                continue
            stable: Table = src_md.tables[bare]
            cols = [c.name for c in stable.columns if c.name in ttable.columns]
            if args.truncate:
                conn.execute(text(f'TRUNCATE TABLE "{schema}"."{bare}" RESTART IDENTITY CASCADE'))
            n = 0
            with src.connect() as sconn:
                rows = sconn.execute(select(*[stable.c[c] for c in cols])).mappings()
                batch = []
                for r in rows:
                    batch.append(dict(r))
                    if len(batch) >= 1000:
                        conn.execute(pg_insert(ttable).values(batch).on_conflict_do_nothing()); n += len(batch); batch = []
                if batch:
                    conn.execute(pg_insert(ttable).values(batch).on_conflict_do_nothing()); n += len(batch)
            # autoincrement 시퀀스 맞추기
            if "id" in ttable.columns and ttable.columns["id"].autoincrement is not False:
                conn.execute(text(f"""SELECT setval(pg_get_serial_sequence('"{schema}"."{bare}"', 'id'), COALESCE((SELECT MAX(id) FROM "{schema}"."{bare}"), 1))"""))
            print(f"[{svc}] {schema}.{bare}: {n}행 복사")
print("완료")
