from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from ..middleware.auth import create_token

from ..dependencies import SessionDep
from ..models.user import User
from ..schemas.responseCommon import ResponseCommon
from ..schemas.user import UserCreate, UserPublic, UserUpdate

router = APIRouter(
    prefix="/users",
    tags=["users"], ##这是写给接口文档的分组名
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def create_user(user: UserCreate, session: SessionDep):
    db_user = User.model_validate(user)
    session.add(db_user)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Username or email already exists")
    session.refresh(db_user)
    return db_user


@router.get("/", response_model=ResponseCommon)
def read_users(
    request: Request,
    session: SessionDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
):
    # 中间件已校验并解码 token，这里就是登录时放进去的 id、username。
    payload = request.state.token_data
    user_id = payload.get("id")
    username = payload.get("username")
    print(111111,user_id,username)
    if user_id is None or not username:
        return ResponseCommon.failed(msg="token 中缺少用户信息")

    users = session.exec(select(User).offset(offset).limit(limit)).all()
    return ResponseCommon.success(data=users)


@router.get("/{user_id}", response_model=UserPublic)
def read_user(user_id: int, session: SessionDep):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserPublic)
def update_user(user_id: int, user: UserUpdate, session: SessionDep):
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db_user.sqlmodel_update(user.model_dump(exclude_unset=True))
    session.add(db_user)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Username or email already exists")
    session.refresh(db_user)
    return db_user


@router.delete("/{user_id}")
def delete_user(user_id: int, session: SessionDep):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    session.delete(user)
    session.commit()
    return {"ok": True}



@router.post("/login")
def login(username: str, password: str, session: SessionDep):
    try:
        if not username or not password:
            raise HTTPException(status_code=400, detail="Username or password is required")
        user = session.exec(select(User).where(User.username == username, User.password == password)).one()
        token = create_token({"id":user.id, "username":user.username})
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Username or email already exists")
    # session.refresh(db_user)
    return {"token": token}
