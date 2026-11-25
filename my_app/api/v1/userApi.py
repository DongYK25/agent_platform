from typing import Annotated

from fastapi import APIRouter, Query

from core.jwt import create_token
from schemas.commonSchemas import ResponseCommon
from schemas.userSchemas import UserCreate_Pydantic, UserQuerySet, UserUpdate_Pydantic
from services import userServices


router = APIRouter(prefix="/users", tags=["用户管理"])


@router.post("", response_model=ResponseCommon)
async def create_user(data: UserCreate_Pydantic):
    try:
        await userServices.create_user(data)
    except ValueError as exc:
        return ResponseCommon.failed(msg=str(exc))

    return ResponseCommon.success(data="创建成功")


@router.get("", response_model=ResponseCommon)
async def get_user(data: Annotated[UserQuerySet, Query()]):
    users = await userServices.get_user(data)
    return ResponseCommon.success(data=users)


@router.put("", response_model=ResponseCommon)
async def update_user(data: UserUpdate_Pydantic):
    try:
        user = await userServices.update_user(data)
    except ValueError as exc:
        return ResponseCommon.failed(msg=str(exc))

    if not user:
        return ResponseCommon.failed(msg="用户不存在", code=404)
    return ResponseCommon.success(data="更新成功")


@router.delete("", response_model=ResponseCommon)
async def delete_user(id: Annotated[int, Query(ge=1)]):
    user = await userServices.delete_user(id)
    if not user:
        return ResponseCommon.failed(msg="用户不存在", code=404)
    return ResponseCommon.success(data="删除成功")



@router.post("/login", response_model=ResponseCommon)
async def login(username: str, password: str):
    user = await userServices.login(username, password)
    if not user:
        return ResponseCommon.failed(msg="用户名或密码错误")
    token = create_token(user.id, user.user_uuid, user.username, user.role_id)
    return ResponseCommon.success(data=token)

