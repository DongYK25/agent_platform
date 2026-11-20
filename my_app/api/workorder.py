"""work_order 增删查改"""

import asyncio
import sys
from datetime import datetime, timezone

from db import close_db, init_db
from db.models import WorkOrder


# ---------- 增 ----------
async def create_work_order(title: str, creator_id: int, **kwargs) -> WorkOrder:
    """新建工单, kwargs 可传 content / status / order_type / priority / handler_id / remark"""
    return await WorkOrder.create(title=title, creator_id=creator_id, **kwargs)


# ---------- 删 ----------
async def delete_work_order(order_id: int) -> bool:
    """软删除: 只标记 is_deleted, 不真正删除数据"""
    order = await WorkOrder.get_or_none(id=order_id, is_deleted=False)
    if order is None:
        return False
    order.is_deleted = True
    order.deleted_at = datetime.now(timezone.utc)
    await order.save()
    return True


async def hard_delete_work_order(order_id: int) -> bool:
    """物理删除: 从表中删除这条记录"""
    deleted_count = await WorkOrder.filter(id=order_id).delete()
    return deleted_count > 0


# ---------- 查 ----------
async def get_work_order(order_id: int) -> WorkOrder | None:
    """按 id 查询单条工单"""
    return await WorkOrder.get_or_none(id=order_id, is_deleted=False)


async def list_work_orders(page: int = 1, page_size: int = 10, **filters) -> list[WorkOrder]:
    """分页查询工单列表, filters 可传 status / creator_id / handler_id 等"""
    return (
        await WorkOrder.filter(is_deleted=False, **filters)
        .order_by("-created_at")
        .offset((page - 1) * page_size)
        .limit(page_size)
    )


# ---------- 改 ----------
async def update_work_order(order_id: int, **kwargs) -> WorkOrder | None:
    """修改工单, 用 save() 保存时 updated_at 会自动更新"""
    order = await WorkOrder.get_or_none(id=order_id, is_deleted=False)
    if order is None:
        return None
    for key, value in kwargs.items():
        setattr(order, key, value)
    await order.save()
    return order

from fastapi.encoders import jsonable_encoder
# ---------- 示例 ----------
async def main():
    await init_db()
    try:
        aa = await  WorkOrder.filter( is_deleted=False).all()
        print(aa)
        print(jsonable_encoder(aa))
        # order = await create_work_order(title="测试工单", creator_id=1, content="工单内容")
        # print("新建:", order)

        # print("查询:", await get_work_order(order.id))
        # print("列表:", await list_work_orders(status="pending"))

        # order = await update_work_order(order.id, status="done", handler_id=2)
        # print("修改:", order, order.status)

        # print("删除:", await delete_work_order(order.id))
    finally:
        await close_db()


if __name__ == "__main__":
    # Windows 默认的 ProactorEventLoop 不支持 psycopg 异步模式, 需改用 SelectorEventLoop
    if sys.platform == "win32":
        asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop)
    else:
        asyncio.run(main())
