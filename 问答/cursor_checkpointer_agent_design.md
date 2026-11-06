# Checkpointer agent design
_Exported on 11/5/2026 at 15:21:14 GMT+8 from Cursor (3.28.7)_

---

**User**

@fastapi_deom/agent/memory_api.py:1-71 这个上下文短期记忆，是我这个初学者用来学习加深影响而手动实现的，手动设计数据库表、读表并存表。但langgraph有checkpointer机制，不需要自己定义这些表，官方的 PostgresSaver 已经提供了数据库迁移和建表机制。
现在在这个 @fastapi_deom/agent/memory_checkpointer.py:1 文件中，使用checkpointer，设计一个同样流程的agent，用来对比我之前的@fastapi_deom/agent/memory_api.py ，并在代码上注释解释，也可以写个md文档用来教导我这个初学者如何是用checkpointer

---

**Cursor**

当前环境只有 LangGraph 基础包，`PostgresSaver` 的独立扩展包尚未安装。我会把依赖补齐，并按“首次建表/迁移”和“每轮聊天”分开设计，避免每次请求都重复执行迁移。

已完成：

- `memory_checkpointer.py`：使用 `PostgresSaver` 自动建表、迁移、恢复和保存上下文。
- `memory_checkpointer.md`：讲解 State、`add_messages`、`thread_id`、运行方式及与手动消息表的区别。
- `agent/requirements.txt`：补充 PostgreSQL checkpointer 依赖。

验证通过：模块导入、语法检查、图编译和 lint 均正常。未执行真实数据库迁移，首次运行时会自动执行：

```powershell
cd fastapi_deom
python -m agent.memory_checkpointer
```

需要注意：PostgresSaver 可替代“为 Agent 恢复上下文”的手写逻辑，但若需要消息分页、搜索、审计或报表，业务消息表仍有保留价值。

---

**User**

checkpoints如何设置压缩呢，在我之前的构想中，人类，ai，tool对话式直接能看到的，这样可以丢给大模型让他总结，自己调整一下读取总结最近的详细。那checkpointer是如何实现的呢?
这样吗class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    summary: str

---

**Cursor**

是的，你的思路正确：

```python
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    summary: str
```

但仅增加 `summary` 字段不会自动压缩。`PostgresSaver` 只负责保存/恢复状态；什么时候总结、怎样总结、删掉哪些旧消息，都需要在图中设计节点。

你当前的 `process()` 会把所有消息发送给模型：

```42:47:fastapi_deom/agent/memory_checkpointer.py
def process(state: AgentState) -> dict:
    """模型能看到 checkpointer 恢复出来的全部当前会话消息。"""
    response = llm.invoke(state["messages"])
    return {"messages": [response]}
```

## 推荐的压缩后状态

```python
from typing_extensions import NotRequired

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    summary: NotRequired[str]
```

其中：

- `summary`：较早对话的滚动摘要。
- `messages`：最近几轮的 Human、AI、Tool 原始消息。
- 每次模型输入：`摘要 + 最近详细消息`。

## 具体执行流程

例如消息超过 12 条后：

1. PostgresSaver 恢复 `summary + messages`。
2. `process` 用“摘要 + 最近消息”回答用户。
3. 判断消息是否超过阈值。
4. 超过阈值就进入 `summarize` 节点。
5. 总结模型根据“旧摘要 + 新消息”生成新摘要。
6. 使用 `RemoveMessage` 删除较早消息，保留最近几轮。
7. PostgresSaver 自动保存压缩后的新状态。

核心代码大致如下：

```python
from langchain_core.messages import (
    HumanMessage,
    RemoveMessage,
    SystemMessage,
)

def process(state: AgentState) -> dict:
    model_messages = []

    summary = state.get("summary")
    if summary:
        model_messages.append(
            SystemMessage(
                content=f"以下是较早对话的摘要：\n{summary}"
            )
        )

    model_messages.extend(state["messages"])
    response = llm.invoke(model_messages)

    return {"messages": [response]}
```

总结节点：

```python
def summarize_conversation(state: AgentState) -> dict:
    old_summary = state.get("summary", "")

    if old_summary:
        prompt = (
            f"这是之前的对话摘要：\n{old_summary}\n\n"
            "请结合以上摘要和最近对话，生成一份新的完整摘要。"
            "保留用户信息、重要事实、任务进度和未完成事项。"
        )
    else:
        prompt = (
            "请总结以上对话，保留用户信息、重要事实、"
            "任务进度和未完成事项。"
        )

    response = llm.invoke(
        list(state["messages"]) + [HumanMessage(content=prompt)]
    )

    # 保留最近4条详细消息，删除更早消息
    messages_to_delete = [
        RemoveMessage(id=message.id)
        for message in state["messages"][:-4]
    ]

    return {
        "summary": response.content,
        "messages": messages_to_delete,
    }
```

然后增加条件路由：

```python
def should_summarize(state: AgentState) -> str:
    if len(state["messages"]) >= 12:
        return "summarize"
    return END


graph_builder.add_node("process", process)
graph_builder.add_node("summarize", summarize_conversation)

graph_builder.add_edge(START, "process")
graph_builder.add_conditional_edges(
    "process",
    should_summarize,
    {
        "summarize": "summarize",
        END: END,
    },
)
graph_builder.add_edge("summarize", END)
```

## Checkpointer 实际保存什么

压缩前可能保存：

