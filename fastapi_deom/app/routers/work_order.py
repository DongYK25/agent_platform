from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from ..dependencies import SessionDep
from ..models.work_order import WorkOrder
from ..schemas.responseCommon import ResponseCommon
from ..schemas.work_order import WorkOrderCreate, WorkOrderPublic, WorkOrderUpdate

router = APIRouter(
    prefix="/work_orders",
    tags=["work_orders"], ##这是写给接口文档的分组名
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=ResponseCommon, status_code=status.HTTP_201_CREATED)
def create_work_order(work_order: WorkOrderCreate, request: Request, session: SessionDep):
    # schema 只校验调用方提交的字段；入库对象必须是 table=True 的 WorkOrder。
    payload = request.state.token_data
    creator_id = payload.get("id")
    if creator_id is None:
        raise HTTPException(status_code=401, detail="token 中缺少用户信息")

    db_work_order = WorkOrder.model_validate(
        {**work_order.model_dump(), "creator_id": creator_id}
    )
    session.add(db_work_order)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="WorkOrdername or email already exists")
    session.refresh(db_work_order)
    return ResponseCommon.success(data=db_work_order)


@router.get("/", response_model=ResponseCommon)
def read_work_orders(
    request: Request,
    session: SessionDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
):
    # 中间件已校验并解码 token，这里就是登录时放进去的 id、work_ordername。
    payload = request.state.token_data
    user_id = payload.get("id")
    username = payload.get("username")
    print(111111,user_id,username)
    if user_id is None or not username:
        raise HTTPException(status_code=401, detail="token 中缺少用户信息")
    
    work_orders = session.exec(select(WorkOrder).offset(offset).limit(limit)).all()
    return_data = [WorkOrderPublic.model_validate(item) for item in work_orders]
    return ResponseCommon.success(data=return_data)


@router.get("/{work_order_id}", response_model=ResponseCommon)
def read_work_order(work_order_id: int, session: SessionDep):
    work_order = session.get(WorkOrder, work_order_id)
    if not work_order:
        raise HTTPException(status_code=404, detail="WorkOrder not found")
    return ResponseCommon.success(data=work_order)


@router.patch("/{work_order_id}", response_model=ResponseCommon)
def update_work_order(work_order_id: int, work_order: WorkOrderUpdate, session: SessionDep):
    db_work_order = session.get(WorkOrder, work_order_id)
    if not db_work_order:
        raise HTTPException(status_code=404, detail="WorkOrder not found")
    db_work_order.sqlmodel_update(
        work_order.model_dump(exclude_unset=True, exclude={"id",})
    )
    # session.add(db_work_order)
    try:
        session.commit()
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(e))
    session.refresh(db_work_order)
    return ResponseCommon.success(data=db_work_order)


@router.delete("/{work_order_id}")
def delete_work_order(work_order_id: int, session: SessionDep):
    work_order = session.get(WorkOrder, work_order_id)
    if not work_order:
        raise HTTPException(status_code=404, detail="WorkOrder not found")
    session.delete(work_order)
    session.commit()
    return ResponseCommon.success()


