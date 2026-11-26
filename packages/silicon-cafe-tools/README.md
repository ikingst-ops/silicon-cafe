# silicon-cafe-tools

`silicon-cafe-tools` gives LangChain and CrewAI agents native tools over the 1VR Skill Store — 3,175 agent skills in the open `SKILL.md` format, searchable by the task you need done. Every skill carries the factual signals its health check recorded: findings with sources, tier, and `checked_at`.

Health-check findings are factual records, not a safety guarantee.

Version 0.1.0 · MIT · Published by Silicon Café (1VR) · Support: ikingst-ops@muse.ai

## Install

```bash
pip install "silicon-cafe-tools[langchain]"
# or
pip install "silicon-cafe-tools[crewai]"
```

No account or key is needed to search or check. `TEA_API_KEY` only affects install-fetch recording: if it is set, `skill_store_get_install` records the fetch under your 1VR agent identity; if it is not set, the fetch still works and is simply not attributed.

The package itself has no third-party HTTP dependencies (it uses the standard library's `urllib`) and collects or stores nothing. The only network calls it makes go to `1vr.com`: redirects are refused, so a key can never be forwarded to another host, and a transport-level failure is retried once.

## Tools

The same three tools are exposed for both frameworks.

| Tool | What it does |
| --- | --- |
| `skill_store_search` | Search skills by the task you need done. Optional `category` and `lang` filters, plus `limit`. |
| `skill_store_check` | Return the recorded health-check signals for one skill: `tier`, `checked_at`, and findings grouped by category, each with its source. |
| `skill_store_get_install` | Return ready-to-run install instructions and a source link for one skill. It installs nothing by itself. |

## LangChain

```python
from langchain_silicon_cafe import skill_store_tools

tools = skill_store_tools()

# `tools` is a plain list of LangChain tools — pass it to any LangChain or
# LangGraph agent, e.g. create_react_agent(llm, tools) or a StateGraph node.
#
# Optional: attribute install-fetches to your own 1VR agent identity.
#   export TEA_API_KEY="your-1vr-agent-key"
```

## CrewAI

```python
from crewai import Agent
from crewai_silicon_cafe import (
    SkillStoreSearchTool,
    SkillStoreCheckTool,
    SkillStoreGetInstallTool,
)

scout = Agent(
    role="Skill scout",
    goal="Find a skill that does the requested task, check its recorded signals, and hand back install instructions.",
    backstory="Looks up agent skills in the 1VR Skill Store and reports what the health check recorded.",
    tools=[
        SkillStoreSearchTool(),
        SkillStoreCheckTool(),
        SkillStoreGetInstallTool(),
    ],
)
```

## Prefer MCP directly?

The tools are thin wrappers over the live Skill Store MCP server at `https://1vr.com/mcp/skill-store` (streamable HTTP). You can skip this package and talk to it yourself.

LangChain, via `langchain-mcp-adapters`:

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient(
    {
        "silicon-cafe": {
            "url": "https://1vr.com/mcp/skill-store",
            "transport": "streamable_http",
        }
    }
)
tools = await client.get_tools()
```

CrewAI, using the documented remote-server reference form:

```python
Agent(
    role="Skill scout",
    goal="Find and vet agent skills.",
    backstory="Looks up agent skills in the 1VR Skill Store.",
    mcps=["https://1vr.com/mcp/skill-store"],
)
```

## Notes

- Standalone package, not part of `langchain-community`. Install it next to the framework you actually use — the `[langchain]` and `[crewai]` extras pull in the matching adapter module.
- The store does not host skill files. Installs always come from each skill's own source repository, and results link to that source.
- The same Skill Store is also reachable as a bridge plugin for Claude Code, Codex, Cursor, and Devin, and via the `silicon-cafe` STDIO MCP package.
- Findings describe what a health check recorded at `checked_at`. Re-check before relying on them.

## License

MIT. Browse the store at https://1vr.com/skills.
