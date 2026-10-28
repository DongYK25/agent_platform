from pydantic import EmailStr, field_validator
from sqlmodel import Field, SQLModel

from ..models.user import UserBase, ensure_username


class UserPublic(UserBase):
    id: int


class UserCreate(UserBase):
    email: EmailStr = Field(max_length=255, description="邮箱")
    password: str = Field(min_length=6, max_length=128, description="密码，6-128 位")


class UserUpdate(SQLModel):
    username: str | None = Field(
        default=None,
        min_length=3,
        max_length=32,
        description="3-32 位，只能包含字母、数字和下划线",
    )
    email: EmailStr | None = Field(default=None, max_length=255, description="邮箱")
    full_name: str | None = Field(default=None, max_length=50, description="姓名")
    password: str | None = Field(
        default=None, min_length=6, max_length=128, description="密码，6-128 位"
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return ensure_username(value)
