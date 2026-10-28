import re
from uuid import UUID, uuid4

from pydantic import field_validator
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, SQLModel

from .base import RecordBase, table_args

_USERNAME = re.compile(r"^[A-Za-z0-9_]+$")


def ensure_username(value: str) -> str:
    if _USERNAME.fullmatch(value) is None:
        raise ValueError("只能包含字母、数字和下划线")
    return value


class UserBase(SQLModel):
    username: str = Field(
        index=True,
        unique=True,
        min_length=3,
        max_length=32,
        description="3-32 位，只能包含字母、数字和下划线",
    )
    email: str = Field(index=True, unique=True, max_length=255, description="邮箱")
    full_name: str | None = Field(default=None, max_length=50, description="姓名")

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        return ensure_username(value)


class User(RecordBase, UserBase, table=True):
    __tablename__ = "users"
    __table_args__ = table_args()

    user_uuid: UUID = Field(
        default_factory=uuid4,
        sa_type=PG_UUID(as_uuid=True),
        sa_column_kwargs={
            "nullable": False,
            "unique": True,
            "server_default": text("gen_random_uuid()"),
        },
    )
    phone: str | None = Field(default=None, max_length=20, description="手机号")
    # 当前练习直接保存提交的密码，接入登录时再改成哈希。
    password: str
