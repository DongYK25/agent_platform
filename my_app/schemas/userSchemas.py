from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from tortoise.contrib.pydantic import pydantic_model_creator

from models import User


class UserQuerySet(BaseModel):
    id: int | None = Field(default=None, ge=1)
    user_uuid: UUID | None = None
    username: str | None = None
    email: str | None = None
    full_name: str | None = None
    phone: str | None = None
    status: str | None = None
    remark: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    page: int | None = Field(default=None, ge=1, description="页码，从 1 开始")
    page_size: int | None = Field(
        default=None,
        ge=1,
        le=100,
        description="每页数量，最大 100",
    )

    @model_validator(mode="after")
    def validate_pagination(self) -> "UserQuerySet":
        if (self.page is None) != (self.page_size is None):
            raise ValueError("page 和 page_size 必须同时提供")
        return self


UserList_Pydantic = pydantic_model_creator(
    User,
    name="UserList",
    exclude=("password",),
)

UserCreate_Pydantic = pydantic_model_creator(
    User,
    name="UserCreate",
    exclude_readonly=True,
    exclude=("user_uuid", "status", "deleted_at", "is_deleted"),
)

# 更新密码暂不单独处理。
UserUpdate_Pydantic = pydantic_model_creator(
    User,
    name="UserUpdate",
    exclude_readonly=False,
    exclude=(
        "user_uuid",
        "status",
        "deleted_at",
        "is_deleted",
        "created_at",
        "updated_at",
    ),
)
