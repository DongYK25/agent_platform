from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, Column, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, SQLModel

from .base import table_args


class SessionMessage(SQLModel, table=True):
    __tablename__ = "session_messages"
    __table_args__ = table_args()

    id: int = Field(primary_key=True, sa_type=BigInteger)
    uid: UUID = Field(sa_type=PG_UUID(as_uuid=True))
    user_uid: UUID = Field(sa_type=PG_UUID(as_uuid=True))
    session_uid: UUID = Field(sa_type=PG_UUID(as_uuid=True))
    sequence_no: int = Field(sa_type=BigInteger)
    role: str
    content: str = Field(sa_type=Text)
    content_type: str
    content_token_count: int | None = None
    token_count_method: str | None = None
    tokenizer_model: str | None = None
    # 列名是 metadata，不能直接用作属性名。
    metadata_: dict = Field(sa_column=Column("metadata", JSONB, nullable=False))
    created_at: datetime = Field(sa_type=DateTime(timezone=True))
