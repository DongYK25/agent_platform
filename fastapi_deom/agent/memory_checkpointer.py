"""使用 PostgresSaver 实现 LangGraph 的会话短期记忆。

与 memory_api.py 的区别：
1. 调用方每轮只传入一条新的 HumanMessage。
2. PostgresSaver 根据 thread_id 自动读取并保存整个图状态。
3. 不再手写“查询历史消息 / 计算 sequence_no / 插入两条消息”的代码。

运行方式（请从 fastapi_deom 目录运行）：
    python -m agent.memory_checkpointer
"""

import os
from pathlib import Path
from threading import Lock
from typing import Annotated, Sequence, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from psycopg.conninfo import make_conninfo

from app.database import DB_SCHEMA, database_url

load_dotenv(Path(__file__).resolve().parent / ".env")


class AgentState(TypedDict):
    # add_messages 是一个 reducer（归并函数）。
    # 新节点只需返回本轮新消息，LangGraph 会将其追加到已有 messages。
    messages: Annotated[Sequence[BaseMessage], add_messages]


llm = ChatOpenAI(
    model=os.getenv("DEEPSEEK_MODEL") or "deepseek-v4-flash",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)


def process(state: AgentState) -> dict:
    """模型能看到 checkpointer 恢复出来的全部当前会话消息。"""
    response = llm.invoke(state["messages"])
    # response 本身已经是 AIMessage，不需要再复制成一个新 AIMessage。
    return {"messages": [response]}


# 这里只“画图”，暂不 compile。
# compile 时传入 checkpointer，图才会获得读取和保存状态的能力。
graph_builder = StateGraph(AgentState)
graph_builder.add_node("process", process)
graph_builder.add_edge(START, "process")
graph_builder.add_edge("process", END)


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
# print("config11111",CHECKPOINT_CONNINFO)
# setup() 会执行官方提供的数据库迁移。它本身可重复执行，但没必要每轮都执行。
# Lock 用于防止同一 Python 进程首次收到多个请求时同时初始化。
_setup_lock = Lock()
_setup_finished = False


def _ensure_checkpointer_tables(checkpointer: PostgresSaver) -> None:
    global _setup_finished
    if _setup_finished:
        return

    with _setup_lock:
        if not _setup_finished:
            checkpointer.setup()
            _setup_finished = True


def setup_checkpointer() -> None:
    """显式创建/升级官方 checkpoint 表，可在应用启动阶段调用一次。"""
    with PostgresSaver.from_conn_string(CHECKPOINT_CONNINFO) as checkpointer:
        _ensure_checkpointer_tables(checkpointer)


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


def chat_api(user_input: str, session_uid: str, user_uid: str) -> str:
    """只提交本轮输入；历史读取、状态合并和持久化均由 PostgresSaver 完成。"""
    config = _thread_config(user_uid=user_uid, session_uid=session_uid)

    # from_conn_string 是上下文管理器。连接在 with 内保持可用，离开时自动关闭。
    with PostgresSaver.from_conn_string(CHECKPOINT_CONNINFO) as checkpointer:
        _ensure_checkpointer_tables(checkpointer)
        agent = graph_builder.compile(checkpointer=checkpointer)

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
    # 生产项目通常在部署迁移步骤或 FastAPI startup/lifespan 中调用一次。
    # setup_checkpointer()

    demo_session_uid = "d7f06fd9-9f85-f255-0482-1a2a721ceec1"
    demo_user_uid = "61cc1d3b-d34d-8154-bc0e-fcf25eb7eb56"
    read(demo_user_uid,demo_session_uid)
    while (user_input := input("Enter: ")) != "exit":
        print(
            "AI:",
            chat_api(
                user_input,
                session_uid=demo_session_uid,
                user_uid=demo_user_uid,
            ),
        )