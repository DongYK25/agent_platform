import re

from pydantic import field_validator
from sqlmodel import Field, SQLModel

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


class User(UserBase, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    # 当前练习直接保存提交的密码，接入登录时再改成哈希。
    password: str
