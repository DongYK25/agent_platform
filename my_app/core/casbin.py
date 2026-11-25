from pathlib import Path

import casbin
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from common import role_data
from core.jwt import error_content, is_public


_CORE_DIR = Path(__file__).resolve().parent
_MODEL_PATH = _CORE_DIR / "casbin_model.conf"
_POLICY_PATH = _CORE_DIR / "casbin_policy.csv"

casbin_enforcer = casbin.Enforcer(str(_MODEL_PATH), str(_POLICY_PATH))


class CasbinAuthorizationMiddleware(BaseHTTPMiddleware):
    """根据当前用户角色、请求路径和 HTTP 方法检查访问权限。"""

    async def dispatch(self, request: Request, call_next) -> Response:
        if is_public(request.method, request.url.path):
            return await call_next(request)

        # JWT 中间件已经完成 token 校验并保存了解析结果。
        role_id = request.state.token_data.get("role_id")
        if role_id is None:
            return JSONResponse(
                status_code=401,
                content=error_content(401, "token 中缺少用户角色"),
                headers={"WWW-Authenticate": "Bearer"},
            )

        role = role_data.LOCATION_ROLE.get(role_id)
        if role is None:
            return JSONResponse(
                status_code=403,
                content=error_content(403, "用户角色不存在或已被删除"),
            )

        allowed = casbin_enforcer.enforce(
            role,
            request.url.path,
            request.method.upper(),
        )
        if not allowed:
            return JSONResponse(
                status_code=403,
                content=error_content(403, "无权限"),
            )

        return await call_next(request)
