from fastapi import APIRouter

from api.v1 import userApi, workOrderApi
from api.v1 import roleApi

api_router = APIRouter()

api_router.include_router(userApi.router)
api_router.include_router(workOrderApi.router)
api_router.include_router(roleApi.router)
