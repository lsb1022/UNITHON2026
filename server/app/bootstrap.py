"""DB 초기화.

Postgres면 `db/schema.sql` 이 정본이므로 여기서 손대지 않는다 — 그 파일에만 들어 있는
CHECK 제약을 ORM이 흉내 내다 빠뜨리면, 기획서가 요구한 불변식이 조용히 사라진다.

SQLite면 스키마 파일을 쓸 수 없으므로(ENUM/JSONB/uuid 함수) 모델에서 테이블을 만든다.
모델 쪽에도 핵심 CHECK 를 옮겨 뒀기 때문에 같은 규칙이 그대로 강제된다.

    python -m app.bootstrap
"""

from __future__ import annotations

from sqlalchemy import event, inspect, text

from .db import DATABASE_URL, engine
from .models import Base


def is_sqlite() -> bool:
    return engine.dialect.name == "sqlite"


@event.listens_for(engine, "connect")
def _enable_sqlite_fks(dbapi_connection, _record):
    """SQLite는 외래키를 기본으로 끈다. 켜지 않으면 CASCADE 가 조용히 안 돈다."""
    if is_sqlite():
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def init() -> str:
    if not is_sqlite():
        with engine.connect() as conn:
            has_project = inspect(conn).has_table("project")
        if has_project:
            return f"Postgres 스키마 확인됨 ({DATABASE_URL})"
        raise RuntimeError(
            "Postgres에 테이블이 없습니다. 먼저 스키마를 적재하세요:\n"
            '  psql "$DATABASE_URL" -f db/schema.sql'
        )

    Base.metadata.create_all(engine)
    with engine.connect() as conn:
        tables = sorted(inspect(conn).get_table_names())
    return f"SQLite 테이블 {len(tables)}개 생성: {', '.join(tables)}"


def main() -> None:
    print(init())
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("연결 확인 OK")


if __name__ == "__main__":
    main()
