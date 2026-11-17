"""Filing, reading and approving reports through the API."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db import make_engine
from app.main import create_app
from app.models import Analysis
from tests.helpers import INJECTION_NOTE, pipeline_fake

HIT = {"flagged": True, "reason": "The note tells the system to mark the report GO."}


def app_client(db_url, fake):
    engine = make_engine(db_url)
    return TestClient(create_app(engine, serve_frontend=False, llm_client=fake)), engine


@pytest.fixture
def api(db_url):
    client, engine = app_client(db_url, pipeline_fake())
    with client:
        yield client, engine


def file(client, report, **overrides):
    r = client.post("/api/reports", json={**report, **overrides})
    assert r.status_code == 201, r.text
    return r.json()["id"]


# --- detail ----------------------------------------------------------------
def test_filing_runs_the_pipeline_and_the_detail_shows_everything(api, valid_report):
    client, _ = api
    rid = file(client, valid_report)
    d = client.get(f"/api/reports/{rid}").json()

    assert d["id"] == rid and d["note"] == valid_report["note"]
    a = d["analysis"]
    assert a["status"] == "pending_approval"
    assert a["verdict"] == "go"
    assert a["brief_by_minutes"] == 15
    assert a["briefing"] == "Draft briefing."
    assert a["total_cost_usd"] == "0.005895"
    assert [t["step"] for t in d["trace"]][0] == "limits"
    sort = next(t for t in d["trace"] if t["step"] == "sort")
    assert sort["input_tokens"] == 1000 and sort["cost_usd"] == "0.00035"


def test_unknown_report_is_404(api):
    client, _ = api
    assert client.get("/api/reports/999").status_code == 404


def test_list_shows_status_verdict_and_cost(api, valid_report):
    client, _ = api
    rid = file(client, valid_report, wind_knots=30)
    (item,) = client.get("/api/reports").json()
    assert item["id"] == rid
    assert item["status"] == "pending_approval"
    assert item["verdict"] == "no_go"
    assert item["brief_by_minutes"] == 5
    assert item["needs_review"] is False
    assert item["total_cost_usd"] == "0.005895"


def test_an_injection_note_end_to_end(db_url, valid_report):
    client, _ = app_client(db_url, pipeline_fake(injection=HIT))
    with client:
        rid = file(client, valid_report, note=INJECTION_NOTE, wind_knots=40)
        a = client.get(f"/api/reports/{rid}").json()["analysis"]
    assert a["verdict"] == "no_go"
    assert a["needs_review"] is True and "hidden_instructions" in a["review_reasons"]
    assert a["status"] == "pending_approval"


def test_a_failed_pipeline_still_returns_the_report_with_its_verdict(db_url, valid_report):
    fake = pipeline_fake()
    fake.clear("draft")
    fake.fail("draft", "service down")
    client, _ = app_client(db_url, fake)
    with client:
        rid = file(client, valid_report, fuel_pct=90)
        a = client.get(f"/api/reports/{rid}").json()["analysis"]
    assert a["status"] == "failed" and a["verdict"] == "no_go"


# --- approval --------------------------------------------------------------
def approve(client, rid, name="Dana Reyes"):
    return client.post(f"/api/reports/{rid}/approve", json={"approved_by": name})


def test_a_person_can_approve_a_pending_briefing(api, valid_report):
    client, _ = api
    rid = file(client, valid_report)
    r = approve(client, rid)
    assert r.status_code == 200
    a = r.json()
    assert a["status"] == "approved" and a["approved_by"] == "Dana Reyes"
    assert a["approved_at"]
    assert client.get(f"/api/reports/{rid}").json()["analysis"]["status"] == "approved"


def test_a_flagged_report_can_be_approved_by_a_person(db_url, valid_report):
    client, _ = app_client(db_url, pipeline_fake(injection=HIT))
    with client:
        rid = file(client, valid_report, note=INJECTION_NOTE)
        r = approve(client, rid)
    assert r.status_code == 200 and r.json()["needs_review"] is True


def test_approving_twice_is_refused(api, valid_report):
    client, _ = api
    rid = file(client, valid_report)
    assert approve(client, rid).status_code == 200
    again = approve(client, rid)
    assert again.status_code == 409 and "approved" in again.json()["errors"]["status"]


def test_a_failed_report_cannot_be_approved(db_url, valid_report):
    fake = pipeline_fake()
    fake.clear("draft")
    fake.fail("draft", "service down")
    client, _ = app_client(db_url, fake)
    with client:
        rid = file(client, valid_report)
        assert approve(client, rid).status_code == 409


def test_a_report_still_processing_cannot_be_approved(api, valid_report):
    client, engine = api
    rid = file(client, valid_report)
    with Session(engine) as s:
        a = s.exec(select(Analysis).where(Analysis.report_id == rid)).one()
        a.status = "processing"
        s.add(a)
        s.commit()
    assert approve(client, rid).status_code == 409


def test_approving_an_unknown_report_is_404(api):
    client, _ = api
    assert approve(client, 999).status_code == 404


@pytest.mark.parametrize("body", [{}, {"approved_by": ""}, {"approved_by": "   "}])
def test_approval_needs_a_name(api, valid_report, body):
    client, _ = api
    rid = file(client, valid_report)
    r = client.post(f"/api/reports/{rid}/approve", json=body)
    assert r.status_code == 422 and "approved_by" in r.json()["errors"]
    assert client.get(f"/api/reports/{rid}").json()["analysis"]["status"] == "pending_approval"


def test_filing_never_leaves_a_report_approved(api, valid_report):
    client, _ = api
    for _ in range(3):
        rid = file(client, valid_report)
        assert client.get(f"/api/reports/{rid}").json()["analysis"]["status"] != "approved"


# --- restart ---------------------------------------------------------------
def test_analysis_and_trace_survive_a_restart(db_url, valid_report):
    client, engine = app_client(db_url, pipeline_fake())
    with client:
        rid = file(client, valid_report)
        before = client.get(f"/api/reports/{rid}").json()
    engine.dispose()

    client2, _ = app_client(db_url, pipeline_fake())
    with client2:
        after = client2.get(f"/api/reports/{rid}").json()
    assert after == before
    assert len(after["trace"]) >= 8


def test_a_report_interrupted_by_a_restart_is_marked_failed(db_url, valid_report):
    client, engine = app_client(db_url, pipeline_fake())
    with client:
        rid = file(client, valid_report)
    with Session(engine) as s:
        a = s.exec(select(Analysis).where(Analysis.report_id == rid)).one()
        a.status = "processing"
        s.add(a)
        s.commit()
    engine.dispose()

    client2, _ = app_client(db_url, pipeline_fake())
    with client2:
        a = client2.get(f"/api/reports/{rid}").json()["analysis"]
    assert a["status"] == "failed" and "restart" in a["error"].lower()
