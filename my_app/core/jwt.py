from datetime import datetime, timedelta, timezone

import jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .config import settings
from schemas.commonSchemas import ResponseCommon
_SECRET = settings.JWT_SECRET_KEY
_ALGORITHM = settings.JWT_ALGORITHM
_EXPIRE_DAYS = settings.JWT_EXPIRE_DAYS

def error_content(code: int, msg: str, data=None) -> dict:
    return ResponseCommon(code=code, msg=msg, data=data).model_dump()

# 登录、注册不校验 token。其他所有接口都需要校验 token。
_PUBLIC_POST_PATHS = {
    "/users/register",
    "/api/v1/users/login",
}

_DOC_PREFIXES = ("/docs", "/redoc", "/openapi.json")


def create_token(id,uuid,username,role_id) -> str:
    """登录成功后调用。payload 放用户标识，不要放密码。"""
    # data = payload.copy()
    data = {"id": id, "uid": str(uuid), "username": username, "role_id": role_id}
    data["exp"] = datetime.now(timezone.utc) + timedelta(days=_EXPIRE_DAYS)
    return jwt.encode(data, _SECRET, algorithm=_ALGORITHM)


def _normalize(path: str) -> str:
    if len(path) > 1 and path.endswith("/"):
        return path.rstrip("/")
    return path


def is_public(method: str, path: str) -> bool:
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
        if is_public(request.method, request.url.path):
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

        user_id = payload.get("id")
        if not user_id:
            return _unauthorized("token 中缺少用户信息")

        request.state.token_data = payload
        return await call_next(request)
