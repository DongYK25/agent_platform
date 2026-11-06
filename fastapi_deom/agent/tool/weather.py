import os
from pathlib import Path
from threading import Lock
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
# print(weather_api_url)

@tool
def get_weather(city: str):
    '''查询指定城市的实时天气。用户问到天气、气温、是否下雨、要不要带伞时使用。'''
    resp = requests.get(
        weather_api_url,
        params={"city": city},
        timeout=10,
    )
    return resp.json()

# print(get_weather("山东青岛"))

tools = [get_weather]

# class AgentState(TypedDict):
#     # add_messages 是一个 reducer（归并函数）。
#     # 新节点只需返回本轮新消息，LangGraph 会将其追加到已有 messages。
#     messages: Annotated[Sequence[BaseMessage], add_messages]
class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

llm = ChatOpenAI(
    model=os.getenv("DEEPSEEK_MODEL") or "deepseek-v4-flash",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)
# 不绑定的话，模型不知道 get_weather 的参数格式，只会把 <tool_call> 写进正文。
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
# app = graph.compile()


if __name__ == "__main__":
    # 生产项目通常在部署迁移步骤或 FastAPI startup/lifespan 中调用一次。
    # setup_checkpointer()
    from agent.memory.short_memory_checkpointer_class import ShortMemoryCheckpointer
    demo_session_uid = "1212"
    demo_user_uid = "121212"
    
    messages = ShortMemoryCheckpointer.read(demo_user_uid,demo_session_uid)
    # print(messages)

    # memory = ShortMemoryCheckpointer(graph)
    # while (user_input := input("Enter: ")) != "exit":
    #     print(
    #         "AI:",
    #         memory.chat(
    #             user_input,
    #             session_uid=demo_session_uid,
    #             user_uid=demo_user_uid,
    #         ),
    #     )