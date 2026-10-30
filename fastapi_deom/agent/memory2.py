import os
from pathlib import Path
from typing import TypedDict, List, Union
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

class AgentState(TypedDict):
    messages: List[Union[HumanMessage, AIMessage]]

llm = ChatOpenAI(
    model=os.getenv("DEEPSEEK_MODEL"),
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

conversation_history: List[Union[HumanMessage, AIMessage]] = []


def chat(user_input: str) -> str:
    """把一条用户消息送进图，并沿用进程内的对话历史。"""
    global conversation_history
    conversation_history.append(HumanMessage(content=user_input))
    result = agent.invoke({"messages": conversation_history})
    conversation_history = result["messages"]
    reply = conversation_history[-1].content
    return reply if isinstance(reply, str) else str(reply)


def _save_log() -> None:
    with open("logging.txt", "w", encoding="utf-8") as file:
        file.write("Your Conversation Log:\n")

        for message in conversation_history:
            if isinstance(message, HumanMessage):
                file.write(f"You: {message.content}\n")
            elif isinstance(message, AIMessage):
                file.write(f"AI: {message.content}\n\n")
        file.write("End of Conversation")

    print("Conversation saved to logging.txt")


if __name__ == "__main__":
    user_input = input("Enter: ")
    while user_input != "exit":
        chat(user_input)
        user_input = input("Enter: ")
    _save_log()