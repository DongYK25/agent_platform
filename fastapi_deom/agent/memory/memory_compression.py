"""LangGraph 对话状态的“滚动摘要 + 近期原文”压缩工具。

这里压缩的是模型下一轮要读取的当前状态，不是压缩 PostgreSQL 文件。
PostgresSaver 只负责保存状态；何时总结、保留哪些消息由本模块决定。
"""

from dataclasses import dataclass
from typing import Annotated, Callable, Literal, Sequence, TypedDict

from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
)
from langchain_core.messages.utils import count_tokens_approximately
from langchain_core.runnables import Runnable
from langgraph.graph.message import add_messages
from typing_extensions import NotRequired


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    # 旧 checkpoint 中没有 summary 也没关系，读取时使用 state.get("summary")。
    summary: NotRequired[str]


@dataclass(frozen=True)
class SummaryConfig:
    """总结触发阈值和压缩后保留的近期原文大小。"""

    trigger_tokens: int = 6000
    keep_recent_tokens: int = 2000
    min_recent_turns: int = 2

    def __post_init__(self) -> None:
        if self.trigger_tokens <= 0:
            raise ValueError("trigger_tokens 必须大于 0")
        if self.keep_recent_tokens <= 0:
            raise ValueError("keep_recent_tokens 必须大于 0")
        if self.keep_recent_tokens >= self.trigger_tokens:
            raise ValueError("keep_recent_tokens 必须小于 trigger_tokens")
        if self.min_recent_turns <= 0:
            raise ValueError("min_recent_turns 必须大于 0")


def approximate_message_tokens(messages: Sequence[BaseMessage]) -> int:
    """在本地按字符等信息估算 token，不会额外调用模型供应商接口。"""
    return count_tokens_approximately(messages)


def approximate_state_tokens(state: AgentState) -> int:
    """估算下一次模型输入中的“摘要 + 近期消息”token 数。"""
    messages = list(state.get("messages") or [])
    summary = state.get("summary")
    if summary:
        messages.insert(
            0,
            SystemMessage(content=f"较早对话摘要：\n{summary}"),
        )
    return approximate_message_tokens(messages)


def build_model_messages(state: AgentState) -> list[BaseMessage]:
    """将当前状态转换为模型实际读取的“摘要 + 近期详细消息”组合。"""
    model_messages: list[BaseMessage] = []
    summary = state.get("summary")
    if summary:
        model_messages.append(
            SystemMessage(
                content=(
                    "以下是较早对话的摘要。请把它作为对话背景，"
                    "并优先遵循后面的近期消息：\n\n"
                    f"{summary}"
                )
            )
        )
    model_messages.extend(state["messages"])
    return model_messages


def route_before_model(
    state: AgentState,
    config: SummaryConfig,
) -> Literal["summarize", "process"]:
    """超过 token 阈值时，先总结再调用主模型。"""
    if approximate_state_tokens(state) >= config.trigger_tokens:
        return "summarize"
    return "process"


def _split_old_and_recent_messages(
    messages: Sequence[BaseMessage],
    config: SummaryConfig,
) -> tuple[list[BaseMessage], list[BaseMessage]]:
    """按完整 Human 对话轮次切分，避免拆散 AI tool_call 与 ToolMessage。

    每个 HumanMessage 开启一轮；该消息之后的 AIMessage、ToolMessage 等都属于
    这一轮，直到下一个 HumanMessage。至少保留最后 min_recent_turns 轮。
    """
    message_list = list(messages)
    human_starts = [
        index
        for index, message in enumerate(message_list)
        if isinstance(message, HumanMessage)
    ]

    # 没有足够的完整轮次时不删除，避免产生无效消息序列。
    if len(human_starts) <= config.min_recent_turns:
        return [], message_list

    first_kept_turn = max(0, len(human_starts) - config.min_recent_turns)
    keep_start = human_starts[first_kept_turn]
    recent_messages = message_list[keep_start:]
    recent_tokens = approximate_message_tokens(recent_messages)

    # 在 token 预算允许时，再多保留若干完整轮次。
    for turn_index in range(first_kept_turn - 1, -1, -1):
        candidate_start = human_starts[turn_index]
        candidate_messages = message_list[candidate_start:keep_start]
        candidate_tokens = approximate_message_tokens(candidate_messages)
        if recent_tokens + candidate_tokens > config.keep_recent_tokens:
            break
        keep_start = candidate_start
        recent_messages = message_list[keep_start:]
        recent_tokens += candidate_tokens

    return message_list[:keep_start], recent_messages


def create_summary_node(
    model: Runnable,
    config: SummaryConfig,
) -> Callable[[AgentState], dict]:
    """创建可直接注册到 StateGraph 的总结节点。"""

    def summarize_conversation(state: AgentState) -> dict:
        old_messages, _recent_messages = _split_old_and_recent_messages(
            state["messages"],
            config,
        )

        # 例如只有一轮特别长的输入时，没有安全的旧轮次可删除。
        if not old_messages:
            return {}

        previous_summary = state.get("summary", "")
        summary_input: list[BaseMessage] = [
            SystemMessage(
                content=(
                    "你负责压缩对话记忆。请生成简洁、准确、可继续更新的摘要。"
                    "必须保留：用户身份与偏好、重要事实、明确决定、任务进度、"
                    "工具执行的重要结果、未完成事项。不要虚构信息。"
                )
            )
        ]
        if previous_summary:
            summary_input.append(
                HumanMessage(
                    content=f"这是已经存在的较早对话摘要：\n{previous_summary}"
                )
            )

        # 只总结即将删除的旧消息；近期消息继续以原文保留，避免重复总结。
        summary_input.extend(old_messages)
        summary_input.append(
            HumanMessage(
                content=(
                    "请把已有摘要与上面的旧对话合并成一份新的完整摘要。"
                    "直接输出摘要正文。"
                )
            )
        )
        response = model.invoke(summary_input)

        # add_messages 看到 RemoveMessage 后，会从“当前状态”删除对应消息。
        # 按完整轮次删除，因此不会把 tool_call 和 ToolMessage 拆开。
        removals = [
            RemoveMessage(id=message.id)
            for message in old_messages
            if message.id is not None
        ]
        return {
            "summary": (
                response.content
                if isinstance(response.content, str)
                else str(response.content)
            ),
            "messages": removals,
        }

    return summarize_conversation
