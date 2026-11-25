from typing import Annotated

from fastapi import APIRouter, Query

from schemas.commonSchemas import ResponseCommon
from schemas.roleSchemas import (
    RoleCreate_Pydantic,
    RoleQuerySet,
    RoleUpdate_Pydantic,
)
from services import roleServices


router = APIRouter(prefix='/roles', tags=['角色管理'])


@router.get("", response_model=ResponseCommon)
async def get_instance(data: Annotated[RoleQuerySet, Query()]):
    instances = await roleServices.get_instances(data)
    return ResponseCommon.success(data=instances)


@router.post("", response_model=ResponseCommon)
async def create_instance(data: RoleCreate_Pydantic):
    try:
        instance = await roleServices.create_instance(data)
    except ValueError as exc:
        return ResponseCommon.failed(msg=str(exc))

    return ResponseCommon.success(data=instance)


@router.put("", response_model=ResponseCommon)
async def update_instance(data: RoleUpdate_Pydantic):
    try:
        instance = await roleServices.update_instance(data)
    except ValueError as exc:
        return ResponseCommon.failed(msg=str(exc))

    if not instance:
        return ResponseCommon.failed(msg="数据不存在", code=404)
    return ResponseCommon.success(data=instance)


@router.delete("", response_model=ResponseCommon)
async def delete_instance(id: Annotated[int, Query(ge=1)]):
    instance = await roleServices.delete_instance(id)
    if not instance:
        return ResponseCommon.failed(msg="数据不存在", code=404)
    return ResponseCommon.success(data="删除成功")
