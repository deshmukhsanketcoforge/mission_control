from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.db import init_db, make_engine
from app.models import Report
from app.schemas import ReportIn, ReportOut

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

REQUIRED_MESSAGE = "This field is required."


def _clean_message(error: dict) -> str:
    """Turn a pydantic error into one short sentence for the user."""
    kind = error.get("type", "")
    if kind == "missing":
        return REQUIRED_MESSAGE
    if kind == "string_too_short":
        return REQUIRED_MESSAGE
    if kind == "string_too_long":
        limit = error.get("ctx", {}).get("max_length")
        return f"Must be at most {limit} characters."
    if kind in ("float_parsing", "float_type", "finite_number"):
        return "Must be a number."
    msg = error.get("msg", "Invalid value.")
    return msg.removeprefix("Value error, ")


def create_app(engine: Engine | None = None, serve_frontend: bool = True) -> FastAPI:
    engine = engine or make_engine()
    init_db(engine)

    app = FastAPI(title="Mission Control")
    app.state.engine = engine

    def get_session():
        with Session(engine) as session:
            yield session

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError):
        errors: dict[str, str] = {}
        for err in exc.errors():
            loc = [p for p in err["loc"] if p != "body"]
            field = str(loc[0]) if loc else "body"
            errors.setdefault(field, _clean_message(err))
        return JSONResponse(status_code=422, content={"errors": errors})

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.post("/api/reports", response_model=ReportOut, status_code=201)
    def create_report(payload: ReportIn, session: Session = Depends(get_session)):
        report = Report(**payload.model_dump())
        session.add(report)
        session.commit()
        session.refresh(report)
        return report

    @app.get("/api/reports", response_model=list[ReportOut])
    def list_reports(session: Session = Depends(get_session)):
        return session.exec(select(Report).order_by(Report.id.desc())).all()

    if serve_frontend and FRONTEND_DIST.is_dir():
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

    return app


def app_factory() -> FastAPI:
    """Entry point for uvicorn: `uvicorn app.main:app_factory --factory`."""
    return create_app()
