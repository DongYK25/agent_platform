from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Column, DateTime, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, SQLModel

from .base import table_args, utcnow


class SessionMessage(SQLModel, table=True):
    __tablename__ = "session_messages"
    __table_args__ = table_args()

    # 自增主键不由调用方传入，省略后由数据库生成。
    id: int | None = Field(default=None, primary_key=True, sa_type=BigInteger)
    uid: UUID = Field(
        default_factory=uuid4,
        sa_type=PG_UUID(as_uuid=True),
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
    )
    user_uid: UUID = Field(sa_type=PG_UUID(as_uuid=True))
    session_uid: UUID = Field(sa_type=PG_UUID(as_uuid=True))
    sequence_no: int = Field(sa_type=BigInteger)
    role: str
    content: str = Field(sa_type=Text)
    content_type: str = Field(
        default="text",
        sa_column_kwargs={"server_default": text("'text'")},
    )
    content_token_count: int | None = None
    token_count_method: str | None = None
    tokenizer_model: str | None = None
    # 列名是 metadata，不能直接用作属性名。
    metadata_: dict = Field(
        default_factory=dict,
        sa_column=Column(
            "metadata",
            JSONB,
            nullable=False,
            server_default=text("'{}'::jsonb"),
        ),
    )
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": text("now()")},
    )
