"""Suite-wide guards.

The transport tests never touch a real socket, and this fixture makes that a
hard guarantee rather than a convention: any attempt to open a TCP connection
from anywhere in the test run fails loudly instead of silently reaching out.
"""

import socket

import pytest


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Disable outbound TCP for every test, automatically."""

    def _refuse(*args, **kwargs):
        raise AssertionError("network access is disabled in tests")

    monkeypatch.setattr(socket, "create_connection", _refuse)
