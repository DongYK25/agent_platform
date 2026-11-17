
from langgraph.checkpoint.postgres import PostgresSaver
from fastapi_deom.agent.baseConfig import get_connection_info
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, START, END, tool

def thread_config(user_uid: str, session_uid: str) -> dict:
    """同一用户、同一会话必须始终得到同一个 thread_id。"""
    if not user_uid or not session_uid:
        raise ValueError("user_uid 和 session_uid 不能为空")

    # thread_id 就是 checkpointer 查找会话状态的键。
    # 同 session_uid 若可能属于不同用户，就必须把 user_uid 也包含进来。
    thread_id = f"{user_uid}:{session_uid}"
    if len(thread_id) > 255:
        raise ValueError("user_uid 与 session_uid 组成的 thread_id 不能超过 255 个字符")
    return {"configurable": {"thread_id": thread_id}}

class ShortMemoryCheckpointer:
    """按用户会话读写 LangGraph 短期记忆。调用前假定 checkpoint 表已经存在。"""
    
    def __init__(self, graph: StateGraph) -> None:
        self.graph = graph
    _conninfo = get_connection_info()
    def chat(self, user_input: str, session_uid: str, user_uid: str) -> str:
        """只提交本轮输入；历史读取、状态合并和持久化均由 PostgresSaver 完成。"""
        config = thread_config(user_uid=user_uid, session_uid=session_uid)

        # from_conn_string 是上下文管理器。连接在 with 内保持可用，离开时自动关闭。
        # checkpointer 绑定这条连接，所以必须在 with 内 compile。
        with PostgresSaver.from_conn_string(self._conninfo) as checkpointer:
            agent = self.graph.compile(checkpointer=checkpointer)
            result = agent.invoke(
                {"messages": [HumanMessage(content=user_input)]},
                config=config,
            )

        reply = result["messages"][-1].content
        return reply if isinstance(reply, str) else str(reply)
    @classmethod
    def read(cls, user_uid: str, session_uid: str) -> list[BaseMessage]:
        """读取该用户在该会话中已保存的消息。没有记录时返回空列表。"""
        config = thread_config(user_uid=user_uid, session_uid=session_uid)

        with PostgresSaver.from_conn_string(cls._conninfo) as checkpointer:
            state = checkpointer.get(config)

        if not state:
            return []
        messages = state["channel_values"].get("messages",[])
        for message in messages:
            print(message.type, message.content)
        return list(messages)

    @classmethod
    def filter_display_messages(cls,messages: list[BaseMessage]) -> list[BaseMessage]:
        """过滤出适合前端展示的对话消息。应该用不到"""
        result = []

        for message in messages:
            if isinstance(message, HumanMessage):
                result.append(message)

            elif isinstance(message, AIMessage):
                # 排除工具调用消息
                if not message.tool_calls:
                    result.append(message)

        return result

    @classmethod
    def setup(cls) -> None:
        """执行官方迁移并创建 checkpoint 表。"""
        with PostgresSaver.from_conn_string(cls._conninfo) as checkpointer:
            checkpointer.setup()
if __name__ == "__main__":
    # 只在直接运行本文件时建表。业务侧调用 chat / read 时假定表已经存在。
    ShortMemoryCheckpointer.setup()
