import pytest


def test_file_report_saves_all_fields(client, valid_report):
    r = client.post("/api/reports", json=valid_report)
    assert r.status_code == 201
    body = r.json()
    for key, value in valid_report.items():
        assert body[key] == value
    assert body["id"] >= 1
    assert body["created_at"]


def test_list_reports_newest_first(client, valid_report):
    client.post("/api/reports", json={**valid_report, "name": "First"})
    client.post("/api/reports", json={**valid_report, "name": "Second"})
    names = [r["name"] for r in client.get("/api/reports").json()]
    assert names == ["Second", "First"]


def test_whitespace_is_trimmed(client, valid_report):
    r = client.post("/api/reports", json={**valid_report, "name": "  Ada  "})
    assert r.json()["name"] == "Ada"


@pytest.mark.parametrize("field", ["name", "station", "wind_knots", "temp_c", "fuel_pct", "note"])
def test_missing_field_is_rejected_with_message(client, valid_report, field):
    del valid_report[field]
    r = client.post("/api/reports", json=valid_report)
    assert r.status_code == 422
    assert r.json()["errors"][field] == "This field is required."
    assert client.get("/api/reports").json() == []


@pytest.mark.parametrize("field", ["name", "station", "note"])
def test_blank_text_is_rejected(client, valid_report, field):
    valid_report[field] = "   "
    r = client.post("/api/reports", json=valid_report)
    assert r.status_code == 422
    assert field in r.json()["errors"]


@pytest.mark.parametrize(
    "field,value,fragment",
    [
        ("wind_knots", -1, "Wind must be between"),
        ("wind_knots", 500, "Wind must be between"),
        ("temp_c", -200, "Temperature must be between"),
        ("temp_c", 100, "Temperature must be between"),
        ("fuel_pct", -0.1, "Fuel must be between"),
        ("fuel_pct", 100.1, "Fuel must be between"),
    ],
)
def test_out_of_range_readings_are_rejected(client, valid_report, field, value, fragment):
    valid_report[field] = value
    r = client.post("/api/reports", json=valid_report)
    assert r.status_code == 422
    assert fragment in r.json()["errors"][field]


@pytest.mark.parametrize("field", ["wind_knots", "temp_c", "fuel_pct"])
def test_non_numeric_reading_is_rejected(client, valid_report, field):
    valid_report[field] = "windy"
    r = client.post("/api/reports", json=valid_report)
    assert r.status_code == 422
    assert r.json()["errors"][field] == "Must be a number."


def test_boundary_values_are_accepted(client, valid_report):
    # Launch-limit edges (25 kt, 4 C, 98 and 100 %) are valid input.
    for wind, temp, fuel in [(25, 4, 98), (25.01, 3.99, 97.99), (0, -90, 100)]:
        r = client.post(
            "/api/reports",
            json={**valid_report, "wind_knots": wind, "temp_c": temp, "fuel_pct": fuel},
        )
        assert r.status_code == 201


def test_long_note_is_rejected(client, valid_report):
    valid_report["note"] = "x" * 2001
    r = client.post("/api/reports", json=valid_report)
    assert r.status_code == 422
    assert "at most 2000" in r.json()["errors"]["note"]
