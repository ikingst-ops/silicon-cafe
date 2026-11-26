"""CrewAI tool wrappers around the 1VR Skill Store client.

The tools delegate to :mod:`silicon_cafe_tools.client`, looking functions up
on the module at call time so they can be monkeypatched in tests.
"""

from __future__ import annotations

import json
from typing import Any, Optional, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from silicon_cafe_tools import client

__all__ = [
    "SkillStoreSearchInput",
    "SkillStoreSkillIdInput",
    "SkillStoreSearchTool",
    "SkillStoreCheckTool",
    "SkillStoreGetInstallTool",
]

_HONESTY_NOTE = (
    "Health-check findings are factual records with sources, not a safety guarantee."
)


def _to_text(result: Any) -> str:
    """Render a client result as a string suitable for an LLM tool response."""
    if isinstance(result, str):
        return result
    return json.dumps(result, ensure_ascii=False)


class SkillStoreSearchInput(BaseModel):
    """Arguments for :class:`SkillStoreSearchTool`."""

    query: str = Field(..., description="Free-text search query for agent skills.")
    category: Optional[str] = Field(
        default=None, description="Optional category filter."
    )
    lang: Optional[str] = Field(
        default=None, description="Optional language filter (e.g. 'en')."
    )
    limit: int = Field(
        default=8, ge=1, description="Maximum number of results to return."
    )


class SkillStoreSkillIdInput(BaseModel):
    """Arguments for tools that operate on a single skill."""

    skill_id: int = Field(..., description="Numeric ID of the skill in the 1VR Skill Store.")


class SkillStoreSearchTool(BaseTool):
    """Search the 1VR Skill Store for agent skills."""

    name: str = "skill_store_search"
    description: str = (
        "Search the 1VR Skill Store (3,175 agent skills) by free-text query, "
        "optionally filtered by category and language, and return matching "
        "skills with their health-check summaries. " + _HONESTY_NOTE
    )
    args_schema: Type[BaseModel] = SkillStoreSearchInput

    def _run(
        self,
        query: str,
        category: Optional[str] = None,
        lang: Optional[str] = None,
        limit: int = 8,
    ) -> str:
        result = client.search_skills(
            query, category=category, lang=lang, limit=limit
        )
        return _to_text(result)


class SkillStoreCheckTool(BaseTool):
    """Fetch the health-check record for a single skill."""

    name: str = "skill_store_check"
    description: str = (
        "Retrieve the health-check record for a 1VR Skill Store skill by its "
        "numeric ID, including findings and their sources. " + _HONESTY_NOTE
    )
    args_schema: Type[BaseModel] = SkillStoreSkillIdInput

    def _run(self, skill_id: int) -> str:
        return _to_text(client.check_skill(skill_id))


class SkillStoreGetInstallTool(BaseTool):
    """Fetch installation instructions for a single skill."""

    name: str = "skill_store_get_install"
    description: str = (
        "Fetch installation information for a 1VR Skill Store skill by its "
        "numeric ID; this tool installs nothing by itself. The fetch is "
        "recorded under the caller's own 1VR agent identity only when the "
        "TEA_API_KEY environment variable is set. " + _HONESTY_NOTE
    )
    args_schema: Type[BaseModel] = SkillStoreSkillIdInput

    def _run(self, skill_id: int) -> str:
        # No explicit key: the client reads TEA_API_KEY from the environment.
        return _to_text(client.get_install_info(skill_id))
