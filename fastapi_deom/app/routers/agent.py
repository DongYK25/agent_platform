import re
import sys
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlmodel import select

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from fastapi_deom.agent.memory.db import get_history_message
from fastapi_deom.agent.memory.memory_api import chat_api

from ..dependencies import SessionDep
from ..models.base import utcnow
from ..models.session_messages import SessionMessage
from ..models.session_summaries import SessionSummary
from ..models.sessions import Session as ChatSession
from ..schemas.agent import AgentRequest, SessionTitleUpdate
from ..schemas.responseCommon import ResponseCommon

router = APIRouter(
    prefix="/agent",
    tags=["agent"],
)


def _user_uid(request: Request) -> UUID:
    raw = getattr(request.state, "token_data", {}).get("uid")
    if not raw:
        raise HTTPException(status_code=401, detail="token 中缺少用户信息")
    try:
        return UUID(str(raw))
    except ValueError:
        raise HTTPException(status_code=401, detail="token 中的用户信息无效") from None


def _own_session(db: SessionDep, user_uid: UUID, session_uid: UUID) -> ChatSession:
    row = db.exec(
        select(ChatSession).where(ChatSession.id == session_uid, ChatSession.user_uid == user_uid)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="对话不存在")
    return row


def _next_title(db: SessionDep, user_uid: UUID) -> str:
    """已有「对话1」「对话2」时，新窗口用下一个序号。model 不在这里填写。"""
    titles = db.exec(select(ChatSession.title).where(ChatSession.user_uid == user_uid)).all()
    numbers: list[int] = []
    for title in titles:
        if not isinstance(title, str):
            continue
        matched = re.fullmatch(r"对话(\d+)", title.strip())
        if matched:
            numbers.append(int(matched.group(1)))
    return f"对话{max(numbers) + 1 if numbers else 1}"


@router.post("/chat", response_model=ResponseCommon)
def agent_chat(request: Request, body: AgentRequest, db: SessionDep):
    text = body.msg.strip()
    if not text:
        raise HTTPException(status_code=400, detail="msg 不能为空")
    try:
        session_uid = UUID(body.session_uid)
    except ValueError:
        raise HTTPException(status_code=400, detail="session_uid 无效") from None

    user_uid = _user_uid(request)
    row = _own_session(db, user_uid, session_uid)
    db.commit()
    try:
        reply = chat_api(text, str(session_uid), str(user_uid))
    except Exception as exc:
        raise HTTPException(status_code=502, detail="模型调用失败") from exc
    row.updated_at = utcnow()
    db.add(row)
    db.commit()
    return ResponseCommon.success(data=reply)


@router.get("/chat_history", response_model=ResponseCommon)
def read_chat_history(request: Request, db: SessionDep, session_uid: UUID):
    """打开某个对话窗口时查询一次历史。"""
    user_uid = _user_uid(request)
    _own_session(db, user_uid, session_uid)
    try:
        history, _ = get_history_message(str(user_uid), str(session_uid))
    except Exception as exc:
        raise HTTPException(status_code=502, detail="历史记录查询失败") from exc
    data = []
    for message in history:
        content = message.content if isinstance(message.content, str) else str(message.content)
        role = "user" if message.type == "human" else "assistant"
        data.append({"role": role, "content": content})
    return ResponseCommon.success(data=data)


@router.get("/user_sessions", response_model=ResponseCommon)
def read_user_sessions(
    request: Request,
    db: SessionDep,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
):
    user_uid = _user_uid(request)
    rows = db.exec(
        select(ChatSession)
        .where(ChatSession.user_uid == user_uid)
        .order_by(ChatSession.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return ResponseCommon.success(data=[item.model_dump(mode="json") for item in rows])


@router.post("/user_sessions", response_model=ResponseCommon, status_code=status.HTTP_201_CREATED)
def create_user_session(request: Request, db: SessionDep):
    user_uid = _user_uid(request)
    row = ChatSession(user_uid=user_uid, title=_next_title(db, user_uid))
    db.add(row)
    db.commit()
    db.refresh(row)
    return ResponseCommon.success(data=row.model_dump(mode="json"))


@router.patch("/user_sessions/{session_uid}", response_model=ResponseCommon)
def update_user_session(
    session_uid: UUID,
    body: SessionTitleUpdate,
    request: Request,
    db: SessionDep,
):
    title = body.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="标题不能为空")
    row = _own_session(db, _user_uid(request), session_uid)
    row.title = title
    row.updated_at = utcnow()
    db.add(row)
    db.commit()
    db.refresh(row)
    return ResponseCommon.success(data=row.model_dump(mode="json"))


@router.delete("/user_sessions/{session_uid}", response_model=ResponseCommon)
def delete_user_session(session_uid: UUID, request: Request, db: SessionDep):
    user_uid = _user_uid(request)
    row = _own_session(db, user_uid, session_uid)
    messages = db.exec(
        select(SessionMessage).where(
            SessionMessage.session_uid == row.id,
            SessionMessage.user_uid == user_uid,
        )
    ).all()
    summaries = db.exec(
        select(SessionSummary).where(
            SessionSummary.session_uid == row.id,
            SessionSummary.user_uid == user_uid,
        )
    ).all()
    for item in messages:
        db.delete(item)
    for item in summaries:
        db.delete(item)
    db.delete(row)
    db.commit()
    return ResponseCommon.success()
