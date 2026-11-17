"""Reports must survive a restart: a brand new app on the same database file."""

from fastapi.testclient import TestClient

from app.db import make_engine
from app.main import create_app


def test_reports_still_there_after_restart(db_url, valid_report):
    first_engine = make_engine(db_url)
    with TestClient(create_app(first_engine, serve_frontend=False)) as first:
        created = first.post("/api/reports", json=valid_report).json()
    first_engine.dispose()  # the "shutdown"

    second_engine = make_engine(db_url)  # the "restart"
    with TestClient(create_app(second_engine, serve_frontend=False)) as second:
        reports = second.get("/api/reports").json()

    assert [r["id"] for r in reports] == [created["id"]]
    assert reports[0]["note"] == valid_report["note"]
    assert reports[0]["fuel_pct"] == valid_report["fuel_pct"]
