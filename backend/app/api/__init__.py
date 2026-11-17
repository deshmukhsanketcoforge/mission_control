from fastapi import APIRouter

from app.api import health, reports

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(reports.router)
