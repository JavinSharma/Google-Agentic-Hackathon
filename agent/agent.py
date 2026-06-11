import sys

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.genai import types
from mcp import StdioServerParameters

from agent.prompts import SYSTEM_INSTRUCTION
from agent.tools.log_action import log_user_action

load_dotenv()

APP_NAME = "hyper_context_engine"

# MCP connection to agent/mcp_server.py, which exposes Slice 2's
# fetch_user_context and update_user_profile tools over stdio.
context_engine_tools = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=["-m", "agent.mcp_server"],
        ),
    ),
)

root_agent = LlmAgent(
    name="hyper_context_agent",
    model="gemini-2.5-flash",
    instruction=SYSTEM_INSTRUCTION,
    tools=[log_user_action, context_engine_tools],
)

session_service = InMemorySessionService()
runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)


async def run_agent(user_id: str, message: str, session_id: str) -> tuple[str, list[dict]]:
    """
    Runs one conversational turn through the ADK agent.

    Returns:
        (final_text_response, thought_trace_frames). thought_trace_frames is a
        list of {"type": "tool_call" | "tool_response", "data": {...}} dicts,
        one per ToolCall/ToolResponse event emitted during this run.
    """
    session = await session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    if session is None:
        session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
            state={"user_id": user_id},
        )

    new_message = types.Content(role="user", parts=[types.Part(text=message)])

    thought_trace: list[dict] = []
    final_text = ""

    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=new_message
    ):
        for call in event.get_function_calls():
            thought_trace.append({"type": "tool_call", "data": call.model_dump(exclude_none=True)})

        for response in event.get_function_responses():
            thought_trace.append({"type": "tool_response", "data": response.model_dump(exclude_none=True)})

        if event.is_final_response() and event.content and event.content.parts:
            final_text = "".join(part.text or "" for part in event.content.parts if part.text)

    return final_text, thought_trace
