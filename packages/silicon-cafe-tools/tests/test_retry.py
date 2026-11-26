"""Retry behaviour of ``silicon_cafe_tools.client._rpc_call``.

The client's module-level ``_OPENER`` is swapped for a counting fake, so
no socket is ever created and every test stays hermetic.
"""

import json
import urllib.error

import pytest

from silicon_cafe_tools import client


class _FakeResponse:
    """Minimal stand-in for the object urllib's opener hands back."""

    def __init__(self, body):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self._body


class _FakeOpener:
    """Opener double that replays a script of behaviours.

    Each behaviour is either an exception instance to raise or a callable
    taking the request and returning the raw response body. The final
    behaviour repeats once the script is exhausted, so a single-element
    script models a failure that never clears.
    """

    def __init__(self, *behaviours):
        assert behaviours, "need at least one behaviour"
        self._behaviours = behaviours
        self.call_count = 0

    def open(self, request, timeout=None):
        index = min(self.call_count, len(self._behaviours) - 1)
        behaviour = self._behaviours[index]
        self.call_count += 1
        if isinstance(behaviour, BaseException):
            raise behaviour
        return _FakeResponse(behaviour(request))


def _good_envelope(request):
    """Build a valid response that echoes the id of the request we got."""
    request_id = json.loads(request.data.decode("utf-8"))["id"]
    return json.dumps(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"structuredContent": {"total": 0, "results": []}},
        }
    ).encode("utf-8")


def _structured(result):
    """Return the structured content, whether or not it got unwrapped."""
    if isinstance(result, dict):
        return result.get("structuredContent", result)
    return result


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    """Keep the 0.5s retry delay out of the test run."""
    monkeypatch.setattr(client.time, "sleep", lambda seconds: None)


def test_transport_error_retried_once(monkeypatch):
    opener = _FakeOpener(urllib.error.URLError("down"), _good_envelope)
    monkeypatch.setattr(client, "_OPENER", opener)

    result = client.search_skills("x")

    assert _structured(result) == {"total": 0, "results": []}
    assert opener.call_count == 2


def test_http_error_not_retried(monkeypatch):
    opener = _FakeOpener(
        urllib.error.HTTPError(client.MCP_URL, 500, "Err", {}, None)
    )
    monkeypatch.setattr(client, "_OPENER", opener)

    with pytest.raises(RuntimeError):
        client.search_skills("x")

    assert opener.call_count == 1


def test_second_failure_raises(monkeypatch):
    opener = _FakeOpener(urllib.error.URLError("down"))
    monkeypatch.setattr(client, "_OPENER", opener)

    with pytest.raises(RuntimeError):
        client.search_skills("x")

    assert opener.call_count == 2
