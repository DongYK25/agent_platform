from datetime import datetime

from models.work_order import WorkOrder
from schemas.workOrderSchemas import (
    WorkOrderCreate_Pydantic,
    WorkOrderList_Pydantic,
    WorkOrderQuerySet,
    WorkOrderUpdate_Pydantic,
)


async def get_instances(data: WorkOrderQuerySet):
    filters = data.model_dump(
        exclude={"page", "page_size"},
        exclude_none=True,
    )
    query = WorkOrder.filter(is_deleted=False, **filters).order_by("id")

    if data.page is not None and data.page_size is not None:
        offset = (data.page - 1) * data.page_size
        query = query.offset(offset).limit(data.page_size)

    instances = await query.all()
    return [WorkOrderList_Pydantic.model_validate(instance) for instance in instances]


async def create_instance(data: WorkOrderCreate_Pydantic):
    instance = await WorkOrder.create(**data.model_dump())
    return WorkOrderList_Pydantic.model_validate(instance)



async def update_instance(data: WorkOrderUpdate_Pydantic):
    instance = await WorkOrder.get_or_none(id=data.id, is_deleted=False)
    if not instance:
        return None
    instance.update_from_dict(data.model_dump(exclude={"id"}))
    await instance.save()
    return WorkOrderList_Pydantic.model_validate(instance)


async def delete_instance(id: int):
    instance = await WorkOrder.get_or_none(id=id, is_deleted=False)
    if not instance:
        return None

    instance.is_deleted = True
    instance.deleted_at = datetime.now().astimezone()
    await instance.save(update_fields=["is_deleted", "deleted_at", "updated_at"])
    return instance
