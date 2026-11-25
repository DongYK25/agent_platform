from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from common import role_data
from core.cors import add_cors_middleware
from core.exceptions import register_exception_handlers

from core.database import register_orm
from core.config import settings
from api.router import api_router
from core.casbin import CasbinAuthorizationMiddleware
from core.jwt import JWTAuthMiddleware
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    async with register_orm:
        await role_data.update_location_role()
        yield


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# Starlette 后添加的中间件先执行，因此先注册 Casbin，再注册 JWT。
app.add_middleware(CasbinAuthorizationMiddleware)
app.add_middleware(JWTAuthMiddleware)
add_cors_middleware(app)
register_exception_handlers(app)

app.include_router(
    api_router,
    prefix="/api/v1"
)

# @app.get("/")
# async def root():
#     return {
#         "code": 200,
#         "message": "success",
#         "data": None,
#     }