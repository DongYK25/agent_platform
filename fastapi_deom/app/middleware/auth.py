from datetime import datetime, timedelta, timezone

import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from ..config import load_config
from ..exception_handlers import error_content

_cfg = load_config()
_SECRET = _cfg["JWT_SECRET"]
_ALGORITHM = _cfg.get("JWT_ALGORITHM", "HS256")
_EXPIRE_DAYS = int(_cfg.get("JWT_EXPIRE_DAYS", 1))

# 登录、注册不校验 token。登录接口还没写，路径先留在这里。
_PUBLIC_POST_PATHS = {
    "/users",  # 注册：POST /users/
    "/users/register",
    "/login",
    "/users/login",
    "/agent/chat",
}

_DOC_PREFIXES = ("/docs", "/redoc", "/openapi.json")


def create_token(payload: dict) -> str:
    """登录成功后调用。payload 放用户标识，不要放密码。"""
    data = payload.copy()
    data["exp"] = datetime.now(timezone.utc) + timedelta(days=_EXPIRE_DAYS)
    return jwt.encode(data, _SECRET, algorithm=_ALGORITHM)


def _normalize(path: str) -> str:
    if len(path) > 1 and path.endswith("/"):
        return path.rstrip("/")
    return path


def _is_public(method: str, path: str) -> bool:
    if method == "OPTIONS":
        return True
    normalized = _normalize(path)
    if normalized.startswith(_DOC_PREFIXES):
        return True
    return method == "POST" and normalized in _PUBLIC_POST_PATHS


def _unauthorized(detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content=error_content(401, detail),
        headers={"WWW-Authenticate": "Bearer"},
    )


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """除登录、注册和文档外，请求必须带 Authorization: Bearer <token>。"""

    async def dispatch(self, request: Request, call_next) -> Response:
        if _is_public(request.method, request.url.path):
            return await call_next(request)

        authorization = request.headers.get("Authorization")
        if not authorization or not authorization.lower().startswith("bearer "):
            return _unauthorized("未提供 token")

        token = authorization.split(" ", 1)[1].strip()
        if not token:
            return _unauthorized("未提供 token")

        try:
            payload = jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
        except jwt.ExpiredSignatureError:
            return _unauthorized("token 已过期")
        except jwt.InvalidTokenError:
            return _unauthorized("token 无效")

        request.state.token_data = payload
        return await call_next(request)
