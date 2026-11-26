"""Tools for the 1VR Skill Store, backed by its live remote MCP server.

The store indexes 3,175 agent skills and exposes three tools over a stateless
streamable-HTTP MCP endpoint: search, pre-install audit signals, and install
instructions. Health-check findings are factual records with sources, not a
safety guarantee.
"""

from __future__ import annotations

from .client import check_skill, get_install_info, search_skills

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "search_skills",
    "check_skill",
    "get_install_info",
]
