"""LangChain wrappers around the 1VR Skill Store client.

Every tool here is a thin, side-effect-free adapter over
``silicon_cafe_tools.client``; the raw JSON payload is returned as text so an
agent can read it directly. Health-check findings are factual records with
sources, not a safety guarantee.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import StructuredTool

from silicon_cafe_tools.client import check_skill, get_install_info, search_skills

HONESTY_NOTE = (
    "Health-check findings are factual records with sources, not a safety guarantee."
)

__all__ = [
    "skill_store_tools",
    "skill_store_search_tool",
    "skill_store_check_tool",
    "skill_store_get_install_tool",
]


def _as_text(result: Any) -> str:
    """Render a client result as text, leaving strings untouched."""
    if isinstance(result, str):
        return result
    return json.dumps(result, ensure_ascii=False)


def skill_store_search(
    query: str,
    category: str | None = None,
    lang: str | None = None,
    limit: int = 8,
) -> str:
    """Search the 1VR Skill Store.

    Args:
        query: Task or keyword to search for.
        category: Optional category filter.
        lang: Optional language filter.
        limit: Maximum number of results, 1-20 (default 8).
    """
    return _as_text(
        search_skills(q=query, category=category, lang=lang, limit=limit)
    )


def skill_store_check(skill_id: int) -> str:
    """Fetch the recorded pre-install audit signals for one skill."""
    return _as_text(check_skill(skill_id=skill_id))


def skill_store_get_install(skill_id: int) -> str:
    """Fetch ready-to-run install text and the source link for one skill."""
    return _as_text(get_install_info(skill_id=skill_id))


skill_store_search_tool = StructuredTool.from_function(
    func=skill_store_search,
    name="skill_store_search",
    description=(
        "Search 3,175 agent skills in the 1VR Skill Store by task or keyword. "
        "Returns matching skills with their install information and a summary of "
        "each skill's recorded health-check (audit) signals. "
        "Optional filters: category, lang; limit is 1-20 (default 8). "
        + HONESTY_NOTE
    ),
)

skill_store_check_tool = StructuredTool.from_function(
    func=skill_store_check,
    name="skill_store_check",
    description=(
        "Return the pre-install audit signals recorded for one Skill Store skill "
        "(a numeric skill_id from search results): tier, checked_at, and findings "
        "grouped by category with their sources. Reports facts only and certifies "
        "nothing. " + HONESTY_NOTE
    ),
)

skill_store_get_install_tool = StructuredTool.from_function(
    func=skill_store_get_install,
    name="skill_store_get_install",
    description=(
        "Return ready-to-run install text and the source link for one Skill Store "
        "skill (a numeric skill_id from search results). Call this after checking a "
        "skill so the agent has exact install commands. " + HONESTY_NOTE
    ),
)


def skill_store_tools() -> list[StructuredTool]:
    """Return all Skill Store tools, ready to bind to a LangChain agent."""
    return [
        skill_store_search_tool,
        skill_store_check_tool,
        skill_store_get_install_tool,
    ]
