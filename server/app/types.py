"""방언 중립 컬럼 타입.

정본 스키마는 Postgres(`db/schema.sql`)다. 하지만 이 프로젝트를 처음 켜는 사람에게
"Docker부터 설치하세요"를 요구하면 백엔드가 영영 안 돌아간다. 그래서 같은 모델이
SQLite 위에서도 뜨게 만들어 뒀다.

Postgres에서는 UUID / JSONB 를 그대로 쓰고, SQLite에서는 CHAR(36) / JSON 으로 떨어진다.
값의 의미는 같고, 저장 형태만 방언에 맞춘다.
"""

from __future__ import annotations

import uuid

from sqlalchemy import CHAR, JSON, String, TypeDecorator
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID


class GUID(TypeDecorator):
    """Postgres면 uuid, 아니면 36자 문자열. 파이썬 쪽은 항상 uuid.UUID 로 보인다."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


def json_type():
    """Postgres에서는 JSONB, 그 외에는 JSON."""
    return JSON().with_variant(JSONB(), "postgresql")


def enum_type(name: str, *values: str):
    """
    Postgres에서는 진짜 ENUM 타입(schema.sql 이 이미 생성), 그 외에는 문자열.

    create_type=False 인 이유: 타입 생성의 주인은 DDL 파일이다. ORM이 몰래 만들면
    schema.sql 과 두 벌이 되고, 어느 쪽이 정본인지 알 수 없어진다.
    """
    return String(32).with_variant(PG_ENUM(*values, name=name, create_type=False), "postgresql")
