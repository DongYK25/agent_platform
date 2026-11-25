from datetime import datetime

from models.user import User
from schemas.userSchemas import (
    UserCreate_Pydantic,
    UserList_Pydantic,
    UserQuerySet,
    UserUpdate_Pydantic,
)


async def get_user(data: UserQuerySet) -> list[UserList_Pydantic]:
    filters = data.model_dump(
        exclude={"page", "page_size"},
        exclude_none=True,
    )
    query = User.filter(is_deleted=False, **filters).order_by("id")

    if data.page is not None and data.page_size is not None:
        offset = (data.page - 1) * data.page_size
        query = query.offset(offset).limit(data.page_size)

    users = await query.all()
    return [UserList_Pydantic.model_validate(user) for user in users]


async def create_user(data: UserCreate_Pydantic) -> User:
    exists = await User.filter(username=data.username).exists()
    if exists:
        raise ValueError("用户名已存在")

    return await User.create(**data.model_dump())


async def update_user(data: UserUpdate_Pydantic) -> User | None:
    user = await User.get_or_none(id=data.id, is_deleted=False)
    if not user:
        return None

    exists = await User.filter(username=data.username).exclude(id=data.id).exists()
    if exists:
        raise ValueError("用户名已存在")

    # PUT 采用整体覆盖；主键只用于定位记录，不参与更新。
    user.update_from_dict(data.model_dump(exclude={"id"}))
    await user.save()
    return user


async def delete_user(id: int) -> User | None:
    user = await User.get_or_none(id=id, is_deleted=False)
    if not user:
        return None

    user.is_deleted = True
    user.deleted_at = datetime.now().astimezone()
    await user.save(update_fields=["is_deleted", "deleted_at", "updated_at"])
    return user


async def login(username: str, password: str) -> User | None:
    user = await User.get_or_none(username=username, is_deleted=False)
    if not user or user.password != password:
        return None
    return user