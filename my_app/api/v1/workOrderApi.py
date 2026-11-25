from typing import Annotated

from fastapi import APIRouter, Query

from schemas.commonSchemas import ResponseCommon
from schemas.workOrderSchemas import WorkOrderCreate_Pydantic, WorkOrderQuerySet, WorkOrderUpdate_Pydantic
from services import workOrderServices


router = APIRouter(prefix="/workOrders", tags=["工作订单管理"])


@router.get("", response_model=ResponseCommon)
async def get_instance(data: Annotated[WorkOrderQuerySet, Query()]):
    instances = await workOrderServices.get_instances(data)
    return ResponseCommon.success(data=instances)


@router.post("", response_model=ResponseCommon)
async def create_instance(data: WorkOrderCreate_Pydantic):
    try:
        instance = await workOrderServices.create_instance(data)
    except ValueError as exc:
        return ResponseCommon.failed(msg=str(exc))

    return ResponseCommon.success(data=instance)


@router.put("", response_model=ResponseCommon)
async def update_instance(data: WorkOrderUpdate_Pydantic):
    try:
        instance = await workOrderServices.update_instance(data)
    except ValueError as exc:
        return ResponseCommon.failed(msg=str(exc))

    if not instance:
        return ResponseCommon.failed(msg="数据不存在", code=404)
    return ResponseCommon.success(data=instance)


@router.delete("", response_model=ResponseCommon)
async def delete_instance(id: Annotated[int, Query(ge=1)]):
    instance = await workOrderServices.delete_instance(id)
    if not instance:
        return ResponseCommon.failed(msg="数据不存在", code=404)
    return ResponseCommon.success(data="删除成功")
