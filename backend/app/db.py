import os
from pathlib import Path

from sqlalchemy.engine import Engine
from sqlmodel import SQLModel, create_engine

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "mission_control.db"


def database_url() -> str:
    return os.environ.get("MISSION_CONTROL_DB_URL") or f"sqlite:///{DEFAULT_DB}"


def make_engine(url: str | None = None) -> Engine:
    url = url or database_url()
    if url.startswith("sqlite:///") and ":memory:" not in url:
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(url, connect_args={"check_same_thread": False})


def init_db(engine: Engine) -> None:
    SQLModel.metadata.create_all(engine)
