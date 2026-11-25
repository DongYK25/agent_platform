
import uuid

from tortoise import fields, models


class User(models.Model):

    id = fields.BigIntField(primary_key=True)

    user_uuid = fields.UUIDField(default=uuid.uuid4)

    username = fields.CharField(max_length=32)

    password = fields.CharField(max_length=255)

    email = fields.CharField(max_length=255, null=True)

    full_name = fields.CharField(max_length=50, null=True)

    phone = fields.CharField(max_length=20, null=True)

    role_id = fields.BigIntField()

    status = fields.CharField(max_length=32, default="active")

    remark = fields.TextField(null=True)

    created_at = fields.DatetimeField(auto_now_add=True)

    updated_at = fields.DatetimeField(auto_now=True)

    deleted_at = fields.DatetimeField(null=True)

    is_deleted = fields.BooleanField(default=False)

    class Meta:
        schema = "agent"
        table = "users"



