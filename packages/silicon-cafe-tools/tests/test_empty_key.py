"""Hermetic tests: None, empty, and whitespace-only keys count as no key.

Every test replaces the module-level opener with a recorder that always
fails at the transport layer, and neutralises the retry sleep, so no real
socket is opened and nothing is written to the store.
"""

import urllib.error

import pytest

import silicon_cafe_tools.client as client


class _RecordingOpener:
    """Stands in for ``client._OPENER``: records each Request, then fails."""

    def __init__(self):
        self.requests = []

    def open(self, request, timeout=None):
        self.requests.append(request)
        raise urllib.error.URLError("down")


def _patch_client(monkeypatch):
    """Install the fake opener and a no-op sleep; return the opener."""
    opener = _RecordingOpener()
    monkeypatch.setattr(client, "_OPENER", opener)
    monkeypatch.setattr(client.time, "sleep", lambda *args, **kwargs: None)
    return opener


def _has_authorization(request):
    """True if the request carries an Authorization header, any casing."""
    return any(str(name).lower() == "authorization" for name in request.headers)


def test_empty_env_key_is_anonymous_and_retried(monkeypatch):
    monkeypatch.setenv("TEA_API_KEY", "")
    opener = _patch_client(monkeypatch)

    with pytest.raises(RuntimeError):
        client.get_install_info(3001)

    assert len(opener.requests) == 2
    assert not any(_has_authorization(request) for request in opener.requests)


def test_whitespace_explicit_key_is_anonymous(monkeypatch):
    monkeypatch.delenv("TEA_API_KEY", raising=False)
    opener = _patch_client(monkeypatch)

    with pytest.raises(RuntimeError):
        client.get_install_info(3001, api_key="  ")

    assert len(opener.requests) == 2
    assert not any(_has_authorization(request) for request in opener.requests)
