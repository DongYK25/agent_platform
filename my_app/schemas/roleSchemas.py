from datetime import datetime

from pydantic import BaseModel, Field, model_validator
from tortoise.contrib.pydantic import pydantic_model_creator

from models import Role


class RoleQuerySet(BaseModel):
    id: int | None = Field(default=None, ge=1)
    role_name: str | None = None
    remark: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    is_deleted: bool | None = None
    page: int | None = Field(default=None, ge=1, description="页码，从 1 开始")
    page_size: int | None = Field(
        default=None,
        ge=1,
        le=100,
        description="每页数量，最大 100",
    )

    @model_validator(mode="after")
    def validate_pagination(self) -> "RoleQuerySet":
        if (self.page is None) != (self.page_size is None):
            raise ValueError("page 和 page_size 必须同时提供")
        return self


RoleList_Pydantic = pydantic_model_creator(
    Role,
    name="RoleList",
    exclude=(),
)

RoleCreate_Pydantic = pydantic_model_creator(
    Role,
    name="RoleCreate",
    exclude_readonly=True,
    exclude=("deleted_at", "is_deleted"),
)

RoleUpdate_Pydantic = pydantic_model_creator(
    Role,
    name="RoleUpdate",
    exclude_readonly=False,
    exclude=(
        "deleted_at",
        "is_deleted",
        "created_at",
        "updated_at",
    ),
)
