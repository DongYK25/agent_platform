from uuid import UUID

from sqlmodel import Field, SQLModel


class WorkOrderPublic(SQLModel):
    """列表返回。只输出这些字段，内容、备注、时间、完成时间和软删除标记不返回。"""

    id: int = Field(description="工单 id")
    order_uuid: UUID = Field(description="工单 uuid")
    title: str = Field(description="标题")
    status: str = Field(description="状态")
    order_type: str | None = Field(default=None, description="工单类型")
    priority: str | None = Field(default=None, description="优先级")
    creator_id: int = Field(description="创建人")
    handler_id: int | None = Field(default=None, description="处理人")


class WorkOrderCreate(SQLModel):
    """新增。id、order_uuid、创建/更新时间、创建人、完成时间由系统写入。"""

    title: str = Field(description="标题")
    content: str | None = Field(default=None, description="内容")
    status: str = Field(default="pending", description="状态，默认 pending")
    order_type: str | None = Field(default=None, description="工单类型")
    priority: str | None = Field(default="medium", description="优先级，默认 medium")
    handler_id: int | None = Field(default=None, description="处理人")
    remark: str | None = Field(default=None, description="备注")


class WorkOrderUpdate(SQLModel):
    """修改。用 id 指定记录，只提交要改的字段。

    可改：标题、内容、状态、类型、优先级、处理人、备注。
    不可改：order_uuid、创建人、创建/更新/删除时间、完成时间、软删除标记。
    """

    id: int = Field(description="工单 id")
    title: str | None = Field(default=None, description="标题")
    content: str | None = Field(default=None, description="内容")
    status: str | None = Field(default=None, description="状态")
    order_type: str | None = Field(default=None, description="工单类型")
    priority: str | None = Field(default=None, description="优先级")
    handler_id: int | None = Field(default=None, description="处理人")
    remark: str | None = Field(default=None, description="备注")


class WorkOrderDelete(SQLModel):
    """删除。只传 id。"""

    id: int = Field(description="工单 id")


class WorkOrderQuery(SQLModel):
    """查询。字段都可选，传入哪个就按哪个过滤，可以组合。"""

    id: int | None = Field(default=None, description="工单 id")
    order_uuid: UUID | None = Field(default=None, description="工单 uuid")
    title: str | None = Field(default=None, description="标题")
    status: str | None = Field(default=None, description="状态")
    order_type: str | None = Field(default=None, description="工单类型")
    priority: str | None = Field(default=None, description="优先级")
    creator_id: int | None = Field(default=None, description="创建人")
    handler_id: int | None = Field(default=None, description="处理人")
