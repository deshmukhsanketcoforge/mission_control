import socket

import pytest
from fastapi.testclient import TestClient

from app.db import make_engine
from app.main import create_app


@pytest.fixture
def db_url(tmp_path):
    return f"sqlite:///{tmp_path / 'test.db'}"


@pytest.fixture
def client(db_url):
    app = create_app(make_engine(db_url), serve_frontend=False)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def valid_report():
    return {
        "name": "Ada Lovelace",
        "station": "Propulsion-2",
        "wind_knots": 12.5,
        "temp_c": 18,
        "fuel_pct": 99.2,
        "note": "Valve V3 stuck for two seconds before opening.",
    }


@pytest.fixture(autouse=True)
def no_network_and_no_api_key(monkeypatch):
    """Tests must pass offline and without credentials.

    Any attempt to open a network connection fails the test, and API keys are
    removed from the environment so a real client can never be used by accident.
    """
    for var in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        monkeypatch.delenv(var, raising=False)

    def blocked(*args, **kwargs):
        raise RuntimeError("Network access is not allowed in tests.")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
