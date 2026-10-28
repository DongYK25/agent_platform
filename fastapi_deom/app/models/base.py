from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime
from sqlmodel import Field, SQLModel

from ..database import DB_SCHEMA


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def table_args() -> dict[str, str] | None:
    """指定schema,默认为配置文件中的"""
    if not DB_SCHEMA:
        return None
    return {"schema": DB_SCHEMA}


class RecordBase(SQLModel):
    """各业务表共用的主键、状态、备注、时间和软删除字段。"""
    """
    default_factory 动态生成默认值
    sa_type 数据库中的实际类型
    bool = False 相当于默认值， :后面的描述基本都是创建数据或者数据库表的时候的约束条件
    """

    id: int | None = Field(default=None, primary_key=True, sa_type=BigInteger)
    status: str = "active"
    remark: str | None = None
    created_at: datetime = Field(default_factory=utcnow, sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(default_factory=utcnow, sa_type=DateTime(timezone=True))
    deleted_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    is_deleted: bool = False
