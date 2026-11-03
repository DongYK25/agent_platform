from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, SQLModel

from .base import table_args


class SessionSummary(SQLModel, table=True):
    __tablename__ = "session_summaries"
    __table_args__ = table_args()

    id: int = Field(primary_key=True, sa_type=BigInteger)
    uid: UUID = Field(sa_type=PG_UUID(as_uuid=True))
    user_uid: UUID = Field(sa_type=PG_UUID(as_uuid=True))
    session_uid: UUID = Field(sa_type=PG_UUID(as_uuid=True))
    summary: str = Field(sa_type=Text)
    summary_data: dict = Field(sa_type=JSONB)
    source_last_message_id: int | None = Field(default=None, sa_type=BigInteger)
    source_last_sequence_no: int = Field(sa_type=BigInteger)
    source_message_count: int
    source_token_count: int | None = None
    summary_token_count: int | None = None
    compression_prompt_tokens: int | None = None
    compression_completion_tokens: int | None = None
    compression_model: str | None = None
    prompt_version: str | None = None
    version: int
    created_at: datetime = Field(sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(sa_type=DateTime(timezone=True))
