"""数据模型, 对应 agent.work_order 表"""

import uuid

from tortoise import fields
from tortoise.models import Model


class WorkOrder(Model):
    id = fields.BigIntField(primary_key=True)
    order_uuid = fields.UUIDField(default=uuid.uuid4)
    title = fields.CharField(max_length=512)
    content = fields.TextField(null=True)
    status = fields.CharField(max_length=32, default="pending")
    order_type = fields.CharField(max_length=64, null=True)
    priority = fields.CharField(max_length=32, default="medium", null=True)
    creator_id = fields.BigIntField()
    handler_id = fields.BigIntField(null=True)
    remark = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    finished_at = fields.DatetimeField(null=True)
    deleted_at = fields.DatetimeField(null=True)
    is_deleted = fields.BooleanField(default=False)

    class Meta:
        schema = "agent"
        table = "work_order"

    def __str__(self):
        return f"WorkOrder(id={self.id}, title={self.title})"
