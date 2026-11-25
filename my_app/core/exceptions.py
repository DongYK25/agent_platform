from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from schemas.commonSchemas import ResponseCommon

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求参数校验失败时，统一返回 ResponseCommon 格式。"""
    return JSONResponse(
        status_code=422,
        content=ResponseCommon.failed(
            msg="参数校验失败",
            code=422,
            data=jsonable_encoder(exc.errors()),
        ).model_dump(),
    )

def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
