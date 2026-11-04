from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session,select

from app.dependencies import SessionDep 
from app.database import engine
from app.models import SessionMessage
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

def get_history_message(user_uid: str,session_uid:str):
    '''从数据库中获取所有的历史消息'''
    with Session(engine) as session:
        statement = select(SessionMessage).where(
            SessionMessage.user_uid == user_uid, 
            SessionMessage.session_uid == session_uid
            ).order_by(SessionMessage.sequence_no.asc())
        result = session.exec(statement).all()
    messages = []
    for e in result:
        if e.role == "user":
            messages.append(HumanMessage(content=e.content))
        elif e.role == "assistant":
            messages.append(AIMessage(content=e.content))

    if result:
        return messages,result[-1].sequence_no
    else:
        return messages,0

# def add_message(session: SessionDep,uid:str, user_uid: str, session_uid: str, sequence_no: int,role:str,content:str,content_token_count:int,token_count_method:str):
def add_message(add_list:list[dict]):    
    with Session(engine) as session:
        db_add_messages = [SessionMessage.model_validate(item) for item in add_list]
        session.add_all(db_add_messages)
        try:
            session.commit()
        except Exception as e:
            session.rollback()
            return str(e)
    return None

