"""Hermetic tests for silicon_cafe_tools.client transport hardening.

No sockets, no servers: silicon_cafe_tools.client._OPENER is swapped for a
fake opener that replays canned JSON-RPC envelopes and reads the request id
straight out of the outgoing request body, so happy paths echo the right id.
"""

import json
import urllib.error

import pytest

from silicon_cafe_tools import client


class _FakeResponse:
    """Minimal stand-in for http.client.HTTPResponse."""

    def __init__(self, payload):
        self._payload = payload

    def read(self, *args, **kwargs):
        return self._payload


class _ContextManager:
    def __init__(self, obj):
        self._obj = obj

    def __enter__(self):
        return self._obj

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeOpener:
    """Replaces the module-level urllib opener."""

    def __init__(self, handler):
        self._handler = handler

    def open(self, request, timeout=None):
        payload = self._handler(request)
        return _ContextManager(_FakeResponse(payload))


def _install_opener(monkeypatch, handler):
    opener = _FakeOpener(handler)
    monkeypatch.setattr(client, "_OPENER", opener)
    return opener


def _request_id(request):
    data = request.data
    if isinstance(data, bytes):
        data = data.decode("utf-8")
    return json.loads(data).get("id")


def _bump(request_id):
    if isinstance(request_id, int):
        return request_id + 999
    return "{}-999".format(request_id)


def _envelope(request_id, result=None, *, jsonrpc="2.0", error=None):
    payload = {"jsonrpc": jsonrpc, "id": request_id}
    if error is not None:
        payload["error"] = error
    else:
        payload["result"] = result
    return json.dumps(payload).encode("utf-8")


def _echo(request, result):
    return _envelope(_request_id(request), result)


def test_redirect_is_refused():
    handler = client._NoRedirectHandler()

    class _Req:
        def get_full_url(self):
            return "https://example.invalid/mcp"

        def get_method(self):
            return "POST"

    assert handler.redirect_request(_Req(), object(), 302, "Found", {}, "https://evil.example/x") is None


def test_http_error_surfaces(monkeypatch):
    url = "https://example.invalid/mcp"

    def handler(request):
        raise urllib.error.HTTPError(url, 302, "Found", {}, None)

    _install_opener(monkeypatch, handler)

    with pytest.raises(RuntimeError):
        client._rpc_call("search_skills", {"q": "x"})


def test_is_error_result_raises(monkeypatch):
    result = {"isError": True, "content": [{"type": "text", "text": "boom"}]}
    _install_opener(monkeypatch, lambda request: _echo(request, result))

    with pytest.raises(RuntimeError, match="boom"):
        client.search_skills("x")


def test_id_mismatch_raises(monkeypatch):
    def handler(request):
        return _envelope(_bump(_request_id(request)), {"structuredContent": {"total": 0, "results": []}})

    _install_opener(monkeypatch, handler)

    with pytest.raises(RuntimeError):
        client.search_skills("x")


def test_wrong_version_raises(monkeypatch):
    def handler(request):
        return _envelope(_request_id(request), {"structuredContent": {"total": 0, "results": []}}, jsonrpc="1.0")

    _install_opener(monkeypatch, handler)

    with pytest.raises(RuntimeError):
        client.search_skills("x")


def test_happy_path_still_works(monkeypatch):
    result = {"structuredContent": {"total": 1, "results": []}}
    _install_opener(monkeypatch, lambda request: _echo(request, result))

    assert client.search_skills("x") == {"total": 1, "results": []}
