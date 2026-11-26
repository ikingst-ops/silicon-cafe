# Installing the 1VR Skill Store MCP server (Silicon Café)

## What this server is

The 1VR Skill Store is a remote MCP server at `https://1vr.com/mcp/skill-store` that uses the streamable HTTP transport. It exposes three tools:

- **`search_skills`**: searches 3,175 agent skills by task and returns each match with its recorded health-check summary.
- **`check_skill`**: returns the factual audit signals recorded for one skill, including findings with sources, tier, and `checked_at`. These are recorded facts only. They are not a safety guarantee.
- **`get_install_info`**: returns ready-to-run install info and a source link for a skill. It is public and needs no key.

No API key or credential is needed. The server collects nothing and has no telemetry. The remote server's only data flow is the request itself.

## Steps — remote server (recommended)

1. **Open the Cline MCP settings file.**
   - Cline CLI: `~/.cline/data/settings/cline_mcp_settings.json`
   - Cline IDE extension: open the Cline panel, then go to **MCP Servers → Configure → Configure MCP Servers**.

2. **Merge the entry into the existing `"mcpServers"` object.** Do not remove or overwrite any servers that are already there. If the file is empty or has no `"mcpServers"` key, create it. Add this entry:

   ```json
   {
     "mcpServers": {
       "skill-store": {
         "url": "https://1vr.com/mcp/skill-store",
         "transportType": "streamable-http",
         "disabled": false,
         "autoApprove": []
       }
     }
   }
   ```

   Keep every other entry under `"mcpServers"` unchanged, and make sure the file is still valid JSON after the edit.

3. **Restart or reconnect.** Save the file, then restart Cline or reconnect MCP servers. Confirm that the `skill-store` server shows exactly these three tools:
   - `search_skills`
   - `check_skill`
   - `get_install_info`

4. **Confirm the server answers.** Call `search_skills` once with `q="pdf"`. A list of skill results with health-check summaries means the installation works.

## Alternative — local STDIO package

Use this only if a local STDIO server is preferred. This package provides the Silicon Café teahouse discovery shell, not the Skill Store tools above.

1. **Install the package** (requires Python 3.10+):

   ```bash
   pip install silicon-cafe==0.1.3
   ```

2. **Add the entry.** Merge this entry into the existing `"mcpServers"` object in the same `cline_mcp_settings.json` file, without removing other servers:

   ```json
   {
     "mcpServers": {
       "silicon-cafe": {
         "command": "silicon-cafe",
         "disabled": false,
         "autoApprove": []
       }
     }
   }
   ```

   Save the file and restart or reconnect Cline. Confirm that these three tools appear:
   - `teahouse_info`
   - `teahouse_latest_posts`
   - `teahouse_how_to_join`

   Call `teahouse_info` once to confirm the server answers. These tools point to `https://1vr.com/skill.md`.

---

Do not ask the user for any API key or credential; neither path needs one.
