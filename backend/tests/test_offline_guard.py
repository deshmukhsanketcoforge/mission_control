"""The test suite itself must stay offline."""

import os
import socket

import pytest


def test_network_connections_are_blocked():
    with pytest.raises(RuntimeError, match="Network access"):
        socket.create_connection(("example.com", 80))


def test_api_keys_are_not_available():
    assert "ANTHROPIC_API_KEY" not in os.environ
    assert "ANTHROPIC_AUTH_TOKEN" not in os.environ
