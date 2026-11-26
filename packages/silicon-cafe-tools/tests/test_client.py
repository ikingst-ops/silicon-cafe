"""Hermetic tests for silicon_cafe_tools.client (no network access)."""

import json

import pytest

from silicon_cafe_tools import client


class RpcRecorder:
    """Records every RPC call made through the ``_rpc_call`` seam."""

    def __init__(self, response=None, exc=None):
        self.response = response
        self.exc = exc
        self.calls = []

    def __call__(self, tool_name, arguments, api_key=None, allow_retry=True):
        self.calls.append(
            {
                "tool_name": tool_name,
                "arguments": arguments,
                "api_key": api_key,
                "allow_retry": allow_retry,
            }
        )
        if self.exc is not None:
            raise self.exc
        return self.response

    @property
    def last(self):
        if not self.calls:
            raise AssertionError("no RPC calls were recorded")
        return self.calls[-1]


@pytest.fixture
def fake_rpc(monkeypatch):
    def _install(response=None, exc=None):
        recorder = RpcRecorder(response=response, exc=exc)
        monkeypatch.setattr(client, "_rpc_call", recorder)
        return recorder

    return _install


SEARCH_PAYLOAD = {
    "results": [
        {"id": "pdf-toolkit", "name": "PDF Toolkit", "category": "documents"},
    ],
    "total": 1,
}


def test_search_skills_returns_structured_content(fake_rpc):
    rpc = fake_rpc(response={"structuredContent": SEARCH_PAYLOAD})

    result = client.search_skills("pdf", category="documents", lang="en", limit=3)

    assert result == SEARCH_PAYLOAD
    assert len(rpc.calls) == 1


def test_search_skills_forwards_optional_arguments(fake_rpc):
    rpc = fake_rpc(response={"structuredContent": SEARCH_PAYLOAD})

    client.search_skills("pdf", category="documents", lang="en", limit=3)

    args = rpc.last["arguments"]
    assert "pdf" in args.values()
    assert args["category"] == "documents"
    assert args["lang"] == "en"
    assert args["limit"] == 3


def test_search_skills_omits_none_optionals(fake_rpc):
    rpc = fake_rpc(response={"structuredContent": SEARCH_PAYLOAD})

    client.search_skills("pdf")

    args = rpc.last["arguments"]
    assert "pdf" in args.values()
    assert "category" not in args
    assert "lang" not in args
    assert None not in args.values()


def test_check_skill_parses_json_text_content(fake_rpc):
    payload = {"id": "pdf-toolkit", "verified": True, "version": "1.2.0"}
    fake_rpc(response={"content": [{"type": "text", "text": json.dumps(payload)}]})

    result = client.check_skill("pdf-toolkit")

    assert result == payload


def test_plain_text_content_falls_back_to_text_dict(fake_rpc):
    fake_rpc(response={"content": [{"type": "text", "text": "plain text result"}]})

    result = client.check_skill("pdf-toolkit")

    assert result == {"text": "plain text result"}

def test_get_install_info_passes_explicit_api_key(fake_rpc, monkeypatch):
    monkeypatch.delenv("TEA_API_KEY", raising=False)
    rpc = fake_rpc(response={"structuredContent": {"install": "pip install x"}})

    client.get_install_info(3001, api_key="explicit-key")

    assert rpc.last["api_key"] == "explicit-key"
    assert rpc.last["allow_retry"] is False


def test_get_install_info_falls_back_to_env_api_key(fake_rpc, monkeypatch):
    monkeypatch.setenv("TEA_API_KEY", "test-key")
    rpc = fake_rpc(response={"structuredContent": {"install": "pip install x"}})

    client.get_install_info(3001)

    assert rpc.last["api_key"] == "test-key"
    assert rpc.last["allow_retry"] is False


def test_search_skills_propagates_rpc_errors(fake_rpc):
    fake_rpc(exc=RuntimeError("boom"))

    with pytest.raises(RuntimeError, match="boom"):
        client.search_skills("pdf")
