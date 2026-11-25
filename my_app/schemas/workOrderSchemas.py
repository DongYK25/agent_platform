from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from tortoise.contrib.pydantic import pydantic_model_creator

from models import WorkOrder

class WorkOrderQuerySet(BaseModel):
    id: int | None = Field(default=None, ge=1)
    order_uuid: UUID | None = None
    title: str | None = None
    content: str | None = None
    status: str | None = None
    order_type: str | None = None
    priority: str | None = None
    creator_id: int | None = None
    handler_id: int | None = None
    remark: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    finished_at: datetime | None = None
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
    def validate_pagination(self) -> "WorkOrderQuerySet":
        if (self.page is None) != (self.page_size is None):
            raise ValueError("page 和 page_size 必须同时提供")
        return self

WorkOrderList_Pydantic = pydantic_model_creator(
    WorkOrder,
    name="WorkOrderList",
    exclude=(),
)

WorkOrderCreate_Pydantic = pydantic_model_creator(
    WorkOrder,
    name="WorkOrderCreate",
    exclude_readonly=True,
    exclude=("order_uuid","deleted_at", "is_deleted"),
)

# 更新密码暂不单独处理。
WorkOrderUpdate_Pydantic = pydantic_model_creator(
    WorkOrder,
    name="WorkOrderUpdate",
    exclude_readonly=False,
    exclude=(
        "order_uuid",
        "deleted_at",
        "is_deleted",
        "created_at",
        "updated_at",
    ),
)