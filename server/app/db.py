"""DB 연결. 파이프라인 스크립트(scout/run/score)와 API가 같은 세션 팩토리를 쓴다."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# 기본값은 SQLite다. 처음 켜는 사람이 Docker부터 설치해야 하면 백엔드는 영영 안 돌아간다.
# 운영/실측용 Postgres 로 바꾸려면 환경변수만 주면 된다:
#   DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/uxlab
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./uxlab.db")

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@contextmanager
def session_scope() -> Iterator[Session]:
    """파이프라인 스크립트용. 예외가 나면 롤백한다 — 반쯤 적재된 실행 기록은 통계를 오염시킨다."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Iterator[Session]:
    """FastAPI 의존성."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
