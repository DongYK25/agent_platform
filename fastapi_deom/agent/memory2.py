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
    print(1111,state["messages"])
    ai_message = AIMessage(content=response.content)
    print(f"\nAI: {response.content}")
    # print("CURRENT STATE: ", list(state["messages"]) + [ai_message])
    return {"messages": [ai_message]}

graph = StateGraph(AgentState)
graph.add_node("process", process)
graph.add_edge(START, "process")
graph.add_edge("process", END)
agent = graph.compile(checkpointer=MemorySaver())
THREAD_CONFIG = {"configurable": {"thread_id": "demo"}}


def chat(user_input: str) -> str:
    """只送入本轮用户消息；同一 thread 的历史由检查点和 add_messages 合并。"""
    result = agent.invoke(
        {"messages": [HumanMessage(content=user_input)]},
        config=THREAD_CONFIG,
    )
    print("chat state:", result)
    reply = result["messages"][-1].content
    return reply if isinstance(reply, str) else str(reply)

def _save_log() -> None:
    snapshot = agent.get_state(THREAD_CONFIG)
    messages = list((snapshot.values or {}).get("messages") or [])
    with open("logging2.txt", "w", encoding="utf-8") as file:
        file.write("Your Conversation Log:\n")

        for message in messages:
            if isinstance(message, HumanMessage):
                file.write(f"You: {message.content}\n")
            elif isinstance(message, AIMessage):
                file.write(f"AI: {message.content}\n\n")
        file.write("End of Conversation")

    print("Conversation saved to logging2.txt")


if __name__ == "__main__":
    user_input = input("Enter: ")
    while user_input != "exit":
        chat(user_input)
        user_input = input("Enter: ")
    _save_log()
