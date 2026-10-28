from contextlib import asynccontextmanager

from fastapi import FastAPI

from .database import create_db_and_tables
from .internal import admin
from .middleware.cors import add_cors_middleware
from .middleware.process_time import ProcessTimeMiddleware
from .routers import items, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title="FastAPI Demo", lifespan=lifespan)

app.add_middleware(ProcessTimeMiddleware)
add_cors_middleware(app)

app.include_router(users.router)
app.include_router(items.router)
app.include_router(admin.router, prefix="/admin", tags=["admin"])


@app.get("/")
async def root():
    return {"message": "Hello Bigger Applications!"}
