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


# --- the seed command reports the real problem -------------------------------------------

import io
import urllib.error

import app.seed as seed_module


def http_error(code):
    return urllib.error.HTTPError("http://x/api/reports", code, "Bad", {}, io.BytesIO(b'{"errors":{"note":"too long"}}'))


class BrokenApi:
    def __init__(self, error, existing=0, fail_after=0):
        self.error, self.existing, self.fail_after, self.filed = error, existing, fail_after, 0

    def count(self):
        if isinstance(self.error, Exception) and self.fail_after is None:
            raise self.error
        return self.existing

    def file(self, payload):
        if self.filed >= self.fail_after:
            raise self.error
        self.filed += 1


def run_main(monkeypatch, capsys, api):
    monkeypatch.setattr(seed_module, "HttpApi", lambda url: api)
    code = seed_module.main(["--url", "http://x"])
    return code, capsys.readouterr().out


def test_unreachable_app_says_it_could_not_reach_it(monkeypatch, capsys):
    api = BrokenApi(urllib.error.URLError("refused"), fail_after=0)
    code, out = run_main(monkeypatch, capsys, api)
    assert code == 1
    assert "Could not reach the app" in out and "make start" in out


def test_connection_refused_is_unreachable(monkeypatch, capsys):
    code, out = run_main(monkeypatch, capsys, BrokenApi(ConnectionRefusedError("nope")))
    assert code == 1 and "Could not reach the app" in out


@pytest.mark.parametrize("status", [422, 500])
def test_a_server_rejection_is_not_reported_as_unreachable(monkeypatch, capsys, status):
    code, out = run_main(monkeypatch, capsys, BrokenApi(http_error(status)))
    assert code == 1
    assert "Could not reach" not in out and "make start" not in out
    assert str(status) in out


def test_a_failure_on_the_count_call_names_the_status(monkeypatch, capsys):
    api = BrokenApi(http_error(500), fail_after=None)
    code, out = run_main(monkeypatch, capsys, api)
    assert code == 1 and "500" in out and "Could not reach" not in out


def test_a_failure_part_way_says_how_many_were_filed_and_how_to_retry(monkeypatch, capsys):
    api = BrokenApi(http_error(500), fail_after=3)
    code, out = run_main(monkeypatch, capsys, api)
    assert code == 1
    assert "3 of" in out and "--force" in out


def test_seed_error_carries_the_number_filed():
    api = BrokenApi(http_error(500), fail_after=2)
    with pytest.raises(seed_module.SeedError) as info:
        seed(api)
    assert info.value.filed == 2 and info.value.total == len(SAMPLE_REPORTS)
    assert isinstance(info.value.__cause__, urllib.error.HTTPError)


def test_a_successful_run_still_exits_zero(monkeypatch, capsys):
    code, out = run_main(monkeypatch, capsys, FakeApi())
    assert code == 0 and "Filed" in out
