import os
from pathlib import Path
from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage,AnyMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
# from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
from langgraph.prebuilt import ToolNode
from psycopg.conninfo import make_conninfo
load_dotenv(Path(__file__).resolve().parent / ".env")

class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

llm = ChatOpenAI(
    model=os.getenv("DEEPSEEK_MODEL") or "deepseek-v4-flash",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)


def get_connection_info() -> str:
    """读取数据库连接地址，并指定数据表所在的 schema。"""
    database_url = os.getenv("DATABASE_URL")
    return make_conninfo(
        database_url,
        options=f"-csearch_path=agent",
    )

def build_graph() -> StateGraph:
    @tool
    def test_tool():
        return "test_tool"
    tools = [test_tool]
    llm_with_tools = llm.bind_tools(tools)

    def process(state: AgentState) -> dict:
        """模型能看到 checkpointer 恢复出来的全部当前会话消息。"""
        system_prompt = SystemMessage(content=
            "你是一个ai对话助手，你可以使用工具查询天气信息，请根据用户的问题使用工具查询天气信息，并返回天气信息；如果用户没有提及城市，则使用默认城市山东青岛。"
        )
        response = llm_with_tools.invoke([system_prompt] + list(state["messages"]))
        return {"messages": [response]}

    def common_tool_should_continue(state: AgentState): 
        messages = state["messages"]
        last_message = messages[-1]
        if not last_message.tool_calls: 
            return "end"
        else:
            return "continue"
        
    graph = StateGraph(AgentState)
    ####节点####
    graph.add_node("process", process)
    tool_node = ToolNode(tools=tools)
    graph.add_node("tools", tool_node)

    ####边####
    graph.add_edge(START, "process") ###start -> process

    graph.add_conditional_edges(
        "process",     #process -> common_tool_should_continue
        common_tool_should_continue,
        {
            "continue": "tools", ###common_tool_should_continue 判断进入 tools 节点
            "end": END, ###common_tool_should_continue 判断进入 END 节点
        },
    )    
    graph.add_edge("tools", "process") ###tools -> process
    return graph
