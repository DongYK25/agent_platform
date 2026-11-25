from tortoise import fields, models


class Role(models.Model):

    id = fields.BigIntField(primary_key=True)
    role_name = fields.CharField(max_length=32)
    remark = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)
    is_deleted = fields.BooleanField(default=False)


    class Meta:
        schema = "agent"
        table = "roles"



