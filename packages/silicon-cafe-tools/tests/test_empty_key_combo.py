"""Hermetic test: an explicit empty api_key must win over the environment."""

import time
import urllib.error

import pytest

from silicon_cafe_tools import client


class _RecordingOpener:
    """Stand-in for ``client._OPENER``: records every request, always fails."""

    def __init__(self) -> None:
        self.requests: list[object] = []

    def _handle(self, request):
        self.requests.append(request)
        raise urllib.error.URLError("down")

    def __call__(self, request, *args, **kwargs):
        return self._handle(request)

    def open(self, request, *args, **kwargs):
        return self._handle(request)


def _header_names(request) -> set:
    return {
        str(name).lower()
        for name in (*request.headers, *request.unredirected_hdrs)
    }


def test_explicit_empty_key_overrides_env_and_stays_anonymous(monkeypatch):
    opener = _RecordingOpener()
    monkeypatch.setattr(client, "_OPENER", opener)
    monkeypatch.setattr(time, "sleep", lambda *a, **k: None)
    if hasattr(client, "time"):
        monkeypatch.setattr(client.time, "sleep", lambda *a, **k: None)
    monkeypatch.setenv("TEA_API_KEY", "env-key")

    with pytest.raises(RuntimeError):
        client.get_install_info(3001, api_key="")

    # allow_retry is True for an anonymous call, so the request is attempted twice.
    assert len(opener.requests) == 2

    for request in opener.requests:
        assert request.get_header("Authorization") is None
        assert "authorization" not in _header_names(request)
        assert "authorization" not in {
            str(name).lower() for name in request.headers
        }
