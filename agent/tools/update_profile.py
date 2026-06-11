import json
import os
from dotenv import load_dotenv
from fastmcp import FastMCP
from google import genai
from google.genai import types

from elastic.client import fetch_recent_events, save_user_profile
from agent.prompts import USER_PROFILE_SYNTHESIS_PROMPT, UserProfileSummary

load_dotenv()

# ---------------------------------------------------------------------------
# MCP server instance — import this into agent.py when wiring up the agent
# ---------------------------------------------------------------------------
mcp = FastMCP("context_engine_server")


# ---------------------------------------------------------------------------
# FastMCP Tool
# ---------------------------------------------------------------------------

@mcp.tool()
async def update_user_profile(user_id: str, profile_data: dict) -> str:
    """
    Persists a synthesised user persona profile into Elasticsearch.

    The profile_data argument MUST be a dict (not a JSON string) so that the
    LLM cannot accidentally wrap its payload in Markdown code fences.

    Args:
        user_id:      The unique identifier for the user whose profile to update.
        profile_data: A dictionary containing the fields: interests (list[str]),
                      dislikes (list[str]), persona (str),
                      communication_style (str), technical_depth (str).

    Returns:
        A confirmation string with the Elasticsearch document ID.
    """
    response = await save_user_profile(user_id, profile_data)
    doc_id = response.get("_id", "unknown")
    return (
        f"Profile for user '{user_id}' saved successfully. "
        f"Elasticsearch document ID: {doc_id}"
    )


# ---------------------------------------------------------------------------
# Standalone synthesis helper (called directly by the Streamlit frontend)
# ---------------------------------------------------------------------------

async def trigger_profile_synthesis(user_id: str) -> dict:
    """
    Full pipeline helper:
      1. Fetch the last 15 behavioral events for `user_id`.
      2. Build the synthesis prompt from USER_PROFILE_SYNTHESIS_PROMPT.
      3. Call Gemini 2.0 Flash (async) with UserProfileSummary as the
         structured output schema to guarantee valid JSON.
      4. Persist the resulting profile to Elasticsearch via save_user_profile.
      5. Return the profile dict to the caller.

    Args:
        user_id: The unique identifier for the user.

    Returns:
        The synthesised profile dict.
    """
    # 1. Fetch recent events ------------------------------------------------
    events = await fetch_recent_events(user_id, limit=15)

    if not events:
        empty_profile: dict = {
            "interests": [],
            "dislikes": [],
            "persona": "No recent behavioral history found for this user.",
            "communication_style": "casual",
            "technical_depth": "beginner",
        }
        await save_user_profile(user_id, empty_profile)
        return empty_profile

    # 2. Format events for the prompt ---------------------------------------
    lines = []
    for event in events:
        action = event.get("action_type", "unknown")
        topic = event.get("topic", "unknown")
        ts = event.get("timestamp", "")
        lines.append(f"- Action: {action} | Topic: {topic} | Time: {ts}")

    events_text = "\n".join(lines)
    prompt = USER_PROFILE_SYNTHESIS_PROMPT.format(events_json=events_text)

    # 3. Call Gemini 2.5 Flash Lite with structured output (async) ---------------
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key) if api_key else genai.Client()

    response = await client.aio.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=UserProfileSummary,
        ),
    )

    # 4. Parse the guaranteed-valid JSON response ---------------------------
    profile_dict: dict = json.loads(response.text)

    # 5. Persist to Elasticsearch -------------------------------------------
    await save_user_profile(user_id, profile_dict)

    return profile_dict
