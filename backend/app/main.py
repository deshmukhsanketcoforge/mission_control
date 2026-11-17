from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy.engine import Engine

from app.api import api_router
from app.api.errors import register_error_handlers
from app.db import init_db, make_engine
from app.llm.base import LLMClient
from app.llm.factory import build_llm_client
from app.services import recover_interrupted

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


def create_app(
    engine: Engine | None = None,
    serve_frontend: bool = True,
    llm_client: LLMClient | None = None,
) -> FastAPI:
    engine = engine or make_engine()
    init_db(engine)
    recover_interrupted(engine)  # reports cut off by a restart are marked failed

    app = FastAPI(title="Mission Control")
    app.state.engine = engine
    app.state.llm_client = llm_client or build_llm_client()

    register_error_handlers(app)
    app.include_router(api_router)

    if serve_frontend and FRONTEND_DIST.is_dir():
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

    return app


def app_factory() -> FastAPI:
    """Entry point for uvicorn: `uvicorn app.main:app_factory --factory`."""
    return create_app()
