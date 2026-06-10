import json

from fastmcp import FastMCP

from elastic.client import fetch_recent_events, fetch_user_profile

# Share the same MCP server instance declared in update_profile.py
# to avoid registering duplicate servers. Import it here directly.
from agent.tools.update_profile import mcp


@mcp.tool()
async def fetch_user_context(user_id: str) -> str:
    """
    Retrieves a combined context payload for `user_id` containing:
      - Their most recent 15 behavioral events (from 'behavioral_events' index).
      - Their current synthesised persona profile (from 'user_profiles' index),
        or a placeholder if no profile has been synthesised yet.

    Use this tool when you need to understand what a user has been doing and
    who they are before tailoring a response.

    Args:
        user_id: The unique identifier for the user.

    Returns:
        A JSON string with keys 'recent_events' (list) and 'current_profile' (dict|null).
    """
    recent_events = await fetch_recent_events(user_id, limit=15)
    current_profile = await fetch_user_profile(user_id)

    payload = {
        "user_id": user_id,
        "recent_events": recent_events,
        "current_profile": current_profile,
    }

    return json.dumps(payload, default=str)
