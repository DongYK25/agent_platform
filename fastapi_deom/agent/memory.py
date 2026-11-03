import os
from pathlib import Path
from typing import TypedDict, List, Union
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv
from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
load_dotenv(Path(__file__).resolve().parent / ".env")

class AgentState(TypedDict):
    messages: List[Union[HumanMessage, AIMessage]]

class AgentState2(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

llm = ChatOpenAI(
    model=os.getenv("DEEPSEEK_MODEL") or "deepseek-v4-flash",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)


def process(state: AgentState) -> AgentState:
    """This node will solve the request you input"""
    response = llm.invoke(state["messages"])

    state["messages"].append(AIMessage(content=response.content)) 
    print(f"\nAI: {response.content}")
    print("CURRENT STATE: ", state["messages"])

    return state

graph = StateGraph(AgentState)
graph.add_node("process", process)
graph.add_edge(START, "process")
graph.add_edge("process", END)
agent = graph.compile()


def process2(state: AgentState2) -> dict:
    """只返回这一轮的 AI 消息，交给 add_messages 追加，避免整表再拼一次。"""
    response = llm.invoke(state["messages"])
    ai_message = AIMessage(content=response.content)
    print(f"\nAI: {response.content}")
    print("CURRENT STATE2: ", list(state["messages"]) + [ai_message])
    return {"messages": [ai_message]}


graph2 = StateGraph(AgentState2)
graph2.add_node("process", process2)
graph2.add_edge(START, "process")
graph2.add_edge("process", END)
agent2 = graph2.compile(checkpointer=MemorySaver())
THREAD_CONFIG = {"configurable": {"thread_id": "chat2-demo"}}

conversation_history = []

def chat(user_input: str) -> str:
    """把一条用户消息送进图，并沿用进程内的对话历史。"""
    global conversation_history
    conversation_history.append(HumanMessage(content=user_input))
    result = agent.invoke({"messages": conversation_history})
    print("chat state:", result)
    conversation_history = result["messages"]
    reply = conversation_history[-1].content
    return reply if isinstance(reply, str) else str(reply)

def chat2(user_input: str) -> str:
    """只送入本轮用户消息；同一 thread 的历史由检查点和 add_messages 合并。"""
    result = agent2.invoke(
        {"messages": [HumanMessage(content=user_input)]},
        config=THREAD_CONFIG,
    )
    print("chat2 state:", result)
    reply = result["messages"][-1].content
    return reply if isinstance(reply, str) else str(reply)

def _messages_to_save():
    snapshot = agent2.get_state(THREAD_CONFIG)
    messages = (snapshot.values or {}).get("messages") or []
    return list(messages) or conversation_history

def _save_log() -> None:
    with open("logging.txt", "w", encoding="utf-8") as file:
        file.write("Your Conversation Log:\n")

        for message in _messages_to_save():
            if isinstance(message, HumanMessage):
                file.write(f"You: {message.content}\n")
            elif isinstance(message, AIMessage):
                file.write(f"AI: {message.content}\n\n")
        file.write("End of Conversation")

    print("Conversation saved to logging.txt")


if __name__ == "__main__":
    user_input = input("Enter: ")
    while user_input != "exit":
        chat2(user_input)
        user_input = input("Enter: ")
    _save_log()