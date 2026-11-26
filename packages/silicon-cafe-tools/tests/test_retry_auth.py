import urllib.error

import pytest

import silicon_cafe_tools.client as client


class _CountingOpener:
    """Opener stand-in that records calls and always fails at transport level."""

    def __init__(self):
        self.calls = 0

    def open(self, request, timeout=None):
        self.calls += 1
        raise urllib.error.URLError("down")


@pytest.fixture
def failing_opener(monkeypatch):
    opener = _CountingOpener()
    monkeypatch.setattr(client, "_OPENER", opener)
    monkeypatch.setattr(client.time, "sleep", lambda _seconds: None)
    return opener


def test_authenticated_install_not_retried(failing_opener):
    with pytest.raises(RuntimeError):
        client.get_install_info(3001, api_key="k")

    assert failing_opener.calls == 1


def test_anonymous_install_retried(failing_opener, monkeypatch):
    monkeypatch.delenv("TEA_API_KEY", raising=False)

    with pytest.raises(RuntimeError):
        client.get_install_info(3001)

    assert failing_opener.calls == 2
