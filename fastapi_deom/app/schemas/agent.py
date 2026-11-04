

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    """往当前对话窗口发送一条消息。"""
    msg: str = Field(description="用户消息")
    session_uid: str = Field(description="当前对话窗口")


class SessionTitleUpdate(BaseModel):
    """修改对话窗口，目前只改标题。"""
    title: str = Field(min_length=1, max_length=200, description="对话标题")


class AgentResponse(BaseModel):
    """模型回复"""
    msg: str = Field(description="模型回复")