```text
messages = [Human1, AI1, Human2, AI2, Tool3, AI3, ...]
summary = ""
```

压缩后当前状态变成：

```text
summary = "用户叫小明，正在开发 FastAPI Agent……"
messages = [最近的 Human、AI、Tool、AI]
```

下一次调用时，PostgresSaver 会恢复这个状态，模型看到：

```text
System: 较早对话摘要……
Human: 最近问题
AI: 最近回答
Tool: 最近工具结果
Human: 本轮问题
```

这正是你所设想的“较早内容用摘要，最近内容保留详细”。

## Tool 消息需要特别注意

不能简单从任意位置切掉消息，因为工具调用通常是一个完整组合：

```text
HumanMessage
AIMessage(tool_calls=[...])
ToolMessage
AIMessage
```

不能只删除 `AIMessage(tool_calls)` 而留下 `ToolMessage`，也不能反过来，否则模型 API 可能报“tool message 没有对应 tool call”。

因此生产代码应：

- 按完整对话轮次裁剪。
- 保证 `AIMessage(tool_calls)` 和对应 `ToolMessage` 一起保留或一起删除。
- 最好按 token 数触发，而不是只按消息数量触发。

最后还要区分：压缩“当前图状态”不等于删除 PostgreSQL 中所有旧 checkpoint。旧快照可能仍然保存压缩前状态；如果要控制数据库容量，还需要单独设置 checkpoint 保留和清理策略。

---

**User**

那帮我实现一下总结压缩功能吧，压缩功能的方法可以新建一个py文件，然后memory_checkpointer.py可以调用这些方法，并解答我的疑惑：
1. @fastapi_deom/agent/memory_checkpointer.py:149-151 这个组合的数据我之前对话过几轮，没有加summary，如果加了之后，我再次对话会报错吗
2.如果设置压缩总结，数据应该不会删除，所以它是自动采用压缩+近期详细的组合吗，那如果我查 @fastapi_deom/agent/memory_checkpointer.py:130-144 历史的时候，怎么体现总结呢。
3.压缩总结根据消耗的Token，效果比轮次要好，是预测的Token消耗还是实际的token消耗呢，不同模型调用的token查询接口不一样吧
4.这个总结要建立新的数据库表吗

---

**Cursor**

我会把“压缩”设计成图中的独立总结节点：达到估算 token 阈值时，先把旧的完整对话轮次写入 `summary`，再用 `RemoveMessage` 从当前状态移除这些旧消息，并保留近期完整消息。旧 checkpoint 快照与当前状态是两回事，我也会让 `read()` 分别显示“历史摘要”和“近期原文”。

已实现总结压缩：

- 新增 `agent/memory_compression.py`
  - `summary + 近期消息`状态
  - 本地 token 估算
  - 按完整 Human/AI/Tool 轮次切分
  - 滚动总结
  - `RemoveMessage` 清理当前状态中的旧消息
- 更新 `memory_checkpointer.py`
  - 超过 6000 token 时先总结
  - 保留近期约 2000 token、至少两轮
  - 主模型自动接收“摘要 + 近期原文”
  - `read()` 分开显示摘要和近期消息
- 更新依赖。

配置可通过环境变量调整：

```dotenv
SUMMARY_TRIGGER_TOKENS=6000
SUMMARY_KEEP_RECENT_TOKENS=2000
SUMMARY_MIN_RECENT_TURNS=2
SUMMARY_MAX_OUTPUT_TOKENS=800
```

### 1. 旧会话没有 summary 会报错吗？

不会。

`summary` 被声明为可选字段：

```22:25:fastapi_deom/agent/memory_compression.py
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    summary: NotRequired[str]
```

读取时使用 `state.get("summary")`，旧 checkpoint 缺少它就按空摘要处理。超过阈值后才会首次生成摘要。

我用旧状态结构创建 checkpoint，再换成新状态结构继续对话，兼容性测试已通过。

### 2. 数据是否删除，模型如何组合？

需要区分两层：

- 当前状态：已经总结的旧 `messages` 会被 `RemoveMessage` 删除，留下 `summary + 近期消息`。
- 历史 checkpoint 快照：不会被回头改写，因此数据库中较早快照仍可能含完整旧消息。

主模型每次自动组合：

```text
SystemMessage：较早对话摘要
最近的 Human/AI/Tool 原文
本轮 HumanMessage
```

`read()` 现在显示：

```text
=== 较早对话摘要 ===
...

=== 近期详细消息 ===
human ...
ai ...
tool ...
```

它读取的是最新有效状态，不是所有历史快照。

### 3. 使用预测 token 还是实际 token？

目前使用 `count_tokens_approximately()` 在本地估算：

```48:61:fastapi_deom/agent/memory_compression.py
def approximate_message_tokens(messages: Sequence[BaseMessage]) -> int:
    """在本地按字符等信息估算 token，不会额外调用模型供应商接口。"""
    return count_tokens_approximately(messages)
```

原因是压缩决定发生在调用主模型之前，此时还没有本次调用的实际 usage。不同模型 tokenizer 确实不同，因此这是通用近似值，应给上下文窗口留下充足余量。

### 4. 需要新数据库表吗？

不需要。

`summary` 与 `messages` 都是图状态 channel，由 PostgresSaver 存入现有 checkpoint 表。只有需要单独搜索、分页、审计摘要时，才有必要建立业务摘要表。

已通过语法检查、图编译、压缩逻辑测试、旧 checkpoint 兼容测试和 lint。

