from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field

from .base import RecordBase, table_args


class WorkOrder(RecordBase, table=True):
    __tablename__ = "work_order"
    __table_args__ = table_args()

    order_uuid: UUID = Field(default_factory=uuid4, sa_type=PG_UUID(as_uuid=True))
    title: str
    content: str | None = None
    status: str = "pending"
    order_type: str | None = None
    priority: str | None = "medium"
    creator_id: int = Field(sa_type=BigInteger)
    handler_id: int | None = Field(default=None, sa_type=BigInteger)
    finished_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
