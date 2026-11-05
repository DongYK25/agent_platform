# 用 PostgresSaver 学习 LangGraph 短期记忆

对应示例：

- 手动实现：`memory_api.py`
- Checkpointer 实现：`memory_checkpointer.py`

## 1. Checkpointer 解决了什么问题

`memory_api.py` 的流程是：

1. 按 `user_uid + session_uid` 查询历史消息。
2. 将历史消息和本轮用户消息一起传给图。
3. 手动计算 `sequence_no`。
4. 手动保存用户消息和 AI 消息。

这样做有助于理解“上下文记忆”的本质：模型本身没有记忆，每次调用都必须再次提供历史消息。

使用 `PostgresSaver` 后，流程变为：

1. 为一次会话提供稳定的 `thread_id`。
2. 本轮只传入新的 `HumanMessage`。
3. LangGraph 自动加载该 thread 上一次保存的状态。
4. `add_messages` 将新消息追加到状态。
5. 图执行后，checkpointer 自动把新状态保存到 PostgreSQL。

因此，checkpointer 不是让大模型突然拥有记忆，而是替你完成“读取旧状态 → 合并新状态 → 保存新状态”。

## 2. 三个关键概念

### State

示例中的状态只有 `messages`：

```python
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
```

状态也可以包含其他字段，例如当前步骤、工具结果或业务审批状态。Checkpointer 保存的是图状态快照，不只是普通聊天记录。

### add_messages

它是 `messages` 字段的 reducer（归并函数）。节点返回：

```python
{"messages": [response]}
```

LangGraph 会把这条消息合并进已有状态。如果没有正确配置 reducer，新值可能覆盖旧值。

### thread_id

`thread_id` 是一段对话的标识：

```python
config = {
    "configurable": {
        "thread_id": f"{user_uid}:{session_uid}"
    }
}
```

- 相同 `thread_id`：继续之前的上下文。
- 不同 `thread_id`：创建互相隔离的新上下文。
- 不能只用 `user_uid`：否则该用户的所有会话会混在一起。
- 不能随每次请求随机生成：否则永远读取不到上一轮状态。

## 3. 安装与运行

先从 `fastapi_deom` 目录安装依赖：

```powershell
pip install -r requirements.txt
pip install -r agent/requirements.txt
```

确认 `config/app_dev.yaml` 中的 PostgreSQL 连接可用，然后运行：

```powershell
python -m agent.memory_checkpointer
```

第一次运行会调用：

```python
checkpointer.setup()
```

它会执行 `langgraph-checkpoint-postgres` 自带的迁移，创建或升级 checkpoint 所需的表。不要再用 SQLModel 手写这些官方表。

本项目设置了 `DB_SCHEMA: agent`，代码通过 PostgreSQL `search_path` 让官方表建在该 schema。对应 schema 必须已经存在，并且数据库用户要有建表权限。

## 4. 每轮调用时发生了什么

第一次调用：

```python
chat_api("我叫小明", session_uid="session-1", user_uid="user-1")
```

数据库里还没有该 thread 的状态。图收到用户消息，模型作答，随后 PostgresSaver 保存状态快照。

第二次调用：

```python
chat_api("我叫什么？", session_uid="session-1", user_uid="user-1")
```

调用方仍然只发送第二句话。执行图之前，PostgresSaver 会恢复 `session-1` 的状态，所以模型能同时看到第一轮和第二轮消息。

如果把 `session_uid` 改成 `session-2`，模型不会获得 `session-1` 的上下文。

## 5. 与手动消息表并不完全等价

手动设计的 `SessionMessage` 是业务消息表，适合：

- 后台逐条查询、分页和搜索聊天消息。
- 做消息撤回、审计、统计和报表。
- 给每条消息增加业务字段。

PostgresSaver 保存的是 LangGraph 状态快照，适合：

- 短期会话记忆。
- 中断后恢复图执行。
- human-in-the-loop。
- 查看历史状态和 time travel。
- 保存工具调用过程及其他状态字段。

所以“用了 PostgresSaver 就永远不需要业务消息表”并不准确。只为了让 Agent 延续上下文时，checkpointer 通常足够；如果产品还需要消息检索、审计或报表，可以同时保留一张业务消息表。

## 6. 在 FastAPI 中使用时的建议

示例为了容易学习，每次 `chat_api` 调用都会打开并关闭一个数据库连接。生产服务中建议：

1. 在部署迁移步骤或 FastAPI lifespan 中执行一次 `setup()`。
2. 使用 psycopg 连接池，避免每个请求重新建立连接。
3. 异步接口使用 `AsyncPostgresSaver` 和 `ainvoke()`。
4. 给 checkpoint 数据制定清理策略；长对话会持续增加快照和 token 数。
5. 不要把数据库密码直接写进代码或提交到 Git。

## 7. 常见误区

- `MemorySaver` 只存内存，进程重启后记录会消失。
- PostgresSaver 是短期、thread 范围的状态记忆，不是跨会话的用户长期记忆。
- Checkpointer 不会自动控制上下文长度。对话很长时仍需做消息裁剪、摘要或归档。
- `setup()` 是数据库迁移操作，不应在每轮请求中无条件重复执行。
- 更换 `thread_id` 相当于切换会话，不是清空同一会话。
