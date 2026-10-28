import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class ProcessTimeMiddleware(BaseHTTPMiddleware):
    """把每个请求的处理耗时写到响应头 X-Process-Time。"""

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
