"""Demo sample data: valid, varied, and it never rots away from the API."""

import pytest
from fastapi.testclient import TestClient

from app.db import make_engine
from app.domain.limits import check_limits
from app.llm.demo import DemoLLMClient
from app.main import create_app
from app.schemas import ReportIn
from app.seed import SAMPLE_REPORTS, seed


class FakeApi:
    def __init__(self, existing=0):
        self.existing = existing
        self.filed = []

    def count(self):
        return self.existing + len(self.filed)

    def file(self, payload):
        self.filed.append(payload)


def verdict(sample):
    return check_limits(
        wind_knots=sample["wind_knots"], temp_c=sample["temp_c"], fuel_pct=sample["fuel_pct"]
    )


def test_every_sample_is_a_valid_report():
    for sample in SAMPLE_REPORTS:
        ReportIn(**sample)  # raises if the API would reject it


def test_samples_cover_go_and_no_go():
    verdicts = {verdict(s).verdict for s in SAMPLE_REPORTS}
    assert verdicts == {"go", "no_go"}


def test_samples_cover_each_limit_being_broken():
    broken = {v.field for s in SAMPLE_REPORTS for v in verdict(s).violations}
    assert broken == {"wind_knots", "temp_c", "fuel_pct"}


def test_samples_include_a_report_exactly_on_every_limit_and_one_just_past():
    on_limit = [s for s in SAMPLE_REPORTS if (s["wind_knots"], s["temp_c"], s["fuel_pct"]) == (25, 4, 98)]
    assert on_limit and verdict(on_limit[0]).verdict == "go"
    just_past = [s for s in SAMPLE_REPORTS if s["wind_knots"] == 25.01]
    assert just_past and verdict(just_past[0]).verdict == "no_go"


def test_samples_include_a_note_that_tries_to_give_instructions():
    assert any("ignore" in s["note"].lower() for s in SAMPLE_REPORTS)


def test_running_the_samples_through_the_app_flags_the_instruction_note(db_url):
    app = create_app(make_engine(db_url), serve_frontend=False, llm_client=DemoLLMClient())
    with TestClient(app) as client:
        for sample in SAMPLE_REPORTS:
            assert client.post("/api/reports", json=sample).status_code == 201
        items = client.get("/api/reports").json()

    assert len(items) == len(SAMPLE_REPORTS)
    assert all(i["status"] == "pending_approval" for i in items)  # none approved by seeding
    flagged = [i for i in items if i["needs_review"]]
    assert flagged and all("ignore" in i["note"].lower() for i in flagged)
    by_station = {i["station"]: i for i in items}
    assert by_station["Pad-1"]["verdict"] == "no_go"


def test_seed_files_every_sample():
    api = FakeApi()
    assert seed(api) == len(SAMPLE_REPORTS)
    assert api.filed == SAMPLE_REPORTS


def test_seed_does_not_add_duplicates_to_a_database_that_has_reports():
    api = FakeApi(existing=2)
    assert seed(api) == 0
    assert api.filed == []


def test_seed_can_be_forced():
    api = FakeApi(existing=2)
    assert seed(api, force=True) == len(SAMPLE_REPORTS)


@pytest.mark.parametrize("sample", SAMPLE_REPORTS, ids=lambda s: s["station"])
def test_each_sample_has_a_station_name_and_a_note(sample):
    assert sample["station"] and len(sample["note"].split()) >= 2
