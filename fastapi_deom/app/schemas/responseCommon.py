from typing import Any

from pydantic import BaseModel, Field


class ResponseCommon(BaseModel):
    """通用返回体，包含 code、msg、data。"""

    code: int = Field(description="业务状态码")
    msg: str = Field(description="提示信息")
    data: Any = Field(default=None, description="返回数据")

    @classmethod
    def success(cls, data: Any = None, msg: str = "success", code: int = 200) -> "ResponseCommon":
        return cls(code=code, msg=msg, data=data)

    @classmethod
    def failed(cls, msg: str = "failed", code: int = 400, data: Any = None) -> "ResponseCommon":
        return cls(code=code, msg=msg, data=data)

    @classmethod
    def error(cls, msg: str = "error", code: int = 500, data: Any = None) -> "ResponseCommon":
        return cls(code=code, msg=msg, data=data)
