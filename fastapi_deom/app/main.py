from contextlib import asynccontextmanager

from fastapi import FastAPI

from .database import create_db_and_tables
from .exception_handlers import register_exception_handlers
# from .internal import admin
from .middleware.auth import JWTAuthMiddleware
from .middleware.cors import add_cors_middleware
from .middleware.process_time import ProcessTimeMiddleware
from .routers import  users,work_order


@asynccontextmanager
async def lifespan(app: FastAPI):
    # create_db_and_tables()
    pass
    yield


app = FastAPI(title="FastAPI Demo", lifespan=lifespan)
register_exception_handlers(app)

app.add_middleware(ProcessTimeMiddleware)
app.add_middleware(JWTAuthMiddleware)
add_cors_middleware(app)

app.include_router(users.router)
app.include_router(work_order.router)
# app.include_router(admin.router, prefix="/admin", tags=["admin"])


@app.get("/")
async def root():
    return {"message": "Hello Bigger Applications!"}
