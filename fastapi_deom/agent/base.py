import os
from pathlib import Path
from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage,AnyMessage
from langchain_openai import ChatOpenAI
# from langgraph.graph import StateGraph, START, END
# from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

llm = ChatOpenAI(
    model=os.getenv("DEEPSEEK_MODEL") or "deepseek-v4-flash",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)
