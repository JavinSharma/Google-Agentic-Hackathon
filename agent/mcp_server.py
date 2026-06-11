"""Stdio MCP server entrypoint exposing Slice 2's context-engine tools.

Spawned as a subprocess by the MCPToolset in agent.agent. Importing
agent.tools.fetch_context registers `fetch_user_context` on the shared `mcp`
server instance declared in agent.tools.update_profile.
"""

from agent.tools.update_profile import mcp
import agent.tools.fetch_context  # noqa: F401 - registers fetch_user_context on `mcp`

if __name__ == "__main__":
    mcp.run()
