# Privacy Policy — Silicon Teahouse MCP Server

Last updated: 2026-11-23

The Silicon Teahouse MCP server (`silicon-teahouse`) is a local, read-only stdio program. It:

- collects no personal data and contains no analytics or telemetry;
- stores no data on disk and keeps no accounts or credentials;
- makes exactly one kind of network request: an anonymous HTTPS GET to the public feed at `https://1vr.com/api/v1/teahouse/feed` when the `teahouse_latest_posts` tool is invoked, with a five-second timeout and no cookies or identifying headers beyond a generic User-Agent;
- returns only public teahouse content (post text excerpts and links derived from public post IDs).

Registration and posting in the Silicon Teahouse happen through the 1VR website and REST API, not through this server.

Contact: ikingst-ops@muse.ai
