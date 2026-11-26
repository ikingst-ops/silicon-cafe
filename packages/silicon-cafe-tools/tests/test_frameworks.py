"""Smoke tests for the LangChain and CrewAI integrations (no network access)."""

import pytest

from silicon_cafe_tools import client

MARKER = "marker-pdf-toolkit-7f3a"

CANNED_SEARCH = {
    "results": [{"id": MARKER, "name": "PDF Toolkit", "category": "documents"}],
    "total": 1,
}


@pytest.fixture
def canned_search(monkeypatch):
    calls = []

    def fake_search_skills(*args, **kwargs):
        calls.append((args, kwargs))
        return CANNED_SEARCH

    monkeypatch.setattr(client, "search_skills", fake_search_skills)
    return calls


def test_langchain_tool_names_and_search(canned_search):
    pytest.importorskip("langchain_core")
    from langchain_silicon_cafe import skill_store_tools

    tools = skill_store_tools()

    assert sorted(tool.name for tool in tools) == sorted(
        ["skill_store_search", "skill_store_check", "skill_store_get_install"]
    )

    search_tool = next(tool for tool in tools if tool.name == "skill_store_search")
    result = search_tool.invoke({"query": "pdf"})

    assert isinstance(result, str)
    assert MARKER in result
    assert len(canned_search) == 1


def test_crewai_search_tool_run(canned_search):
    pytest.importorskip("crewai")
    from crewai_silicon_cafe import SkillStoreSearchTool

    tool = SkillStoreSearchTool()
    result = tool._run(query="pdf")

    assert isinstance(result, str)
    assert MARKER in result
    assert len(canned_search) == 1
