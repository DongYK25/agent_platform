import os
from pathlib import Path
from typing import Annotated, Sequence, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage,SystemMessage,AnyMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from psycopg.conninfo import make_conninfo
from langgraph.prebuilt import ToolNode
from app.database import DB_SCHEMA, database_url
import requests
from langchain_core.tools import tool

load_dotenv(Path(__file__).resolve().parent / ".env")
weather_api_url=os.getenv("WEATHER_API_URL")
print(weather_api_url)
class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

################################
def _checkpoint_conninfo() -> str:
    """把项目的 SQLAlchemy PostgreSQL URL 转为 psycopg 可使用的连接串。"""
    if not database_url.drivername.startswith("postgresql"):
        raise RuntimeError("PostgresSaver 只能使用 PostgreSQL，请检查 app.database.USE_DB")

    # psycopg 认识 postgresql://，不认识 SQLAlchemy 的 postgresql+psycopg://。
    uri = database_url.set(drivername="postgresql").render_as_string(
        hide_password=False
    )

    # 项目使用 agent schema；通过 search_path 让官方迁移表也建在该 schema。
    # make_conninfo 会正确处理连接参数的转义，不要手工拼接密码或 query string。
    if DB_SCHEMA:
        return make_conninfo(uri, options=f"-csearch_path={DB_SCHEMA}")
    return uri

CHECKPOINT_CONNINFO = _checkpoint_conninfo()


def _thread_config(user_uid: str, session_uid: str) -> dict:
    """同一用户、同一会话必须始终得到同一个 thread_id。"""
    if not user_uid or not session_uid:
        raise ValueError("user_uid 和 session_uid 不能为空")

    # thread_id 就是 checkpointer 查找会话状态的键。
    # 同 session_uid 若可能属于不同用户，就必须把 user_uid 也包含进来。
    thread_id = f"{user_uid}:{session_uid}"
    if len(thread_id) > 255:
        raise ValueError("user_uid 与 session_uid 组成的 thread_id 不能超过 255 个字符")
    return {"configurable": {"thread_id": thread_id}}

def chat(user_input: str, session_uid: str, user_uid: str,graph: StateGraph) -> str:
    """只提交本轮输入；历史读取、状态合并和持久化均由 PostgresSaver 完成。"""
    config = _thread_config(user_uid=user_uid, session_uid=session_uid)

    # from_conn_string 是上下文管理器。连接在 with 内保持可用，离开时自动关闭。
    # 调用方假定 checkpoint 表已经存在，这里不再检查或创建。
    with PostgresSaver.from_conn_string(CHECKPOINT_CONNINFO) as checkpointer:
        agent = graph.compile(checkpointer=checkpointer)

        result = agent.invoke(
            {"messages": [HumanMessage(content=user_input)]},
            config=config,
        )

    reply = result["messages"][-1].content
    return reply if isinstance(reply, str) else str(reply)


def read(user_uid,session_uid):
    config = {
    "configurable": {
        "thread_id": f"{user_uid}:{session_uid}"
        }
    }

    with PostgresSaver.from_conn_string(CHECKPOINT_CONNINFO) as checkpointer:
        state = checkpointer.get(config)

        if state:
            # print(11111,state)
            for message in state["channel_values"]["messages"]:
                print(message.type, message.content)

if __name__ == "__main__":
    # setup() 执行官方迁移并创建 checkpoint 表。只在直接运行本文件时做一次。
    with PostgresSaver.from_conn_string(CHECKPOINT_CONNINFO) as checkpointer:
        checkpointer.setup()
    # demo_session_uid = "1212"
    # demo_user_uid = "121212"
    # read(demo_user_uid,demo_session_uid)
