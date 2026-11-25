from datetime import datetime

from common import role_data
from models import Role
from schemas.roleSchemas import (
    RoleCreate_Pydantic,
    RoleList_Pydantic,
    RoleQuerySet,
    RoleUpdate_Pydantic,
)


async def get_instances(data: RoleQuerySet):
    filters = data.model_dump(
        exclude={"page", "page_size", "is_deleted"},
        exclude_none=True,
    )
    query = Role.filter(is_deleted=False, **filters).order_by("id")

    if data.page is not None and data.page_size is not None:
        offset = (data.page - 1) * data.page_size
        query = query.offset(offset).limit(data.page_size)

    instances = await query.all()
    return [RoleList_Pydantic.model_validate(instance) for instance in instances]


async def create_instance(data: RoleCreate_Pydantic):
    instance = await Role.create(**data.model_dump())
    await role_data.update_location_role()
    return RoleList_Pydantic.model_validate(instance)


async def update_instance(data: RoleUpdate_Pydantic):
    instance = await Role.get_or_none(id=data.id, is_deleted=False)
    if not instance:
        return None

    instance.update_from_dict(data.model_dump(exclude={"id"}))
    await instance.save()
    await role_data.update_location_role()
    return RoleList_Pydantic.model_validate(instance)


async def delete_instance(id: int):
    instance = await Role.get_or_none(id=id, is_deleted=False)
    if not instance:
        return None

    instance.is_deleted = True
    instance.deleted_at = datetime.now().astimezone()
    await instance.save(update_fields=["is_deleted", "deleted_at", "updated_at"])
    await role_data.update_location_role()
    return instance
