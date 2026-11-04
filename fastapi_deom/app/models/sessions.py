from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, SQLModel

from .base import table_args, utcnow


def _table_args():
    return (
        # Index("idx_sessions_user", "user_id", text("updated_at DESC")),
        table_args() or {},
    )


class Session(SQLModel, table=True):
    __tablename__ = "sessions"
    __table_args__ = _table_args()

    id: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        sa_type=PG_UUID(as_uuid=True),
        sa_column_kwargs={"server_default": text("gen_random_uuid()")},
    )
    user_uid: UUID | None = Field(default=None, sa_type=PG_UUID(as_uuid=True))
    prompt_name: str = Field(
        default="assistant",
        sa_type=Text,
        sa_column_kwargs={"server_default": text("'assistant'")},
    )
    model: str | None = Field(default=None, sa_type=Text)
    title: str | None = Field(default=None, sa_type=Text)
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": text("now()")},
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": text("now()")},
    )
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
