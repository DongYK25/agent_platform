

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    """简单的接口调用ai"""
    msg: str = Field(description="用户消息")


class AgentResponse(BaseModel):
    """模型回复"""
    msg: str = Field(description="模型回复")
