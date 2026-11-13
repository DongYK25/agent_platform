import os
from pathlib import Path
from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

llm = ChatOpenAI(
    model=os.getenv("DEEPSEEK_MODEL") or "deepseek-v4-flash",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)


def process(state: AgentState) -> dict:
    """只返回这一轮的 AI 消息，交给 add_messages 追加，避免整表再拼一次。"""
    response = llm.invoke(state["messages"])
    ai_message = AIMessage(content=response.content)
    # print(111,state)
    # print(222,ai_message)
    # print(333,response.content)
    print(f"\nAI: {response.content}")
    return {"messages": [ai_message]}

graph = StateGraph(AgentState)
graph.add_node("process", process)
graph.add_edge(START, "process")
graph.add_edge("process", END)
agent = graph.compile()

from .db import add_message,get_history_message
def chat_api(user_input: str,session_uid: str,user_uid: str) -> str:
    """只送入本轮用户消息；同一 thread 的历史由检查点和 add_messages 合并。"""
    history_messages,sequence_no = get_history_message(session_uid=session_uid,user_uid=user_uid)
    now_user_message = HumanMessage(content=user_input)
    history_messages.append(now_user_message)
    result = agent.invoke({"messages": history_messages})
    # print("chat state:", result)
    reply = result["messages"][-1].content
    user_message_dict = {
        "user_uid": user_uid,
        "session_uid": session_uid,
        "sequence_no": sequence_no+1,
        "role": "user",
        "content": user_input,
    }
    ai_message_dict = {
        "user_uid": user_uid,
        "session_uid": session_uid,
        "sequence_no": sequence_no+2,
        "role": "assistant",
        "content": reply,
    }
    add_message([user_message_dict,ai_message_dict])
    return reply 


if __name__ == "__main__":
    user_input = input("Enter: ")
    while user_input != "exit":
        chat_api(user_input,session_uid="d7f06fd9-9f85-f255-0482-1a2a721ceec1",user_uid='61cc1d3b-d34d-8154-bc0e-fcf25eb7eb56')
        user_input = input("Enter: ")
